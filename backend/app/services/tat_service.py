import datetime
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Order, SLAHistory, Notification
from app.services.event_bus import event_bus

logger = logging.getLogger("tat_service")

# Fallback/default stage SLA hours defined in OrderFSM
DEFAULT_STAGE_DURATIONS = {
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

STAGE_SEQUENCE = [
    "ORDER_PLACED",
    "PRESCRIPTION_RECEIVED",
    "PRESCRIPTION_VALIDATED",
    "FRAME_ALLOCATED",
    "LENS_ALLOCATED",
    "IN_LAB",
    "CUTTING",
    "COATING",
    "ASSEMBLY",
    "QC_PENDING",
    "PACKAGING",
    "SHIPPED",
    "OUT_FOR_DELIVERY",
    "DELIVERED"
]

class TATService:
    @staticmethod
    def get_average_stage_durations(db: Session) -> dict:
        """
        Calculates average durations spent in each stage using completed SLAHistory.
        Falls back to DEFAULT_STAGE_DURATIONS when historical data is unavailable.
        """
        durations = DEFAULT_STAGE_DURATIONS.copy()
        try:
            results = db.query(SLAHistory.stage, func.avg(SLAHistory.tat_hours))\
                        .filter(SLAHistory.exited_at.isnot(None))\
                        .filter(SLAHistory.tat_hours.isnot(None))\
                        .group_by(SLAHistory.stage).all()
            for stage, avg_tat in results:
                if avg_tat is not None and avg_tat > 0:
                    durations[stage] = float(avg_tat)
        except Exception as e:
            logger.error(f"Error querying historical average durations: {e}")
        return durations

    @staticmethod
    def get_remaining_stages(current_stage: str) -> list:
        """
        Traces the remaining sequence of stages from the current stage to DELIVERED.
        """
        if current_stage == "QC_FAILED":
            return ["QC_FAILED", "REORDER"] + STAGE_SEQUENCE[STAGE_SEQUENCE.index("PRESCRIPTION_VALIDATED"):]
        if current_stage == "REORDER":
            return ["REORDER"] + STAGE_SEQUENCE[STAGE_SEQUENCE.index("PRESCRIPTION_VALIDATED"):]
            
        if current_stage in STAGE_SEQUENCE:
            idx = STAGE_SEQUENCE.index(current_stage)
            return STAGE_SEQUENCE[idx:]
        return []

    @staticmethod
    def predict_and_evaluate_order(db: Session, order: Order) -> dict:
        """
        Predicts SLA breach risk probability and risk level for a given order.
        Updates order properties and issues alerts if risk level becomes High.
        """
        if order.current_status in ["DELIVERED", "CANCELLED"]:
            return {
                "order_id": order.id,
                "status": order.current_status,
                "breach_probability": 0.0,
                "risk_level": "Low"
            }

        # 1. Get average durations from history
        avg_durations = TATService.get_average_stage_durations(db)

        # 2. Get time spent in current stage so far
        time_spent_in_current_stage = 0.0
        active_history = db.query(SLAHistory).filter(
            SLAHistory.order_id == order.id,
            SLAHistory.stage == order.current_status,
            SLAHistory.exited_at.is_(None)
        ).order_by(SLAHistory.entered_at.desc()).first()

        if active_history:
            time_spent_in_current_stage = (datetime.datetime.utcnow() - active_history.entered_at).total_seconds() / 3600.0

        # 3. Trace remaining stages and expected hours
        remaining = TATService.get_remaining_stages(order.current_status)
        if not remaining:
            return {
                "order_id": order.id,
                "breach_probability": 0.0,
                "risk_level": "Low"
            }

        current_stage = remaining[0]
        expected_current_remaining = max(0.0, avg_durations.get(current_stage, 2.0) - time_spent_in_current_stage)
        expected_subsequent_remaining = sum(avg_durations.get(s, 2.0) for s in remaining[1:] if s != "DELIVERED")
        expected_remaining_hours = expected_current_remaining + expected_subsequent_remaining

        # 4. Compare with remaining SLA hours
        deadline = order.created_at + datetime.timedelta(days=order.current_sla_days)
        remaining_sla_hours = (deadline - datetime.datetime.utcnow()).total_seconds() / 3600.0

        # 5. Calculate breach risk probability & level
        if remaining_sla_hours <= 0:
            breach_risk_prob = 1.0
            risk_score = "High"
        elif expected_remaining_hours >= remaining_sla_hours:
            breach_risk_prob = min(0.99, 0.7 + 0.3 * (expected_remaining_hours - remaining_sla_hours) / max(1.0, expected_remaining_hours))
            risk_score = "High"
        elif expected_remaining_hours >= 0.8 * remaining_sla_hours:
            breach_risk_prob = 0.4 + 0.3 * (expected_remaining_hours - 0.8 * remaining_sla_hours) / max(0.1, 0.2 * remaining_sla_hours)
            risk_score = "Medium"
        else:
            breach_risk_prob = max(0.0, min(0.4, 0.4 * expected_remaining_hours / max(1.0, 0.8 * remaining_sla_hours)))
            risk_score = "Low"

        # 6. Save back to the Order model
        order.breach_risk_prob = breach_risk_prob
        order.risk_score = risk_score
        order.remaining_tat_hours = remaining_sla_hours
        db.commit()

        # 7. Check if we need to send a breach alert
        if risk_score == "High":
            TATService._check_and_trigger_alerts(db, order, expected_remaining_hours, remaining_sla_hours)

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "expected_remaining_hours": round(expected_remaining_hours, 2),
            "remaining_sla_hours": round(remaining_sla_hours, 2),
            "breach_probability": round(breach_risk_prob, 2),
            "risk_level": risk_score
        }

    @staticmethod
    def _check_and_trigger_alerts(db: Session, order: Order, expected_remaining_hours: float, remaining_sla_hours: float):
        """
        Helper method to create notification logs and queue them via Celery.
        Prevents duplicate alerts for the same order.
        """
        alert_prefix = f"SLA BREACH ALERT: Order {order.order_number}"
        
        # Look for existing alert for this order to avoid spamming
        existing_alert = db.query(Notification).filter(
            Notification.content.like(f"{alert_prefix}%")
        ).first()

        if existing_alert:
            return

        content = (
            f"SLA BREACH ALERT: Order {order.order_number} is highly likely to breach its SLA! "
            f"Current Stage: {order.current_status}. "
            f"Expected remaining process duration: {expected_remaining_hours:.1f} hours. "
            f"Remaining SLA duration: {remaining_sla_hours:.1f} hours."
        )

        # 1. Create Email alert
        email_notif = Notification(
            channel="EMAIL",
            recipient="s.kundu.20020603@gmail.com",
            content=content,
            status="PENDING"
        )
        db.add(email_notif)

        # 2. Create WhatsApp alert
        whatsapp_notif = Notification(
            channel="WHATSAPP",
            recipient="+91-9709761281",
            content=content,
            status="PENDING"
        )
        db.add(whatsapp_notif)
        db.commit()

        db.refresh(email_notif)
        db.refresh(whatsapp_notif)

        # 3. Publish to WebSocket dashboard updates channel in real-time
        event_bus.publish("SLABreachRiskAlert", {
            "order_id": order.id,
            "order_number": order.order_number,
            "breach_risk_prob": round(order.breach_risk_prob, 2),
            "risk_score": order.risk_score,
            "message": f"Order {order.order_number} is likely to breach its SLA! Expected remaining: {expected_remaining_hours:.1f}h, remaining SLA: {remaining_sla_hours:.1f}h."
        })

        # 4. Check if Redis is up to determine queueing vs sync fallback
        redis_up = False
        try:
            import redis
            from app.config import settings
            r = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
            r.ping()
            redis_up = True
        except Exception:
            redis_up = False

        from app.tasks.celery_tasks import send_email_notification_task, send_whatsapp_notification_task
        if redis_up:
            try:
                send_email_notification_task.delay(email_notif.id)
                send_whatsapp_notification_task.delay(whatsapp_notif.id)
                logger.info(f"Successfully queued Celery alert tasks for order: {order.order_number}")
            except Exception as e:
                logger.error(f"Failed to queue celery alert tasks: {e}. Falling back to sync execution...")
                try:
                    send_email_notification_task(email_notif.id)
                    send_whatsapp_notification_task(whatsapp_notif.id)
                except Exception as sync_ex:
                    logger.error(f"Sync fallback failed: {sync_ex}")
        else:
            logger.info(f"Redis is down. Running SMTP/WhatsApp alerts synchronously...")
            try:
                send_email_notification_task(email_notif.id)
                send_whatsapp_notification_task(whatsapp_notif.id)
            except Exception as sync_ex:
                logger.error(f"Synchronous alert execution failed: {sync_ex}")

    @staticmethod
    def predict_and_evaluate_all_active_orders(db: Session) -> list:
        """
        Utility method to run prediction evaluations for all active orders.
        """
        active_orders = db.query(Order).filter(
            Order.current_status.notin_(["DELIVERED", "CANCELLED"])
        ).all()
        
        results = []
        for order in active_orders:
            res = TATService.predict_and_evaluate_order(db, order)
            results.append(res)
        return results
