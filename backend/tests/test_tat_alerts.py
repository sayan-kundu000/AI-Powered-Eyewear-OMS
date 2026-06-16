import datetime
import pytest
from sqlalchemy.orm import Session
from app.models import Order, Customer, Store, SLAHistory, Notification
from app.services.tat_service import TATService
from app.services.order_fsm import OrderFSM


def test_tat_service_average_calculations(db_session: Session):
    """
    Test that average stage durations are computed correctly from SLAHistory, 
    and fall back to default durations when history is empty.
    """
    # 1. Empty history should yield default values
    avg_durations = TATService.get_average_stage_durations(db_session)
    assert avg_durations["IN_LAB"] == 8.0
    assert avg_durations["COATING"] == 24.0

    # 2. Add history records and verify average updates
    h1 = SLAHistory(
        order_id=999,
        stage="IN_LAB",
        entered_at=datetime.datetime.utcnow() - datetime.timedelta(hours=6),
        exited_at=datetime.datetime.utcnow(),
        tat_hours=6.0,
        sla_limit_hours=8.0,
        status="ON_TIME"
    )
    h2 = SLAHistory(
        order_id=999,
        stage="IN_LAB",
        entered_at=datetime.datetime.utcnow() - datetime.timedelta(hours=10),
        exited_at=datetime.datetime.utcnow(),
        tat_hours=10.0,
        sla_limit_hours=8.0,
        status="BREACHED"
    )
    db_session.add(h1)
    db_session.add(h2)
    db_session.commit()

    avg_durations = TATService.get_average_stage_durations(db_session)
    # Average should be (6.0 + 10.0) / 2 = 8.0 hours
    assert avg_durations["IN_LAB"] == 8.0

def test_tat_service_remaining_stages():
    """
    Verify the remaining stage tracking logic for normal and failed order paths.
    """
    stages_placed = TATService.get_remaining_stages("ORDER_PLACED")
    assert "ORDER_PLACED" in stages_placed
    assert "DELIVERED" in stages_placed

    stages_failed = TATService.get_remaining_stages("QC_FAILED")
    assert stages_failed[0] == "QC_FAILED"
    assert stages_failed[1] == "REORDER"
    assert "PRESCRIPTION_VALIDATED" in stages_failed

def test_tat_predict_and_evaluate_sla_breach_and_alerts(db_session: Session):
    """
    Test that orders exceeding/likely to exceed SLA thresholds are correctly evaluated, 
    and notifications are sent exactly once without duplicates.
    """
    # Setup test customer and store
    cust = Customer(first_name="Alert", last_name="Tester", email="alert@tester.com", phone="1234567890")
    store = Store(name="Alert Test Store", location="Bangalore")
    db_session.add(cust)
    db_session.add(store)
    db_session.commit()

    # Create a new order with 2 days (48 hours) SLA, created 40 hours ago
    created_at_time = datetime.datetime.utcnow() - datetime.timedelta(hours=40)
    order = Order(
        order_number="ORD-TEST-BREACH-1",
        customer_id=cust.id,
        store_id=store.id,
        lens_type="Single Vision",
        lens_index=1.61,
        payment_status="PENDING",
        total_amount=2000.0,
        current_status="IN_LAB",
        current_sla_days=2, # 48 hours SLA
        created_at=created_at_time,
        updated_at=created_at_time
    )
    db_session.add(order)
    db_session.commit()

    # Log active SLAHistory for IN_LAB stage entered 10 hours ago
    entered_time = datetime.datetime.utcnow() - datetime.timedelta(hours=10)
    sla_hist = SLAHistory(
        order_id=order.id,
        stage="IN_LAB",
        entered_at=entered_time,
        exited_at=None,
        sla_limit_hours=8.0,
        status="ON_TIME"
    )
    db_session.add(sla_hist)
    db_session.commit()

    # Remaining stages from IN_LAB: IN_LAB, CUTTING, COATING, ASSEMBLY, QC_PENDING, PACKAGING, SHIPPED, OUT_FOR_DELIVERY, DELIVERED
    # Sum of average fallback durations for these stages is:
    # IN_LAB (8) + CUTTING (12) + COATING (24) + ASSEMBLY (6) + QC_PENDING (4) + PACKAGING (4) + SHIPPED (24) + OUT_FOR_DELIVERY (12) = 94 hours!
    # Remaining SLA hours is 48 - 40 = 8 hours!
    # Expected remaining process duration is 94 hours, which is much greater than 8 hours remaining SLA!
    
    # Run prediction and evaluate risk
    result = TATService.predict_and_evaluate_order(db_session, order)
    
    # Assert risk is High
    assert result["risk_level"] == "High"
    assert result["breach_probability"] >= 0.7
    assert order.risk_score == "High"
    assert order.breach_risk_prob >= 0.7

    # Check notification records are created for s.kundu.20020603@gmail.com and +91-9709761281
    notifs = db_session.query(Notification).filter(
        Notification.content.like(f"%{order.order_number}%")
    ).all()
    
    assert len(notifs) == 2
    
    email_alert = next(n for n in notifs if n.channel == "EMAIL")
    whatsapp_alert = next(n for n in notifs if n.channel == "WHATSAPP")

    assert email_alert.recipient == "s.kundu.20020603@gmail.com"
    assert whatsapp_alert.recipient == "+91-9709761281"
    assert "SLA BREACH ALERT" in email_alert.content
    assert "SLA BREACH ALERT" in whatsapp_alert.content

    # Run check again, verify no duplicate notifications are created
    TATService.predict_and_evaluate_order(db_session, order)
    
    notifs_after = db_session.query(Notification).filter(
        Notification.content.like(f"%{order.order_number}%")
    ).all()
    assert len(notifs_after) == 2 # still 2, no duplicates!

def test_fsm_integration_triggers_prediction(db_session: Session):
    """
    Ensure FSM transition automatically triggers TAT prediction calculations.
    """
    cust = Customer(first_name="FSM", last_name="Tester", email="fsm@tester.com", phone="999")
    store = Store(name="FSM Test Store", location="Pune")
    db_session.add(cust)
    db_session.add(store)
    db_session.commit()

    order = Order(
        order_number="ORD-TEST-FSM-1",
        customer_id=cust.id,
        store_id=store.id,
        lens_type="Single Vision",
        lens_index=1.61,
        payment_status="PENDING",
        total_amount=2000.0,
        current_status="ORDER_PLACED",
        current_sla_days=2,
        remaining_tat_hours=48.0
    )
    db_session.add(order)
    db_session.commit()
    
    # Enter initial stage history
    OrderFSM._record_sla_history_enter(db_session, order, "ORDER_PLACED")
    db_session.commit()

    # Perform transition to PRESCRIPTION_RECEIVED
    # This should trigger OrderFSM.transition_to which runs predict_and_evaluate_order
    OrderFSM.transition_to(db_session, order, "PRESCRIPTION_RECEIVED")
    
    # Check that breach_risk_prob and risk_score were updated by the transition hook
    assert order.current_status == "PRESCRIPTION_RECEIVED"
    assert order.risk_score in ["Low", "Medium", "High"]
    assert order.breach_risk_prob >= 0.0
