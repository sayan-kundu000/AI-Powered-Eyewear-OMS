import pytest
from sqlalchemy.orm import Session
from app.models import Order, Customer, Store, SLAHistory, Reorder
from app.services.order_fsm import OrderFSM
from fastapi import HTTPException

def test_fsm_valid_transitions(db_session: Session):
    # Setup test customer and store
    cust = Customer(first_name="Test", last_name="User", email="test@test.com", phone="12345")
    store = Store(name="Test Store", location="Mumbai")
    db_session.add(cust)
    db_session.add(store)
    db_session.commit()
    
    # Create order
    order = Order(
        order_number="ORD-TEST-001",
        customer_id=cust.id,
        store_id=store.id,
        lens_type="Single Vision",
        lens_index=1.61,
        payment_status="PENDING",
        total_amount=1500.0,
        current_status="ORDER_PLACED",
        remaining_tat_hours=48.0
    )
    db_session.add(order)
    db_session.commit()
    
    # Start in ORDER_PLACED. Transition to PRESCRIPTION_RECEIVED
    OrderFSM.transition_to(db_session, order, "PRESCRIPTION_RECEIVED", reason="Manual upload")
    assert order.current_status == "PRESCRIPTION_RECEIVED"
    
    # Transition to PRESCRIPTION_VALIDATED
    OrderFSM.transition_to(db_session, order, "PRESCRIPTION_VALIDATED")
    assert order.current_status == "PRESCRIPTION_VALIDATED"

def test_fsm_invalid_transitions(db_session: Session):
    cust = Customer(first_name="Test", last_name="User", email="test@test.com", phone="12345")
    store = Store(name="Test Store", location="Mumbai")
    db_session.add(cust)
    db_session.add(store)
    db_session.commit()
    
    order = Order(
        order_number="ORD-TEST-002",
        customer_id=cust.id,
        store_id=store.id,
        lens_type="Single Vision",
        lens_index=1.61,
        payment_status="PENDING",
        total_amount=1500.0,
        current_status="ORDER_PLACED",
        remaining_tat_hours=48.0
    )
    db_session.add(order)
    db_session.commit()
    
    # Try transitioning straight to DELIVERED (invalid, must throw HTTP Exception)
    with pytest.raises(HTTPException):
        OrderFSM.transition_to(db_session, order, "DELIVERED")

def test_order_fsm_delay_reason(db_session: Session):
    cust = Customer(first_name="Delay", last_name="Tester", email="delay@test.com", phone="99999")
    store = Store(name="Test Store", location="Delhi")
    db_session.add(cust)
    db_session.add(store)
    db_session.commit()
    
    order = Order(
        order_number="ORD-TEST-DELAY",
        customer_id=cust.id,
        store_id=store.id,
        lens_type="Single Vision",
        lens_index=1.61,
        payment_status="PENDING",
        total_amount=1500.0,
        current_status="ORDER_PLACED",
        remaining_tat_hours=48.0
    )
    db_session.add(order)
    db_session.commit()
    
    # Transition with reason
    reason_text = "Lab cutting machine calibration delay"
    OrderFSM.transition_to(db_session, order, "PRESCRIPTION_RECEIVED", reason=reason_text)
    
    # Assert delay_reason is populated
    assert order.delay_reason == reason_text
    
    # Check the Audit Log contains the reason
    from app.models import AuditLog
    import json
    log = db_session.query(AuditLog).filter(
        AuditLog.record_id == order.id,
        AuditLog.action == "UPDATE"
    ).first()
    assert log is not None
    new_val = json.loads(log.new_value)
    assert new_val["reason"] == reason_text
