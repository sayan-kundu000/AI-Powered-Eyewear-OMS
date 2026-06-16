import datetime
import random
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from app.database import get_db
from app.models import Order, Customer, Store, QCLog, AuditLog, Prescription, Coating
from app.schemas import OrderCreate, OrderResponse, OrderStatusUpdate, QCVerifyResult, QCLogResponse
from app.api.auth import get_current_user, RoleChecker
from app.services.order_fsm import OrderFSM
from app.services.event_bus import event_bus
from app.services.inventory_service import InventoryService
from app.ai.qc_vision import qc_vision_engine

router = APIRouter(prefix="/orders", tags=["Orders"])

# Role configurations
role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])
role_lab_or_admin = RoleChecker(["LAB_TECH"])

@router.post("", response_model=OrderResponse, dependencies=[Depends(role_staff_or_admin)])
def create_new_order(order_in: OrderCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    # Verify customer and store exist
    customer = db.query(Customer).filter(Customer.id == order_in.customer_id).first()
    store = db.query(Store).filter(Store.id == order_in.store_id).first()
    if not customer or not store:
        raise HTTPException(status_code=404, detail="Customer or Store not found")

    # Generate unique order number
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    rand = random.randint(1000, 9999)
    order_number = f"ORD-{timestamp}-{rand}"

    # Calculate SLA days based on lens type
    # Single Vision: 2 days, Blue Cut: 3 days, Progressive: 5 days
    sla_days = 3
    if "progressive" in order_in.lens_type.lower():
        sla_days = 5
    elif "single" in order_in.lens_type.lower():
        sla_days = 2
        
    # Check lens stock availability immediately upon order placement if prescription is provided
    lens_stock_status = "PENDING"
    if order_in.prescription_id:
        rx = db.query(Prescription).filter(Prescription.id == order_in.prescription_id).first()
        if rx:
            # Look up coating name
            coating_name = "Anti-Reflective"
            if order_in.coating_id:
                coating = db.query(Coating).filter(Coating.id == order_in.coating_id).first()
                if coating:
                    coating_name = coating.name
            
            # Check availability for both eyes
            status_od = InventoryService.check_lens_availability(
                db, order_in.lens_type, rx.sph_od, rx.cyl_od, order_in.lens_index, coating_name
            )
            status_os = InventoryService.check_lens_availability(
                db, order_in.lens_type, rx.sph_os, rx.cyl_os, order_in.lens_index, coating_name
            )
            if status_od == "IN_HOUSE" and status_os == "IN_HOUSE":
                lens_stock_status = "IN_HOUSE"
                # Deliver ASAP: shorten SLA to 1 day for express delivery!
                sla_days = 1
            else:
                lens_stock_status = "VENDOR_REQUIRED"
        
    order = Order(
        order_number=order_number,
        customer_id=order_in.customer_id,
        store_id=order_in.store_id,
        prescription_id=order_in.prescription_id,
        frame_id=order_in.frame_id,
        lens_type=order_in.lens_type,
        lens_index=order_in.lens_index,
        coating_id=order_in.coating_id,
        payment_status="PENDING",
        total_amount=order_in.total_amount,
        current_status="ORDER_PLACED",
        current_sla_days=sla_days,
        remaining_tat_hours=float(sla_days * 24),
        risk_score="Low",
        lens_stock_status=lens_stock_status
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    
    # Audit log
    import json
    audit = AuditLog(
        user_id=current_user.id,
        table_name="orders",
        record_id=order.id,
        action="INSERT",
        new_value=json.dumps({"order_number": order_number, "status": "ORDER_PLACED"})
    )
    db.add(audit)
    
    # SLA History start
    OrderFSM._record_sla_history_enter(db, order, "ORDER_PLACED")
    db.commit()
    
    # Emit event
    event_bus.publish("OrderCreated", {
        "order_id": order.id,
        "order_number": order.order_number,
        "customer_id": order.customer_id
    })
    
    # Try inventory reservation if prescription is already validated
    if order.prescription_id:
        # Check validation
        rx = db.query(Prescription).filter(Prescription.id == order.prescription_id).first()
        if rx and rx.is_validated:
            try:
                # Progress FSM
                OrderFSM.transition_to(db, order, "PRESCRIPTION_RECEIVED", current_user.id, "Auto transitions")
                OrderFSM.transition_to(db, order, "PRESCRIPTION_VALIDATED", current_user.id, "Auto transitions")
                # Attempt to allocate Frame
                allocated = InventoryService.reserve_stock(db, order)
                if allocated:
                    OrderFSM.transition_to(db, order, "FRAME_ALLOCATED", current_user.id, "In-house allocation success")
                    OrderFSM.transition_to(db, order, "LENS_ALLOCATED", current_user.id, "In-house allocation success")
            except Exception as e:
                # Log transition error and proceed
                pass

    return order

@router.get("", response_model=List[OrderResponse], dependencies=[Depends(role_staff_or_admin)])
def list_orders(
    search: Optional[str] = None,
    status: Optional[str] = None,
    store_id: Optional[int] = None,
    lens_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    
    # Apply filters
    if status:
        query = query.filter(Order.current_status == status)
    if store_id:
        query = query.filter(Order.store_id == store_id)
    if lens_type:
        query = query.filter(Order.lens_type == lens_type)
        
    # Search implementation: PostgreSQL Full Text Search / SQLite multi-field string check
    if search:
        # Fallback to standard SQL ILIKE queries that work across SQLite and Postgres
        query = query.join(Order.customer).filter(
            or_(
                Order.order_number.ilike(f"%{search}%"),
                Customer.first_name.ilike(f"%{search}%"),
                Customer.last_name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%")
            )
        )
        
    return query.order_by(desc(Order.created_at)).all()

@router.get("/stores", dependencies=[Depends(role_staff_or_admin)])
def get_all_stores(db: Session = Depends(get_db)):
    stores = db.query(Store).all()
    return [{"id": s.id, "name": s.name, "location": s.location} for s in stores]

@router.get("/{order_id}/history", dependencies=[Depends(role_staff_or_admin)])
def get_order_history(order_id: int, db: Session = Depends(get_db)):
    import json
    # Fetch audit logs for this order
    audit_logs = db.query(AuditLog).filter(
        AuditLog.table_name == "orders",
        AuditLog.record_id == order_id
    ).order_by(AuditLog.timestamp.desc()).all()
    
    history_data = []
    for log in audit_logs:
        try:
            old_val = json.loads(log.old_value) if log.old_value else {}
        except Exception:
            old_val = {}
            
        try:
            new_val = json.loads(log.new_value) if log.new_value else {}
        except Exception:
            new_val = {}
            
        user_name = log.user.full_name if log.user else "System"
        
        history_data.append({
            "id": log.id,
            "action": log.action,
            "timestamp": log.timestamp.isoformat(),
            "user_name": user_name,
            "old_status": old_val.get("current_status") or old_val.get("status"),
            "new_status": new_val.get("current_status") or new_val.get("status"),
            "reason": new_val.get("reason")
        })
        
    return history_data

@router.get("/{order_id}", response_model=OrderResponse, dependencies=[Depends(role_staff_or_admin)])
def get_order_by_id(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.put("/{order_id}/status", response_model=OrderResponse, dependencies=[Depends(role_staff_or_admin)])
def update_order_status(
    order_id: int, status_in: OrderStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order = OrderFSM.transition_to(db, order, status_in.status, current_user.id, status_in.reason)
    
    if status_in.status == "PRESCRIPTION_VALIDATED":
        try:
            allocated = InventoryService.reserve_stock(db, order)
            if allocated:
                OrderFSM.transition_to(db, order, "FRAME_ALLOCATED", current_user.id, "In-house allocation success")
                OrderFSM.transition_to(db, order, "LENS_ALLOCATED", current_user.id, "In-house allocation success")
        except Exception as e:
            import logging
            logger = logging.getLogger("orders")
            logger.error(f"Error checking/reserving stock for order: {e}")
            
    return order

@router.post("/{order_id}/qc", response_model=QCLogResponse, dependencies=[Depends(role_lab_or_admin)])
def upload_qc_verification_image(
    order_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), current_user = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Transition to QC_PENDING to lock order state for review
    if order.current_status != "QC_PENDING":
        try:
            OrderFSM.transition_to(db, order, "QC_PENDING", current_user.id, "Submitting QC Image")
        except Exception:
            raise HTTPException(status_code=400, detail="Cannot perform QC at current order stage.")
            
    # Load image bytes
    contents = file.file.read()
    
    # Run vision analysis pipeline
    analysis = qc_vision_engine.inspect_eyewear(contents)
    
    # Store QC logs
    qc_log = QCLog(
        order_id=order_id,
        image_url=f"/static/qc/{file.filename}",
        qc_score=analysis["qc_score"],
        surface_defect_score=analysis["surface_defect_score"],
        alignment_score=analysis["alignment_score"],
        recommendation=analysis["recommendation"],
        inspector_id=current_user.id
    )
    db.add(qc_log)
    db.commit()
    db.refresh(qc_log)
    
    # Trigger event and FSM state transition
    event_bus.publish("QCCompleted", {
        "order_id": order_id,
        "qc_score": qc_log.qc_score,
        "recommendation": qc_log.recommendation
    })
    
    if qc_log.recommendation == "PASS":
        # Progress to PACKAGING
        OrderFSM.transition_to(db, order, "PACKAGING", current_user.id, "Visual QC Passed")
    else:
        # Failure: transitions to QC_FAILED which auto-creates warranty reorder
        OrderFSM.transition_to(db, order, "QC_FAILED", current_user.id, "Visual QC Failed")
        
    return qc_log
