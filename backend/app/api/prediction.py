from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order
from app.api.auth import get_current_user, RoleChecker
from app.ai.models_registry import registry as ml_registry
from app.services.twin_service import TwinService

router = APIRouter(prefix="/predictions", tags=["Predictions"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])

@router.post("/sla-breach/{order_id}", dependencies=[Depends(role_staff_or_admin)])
def predict_order_sla_breach_probability(order_id: int, db: Session = Depends(get_db)):
    """
    Applies Random Forest/XGBoost to estimate order SLA breach probability.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Extract features: [current_stage_id, lens_type_id, store_id, rx_complexity, qc_failures]
    stage_mapping = {"ORDER_PLACED": 1, "IN_LAB": 2, "CUTTING": 3, "COATING": 4, "QC_PENDING": 5}
    current_stage = stage_mapping.get(order.current_status, 1)
    
    lens_mapping = {"single vision": 1, "progressive": 2, "blue cut": 3}
    lens_type_val = lens_mapping.get(order.lens_type.lower(), 1)
    
    rx_complexity = 1.5  # default baseline
    if order.prescription:
        # Complex SPH or CYL increases difficulty
        rx_complexity += abs(order.prescription.sph_od) * 0.2
        rx_complexity += abs(order.prescription.cyl_od) * 0.4
        
    qc_failures = len(order.qc_logs)
    
    features = [
        float(current_stage),
        float(lens_type_val),
        float(order.store_id),
        float(rx_complexity),
        float(qc_failures)
    ]
    
    prob = ml_registry.predict_sla_breach(db, order.id, features)
    
    # Update order model with breach probability
    order.breach_risk_prob = prob
    if prob >= 0.7:
        order.risk_score = "High"
    elif prob >= 0.4:
        order.risk_score = "Medium"
    else:
        order.risk_score = "Low"
    db.commit()
    
    return {
        "order_id": order.id,
        "breach_probability": round(prob, 2),
        "risk_level": order.risk_score,
        "explanation": {
            "stage_factor": current_stage,
            "lens_complexity_factor": rx_complexity,
            "qc_failure_count": qc_failures
        }
    }

@router.post("/delivery-delay/{order_id}", dependencies=[Depends(role_staff_or_admin)])
def predict_order_courier_delay(order_id: int, db: Session = Depends(get_db)):
    """
    Applies Random Forest/XGBoost to estimate shipping delivery latency.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    # Features: [courier_id, dest_region_id, weather_severity, inventory_availability, historical_delay]
    courier_id = 1.0  # BlueDart
    dest_region = 2.0  # Mumbai/Delhi
    weather = 0.0     # Sunny (0.0 to 3.0 scale)
    inventory = 1.0   # Reserved
    hist_delay = 2.4   # average courier lag
    
    features = [courier_id, dest_region, weather, inventory, hist_delay]
    
    predicted_hours, delay_prob = ml_registry.predict_delivery_delay(db, order.id, features)
    
    return {
        "order_id": order.id,
        "predicted_delay_hours": round(predicted_hours, 2),
        "delay_probability": round(delay_prob, 2),
        "courier": "BlueDart Express"
    }

@router.post("/digital-twin", dependencies=[Depends(role_staff_or_admin)])
def execute_digital_twin_simulation_run(
    scenario: str = "standard", order_load: int = 150, lab_capacity: int = 100, vendor_reliability: float = 0.95
):
    """
    Stochastic simulation of production flow queues under capacity configurations.
    Scenarios: standard, spike, vendor_failure, lab_outage.
    """
    if scenario not in ["standard", "spike", "vendor_failure", "lab_outage"]:
        raise HTTPException(status_code=400, detail="Invalid simulation scenario.")
        
    result = TwinService.simulate_order_flow(scenario, order_load, lab_capacity, vendor_reliability)
    return result

from app.services.tat_service import TATService

@router.post("/check-sla-breach/{order_id}", dependencies=[Depends(role_staff_or_admin)])
def check_order_sla_breach_and_alert(order_id: int, db: Session = Depends(get_db)):
    """
    Evaluates and updates SLA breach risk for a specific order using historical order history & current stage.
    Triggers Email/WhatsApp alerts if breach risk is High.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    result = TATService.predict_and_evaluate_order(db, order)
    return result

@router.post("/check-all-sla-breaches", dependencies=[Depends(role_staff_or_admin)])
def check_all_sla_breaches_and_alert(db: Session = Depends(get_db)):
    """
    Evaluates and updates SLA breach risk for all active (non-delivered, non-cancelled) orders.
    Triggers Email/WhatsApp alerts for high-risk orders.
    """
    results = TATService.predict_and_evaluate_all_active_orders(db)
    return {
        "status": "success",
        "processed_count": len(results),
        "results": results
    }
