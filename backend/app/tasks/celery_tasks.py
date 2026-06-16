import time
import logging
from celery import Celery
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Notification, Order, LensInventory
from app.config import settings
from app.services.ocr_service import OCRService
from app.ai.models_registry import registry as ml_registry

logger = logging.getLogger("celery_tasks")

# Initialize Celery app
celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

@celery_app.task
def process_prescription_ocr_task(prescription_id: int, file_path_or_bytes: bytes, filename: str):
    """
    Background Celery task to execute OCR extraction.
    """
    logger.info(f"Processing OCR for Prescription ID: {prescription_id}")
    db = SessionLocal()
    try:
        extraction = OCRService.extract_from_file(file_path_or_bytes, filename)
        
        from app.models import Prescription
        import json
        import torch
        from app.ai.transformer import model as transformer_model
        
        rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
        if rx:
            vals = extraction["parsed_values"]
            rx.sph_od = vals["sph_od"]
            rx.cyl_od = vals["cyl_od"]
            rx.axis_od = vals["axis_od"]
            rx.add_od = vals["add_od"]
            rx.sph_os = vals["sph_os"]
            rx.cyl_os = vals["cyl_os"]
            rx.axis_os = vals["axis_os"]
            rx.add_os = vals["add_os"]
            rx.pd = vals["pd"]
            rx.raw_ocr_text = extraction["raw_text"]
            
            # Generate embedding
            num_list = [
                vals["sph_od"], vals["cyl_od"], float(vals["axis_od"]), vals["add_od"],
                vals["sph_os"], vals["cyl_os"], float(vals["axis_os"]), vals["add_os"],
                vals["pd"]
            ]
            t_input = torch.tensor([num_list], dtype=torch.float32)
            emb = transformer_model.generate_embeddings(t_input).squeeze(0).tolist()
            rx.embedding = json.dumps(emb)
            
            db.commit()
            logger.info(f"Prescription {prescription_id} OCR parsing success.")
    except Exception as e:
        logger.error(f"Failed to process OCR: {e}")
    finally:
        db.close()

@celery_app.task
def send_email_notification_task(notification_id: int):
    """
    Background Celery task to send SMTP email.
    """
    db = SessionLocal()
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        db.close()
        return
        
    logger.info(f"Sending SMTP email to {notification.recipient}")
    # Simulating SMTP transmission
    try:
        # Check if dummy settings
        if settings.SMTP_PASSWORD == "mockpassword123":
            time.sleep(0.5)  # mock delay
            notification.status = "SENT"
        else:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(notification.content)
            msg['Subject'] = 'Eyewear Order Management Alert'
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = notification.recipient
            
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            notification.status = "SENT"
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        notification.status = "FAILED"
    finally:
        db.commit()
        db.close()

@celery_app.task
def send_whatsapp_notification_task(notification_id: int):
    """
    Background Celery task to send Twilio WhatsApp message.
    """
    db = SessionLocal()
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        db.close()
        return
        
    logger.info(f"Sending Twilio WhatsApp message to {notification.recipient}")
    try:
        if settings.TWILIO_ACCOUNT_SID == "ACmockaccountsid123456":
            time.sleep(0.5)  # mock delay
            notification.status = "SENT"
        else:
            # Twilio REST Client API call
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                from_=f"whatsapp:{settings.TWILIO_FROM_NUMBER}",
                body=notification.content,
                to=f"whatsapp:{notification.recipient}"
            )
            notification.status = "SENT"
    except Exception as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        notification.status = "FAILED"
    finally:
        db.commit()
        db.close()

@celery_app.task
def predict_stock_replenishment_task():
    """
    Cron / periodic task to predict inventory requirements and trigger alerts.
    """
    db = SessionLocal()
    try:
        lenses = db.query(LensInventory).all()
        for lens in lenses:
            # Predict for each low lens item
            sales_velocity = 10
            lead_time = 3
            reorder_point = 8
            
            features = [
                float(lens.quantity),
                float(sales_velocity),
                float(lead_time),
                float(reorder_point),
                float(lens.reserved_quantity)
            ]
            pred = ml_registry.predict_reorder_needs(db, features)
            if pred["urgency_score"] > 70:
                # Trigger critical low stock warning
                content = f"SMART REORDER FORECAST: Lens ID: {lens.id} ({lens.lens_type}) needs {pred['recommended_reorder_qty']} units immediately."
                notification = Notification(
                    channel="EMAIL",
                    recipient="replenishment-manager@eyewearoms.com",
                    content=content,
                    status="PENDING"
                )
                db.add(notification)
        db.commit()
    except Exception as e:
        logger.error(f"Error running nightly replenishment forecasting: {e}")
    finally:
        db.close()

@celery_app.task
def check_active_orders_sla_risk_task():
    """
    Cron / periodic task to evaluate SLA breach risk for all active orders and trigger alerts.
    """
    logger.info("Starting periodic active orders SLA risk check task...")
    db = SessionLocal()
    try:
        from app.services.tat_service import TATService
        results = TATService.predict_and_evaluate_all_active_orders(db)
        logger.info(f"Completed SLA risk check periodic task. Evaluated {len(results)} active orders.")
    except Exception as e:
        logger.error(f"Error executing active orders SLA risk check task: {e}")
    finally:
        db.close()
