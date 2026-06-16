import datetime
import json
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import Order, AuditLog, SLAHistory, Reorder, Prescription

# Define the valid transitions dictionary
VALID_TRANSITIONS = {
    "ORDER_PLACED": {"PRESCRIPTION_RECEIVED", "CANCELLED"},
    "PRESCRIPTION_RECEIVED": {"PRESCRIPTION_VALIDATED", "CANCELLED"},
    "PRESCRIPTION_VALIDATED": {"FRAME_ALLOCATED", "CANCELLED"},
    "FRAME_ALLOCATED": {"LENS_ALLOCATED", "CANCELLED"},
    "LENS_ALLOCATED": {"IN_LAB", "CANCELLED"},
    "IN_LAB": {"CUTTING", "CANCELLED"},
    "CUTTING": {"COATING", "CANCELLED"},
    "COATING": {"ASSEMBLY", "CANCELLED"},
    "ASSEMBLY": {"QC_PENDING", "CANCELLED"},
    "QC_PENDING": {"QC_FAILED", "PACKAGING", "CANCELLED"},
    "QC_FAILED": {"REORDER", "CANCELLED"},
    "REORDER": {"PRESCRIPTION_VALIDATED", "CANCELLED"},
    "PACKAGING": {"SHIPPED", "CANCELLED"},
    "SHIPPED": {"OUT_FOR_DELIVERY", "CANCELLED"},
    "OUT_FOR_DELIVERY": {"DELIVERED", "CANCELLED"},
    "DELIVERED": set(),
    "CANCELLED": set()
}

class OrderFSM:
    @staticmethod
    def transition_to(db: Session, order: Order, new_status: str, user_id: Optional[int] = None, reason: Optional[str] = None) -> Order:
        """
        Transition order to a new state. Restricts invalid transitions and logs changes.
        """
        current_status = order.current_status
        
        # Check transition validity
        if new_status not in VALID_TRANSITIONS.get(current_status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid transition from {current_status} to {new_status}."
            )
            
        # Log old status in SLA history before changing
        OrderFSM._record_sla_history_exit(db, order, current_status)
        
        # Apply the transition
        order.current_status = new_status
        order.updated_at = datetime.datetime.utcnow()
        order.delay_reason = reason
        
        # Log to Audit Log
        audit = AuditLog(
            user_id=user_id,
            table_name="orders",
            record_id=order.id,
            action="UPDATE",
            old_value=json.dumps({"current_status": current_status}),
            new_value=json.dumps({"current_status": new_status, "reason": reason}),
            timestamp=datetime.datetime.utcnow()
        )
        db.add(audit)
        
        # Record SLA history enter for the new state
        OrderFSM._record_sla_history_enter(db, order, new_status)
        
        db.commit()
        db.refresh(order)
        
        # Recalculate TAT prediction and check breach alerts
        try:
            from app.services.tat_service import TATService
            TATService.predict_and_evaluate_order(db, order)
        except Exception as tat_ex:
            import logging
            logger = logging.getLogger("order_fsm")
            logger.error(f"Error running TAT prediction on transition: {tat_ex}")
        
        # Handle Event loop checks
        if new_status == "QC_FAILED":
            OrderFSM._handle_qc_failure(db, order, user_id, reason)
            
        return order

    @staticmethod
    def _record_sla_history_enter(db: Session, order: Order, stage: str):
        # Default SLA hours per stage
        sla_limits = {
            "ORDER_PLACED": 2.0,
            "PRESCRIPTION_RECEIVED": 4.0,
            "PRESCRIPTION_VALIDATED": 4.0,
            "FRAME_ALLOCATED": 2.0,
            "LENS_ALLOCATED": 2.0,
            "IN_LAB": 8.0,
            "CUTTING": 12.0,
            "COATING": 24.0,
            "ASSEMBLY": 6.0,
            "QC_PENDING": 4.0,
            "QC_FAILED": 2.0,
            "REORDER": 2.0,
            "PACKAGING": 4.0,
            "SHIPPED": 24.0,
            "OUT_FOR_DELIVERY": 12.0
        }
        
        limit = sla_limits.get(stage, 12.0)
        history = SLAHistory(
            order_id=order.id,
            stage=stage,
            entered_at=datetime.datetime.utcnow(),
            sla_limit_hours=limit,
            status="ON_TIME"
        )
        db.add(history)

    @staticmethod
    def _record_sla_history_exit(db: Session, order: Order, stage: str):
        history = db.query(SLAHistory).filter(
            SLAHistory.order_id == order.id,
            SLAHistory.stage == stage,
            SLAHistory.exited_at.is_(None)
        ).first()
        
        if history:
            history.exited_at = datetime.datetime.utcnow()
            diff = history.exited_at - history.entered_at
            history.tat_hours = diff.total_seconds() / 3600.0
            
            # If actual TAT exceeded the SLA limit, mark it as BREACHED
            if history.tat_hours > history.sla_limit_hours:
                history.status = "BREACHED"
                order.remaining_tat_hours -= history.tat_hours
                if order.remaining_tat_hours < 0:
                    order.risk_score = "High"

    @staticmethod
    def _handle_qc_failure(db: Session, failed_order: Order, user_id: Optional[int] = None, reason: Optional[str] = None):
        """
        QC Loop execution:
        - Automatically create a warranty reorder.
        - Transfer prescription.
        - Reset/recalculate SLA.
        - Set original order to QC_FAILED and the reorder to PRESCRIPTION_VALIDATED.
        """
        # Transition original order to REORDER state to mark it's being reworked
        failed_order.current_status = "QC_FAILED"
        
        # Calculate new order number
        new_order_number = f"{failed_order.order_number}-R1"
        count = 1
        while db.query(Order).filter(Order.order_number == new_order_number).first():
            count += 1
            new_order_number = f"{failed_order.order_number}-R{count}"
            
        # Create a new warranty Order
        reorder_item = Order(
            order_number=new_order_number,
            customer_id=failed_order.customer_id,
            store_id=failed_order.store_id,
            prescription_id=failed_order.prescription_id,
            frame_id=failed_order.frame_id,
            lens_type=failed_order.lens_type,
            lens_index=failed_order.lens_index,
            coating_id=failed_order.coating_id,
            payment_status="PAID",  # Reorders are covered
            total_amount=0.0,
            current_status="ORDER_PLACED",
            current_sla_days=failed_order.current_sla_days,
            remaining_tat_hours=float(failed_order.current_sla_days * 24),
            risk_score="Medium"
        )
        db.add(reorder_item)
        db.commit()
        db.refresh(reorder_item)
        
        # Track reorder linkage
        link = Reorder(
            original_order_id=failed_order.id,
            new_order_id=reorder_item.id,
            reason=reason or "Failed visual QC checklist",
            created_at=datetime.datetime.utcnow()
        )
        db.add(link)
        db.commit()
        
        # Progress the reorder to PRESCRIPTION_VALIDATED since prescription was already validated
        OrderFSM._record_sla_history_enter(db, reorder_item, "ORDER_PLACED")
        OrderFSM.transition_to(db, reorder_item, "PRESCRIPTION_RECEIVED", user_id=user_id, reason="Auto-reorder created")
        OrderFSM.transition_to(db, reorder_item, "PRESCRIPTION_VALIDATED", user_id=user_id, reason="Auto-reorder auto-validated")
