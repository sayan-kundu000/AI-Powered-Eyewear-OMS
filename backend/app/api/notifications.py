from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification
from app.schemas import NotificationResponse
from app.api.auth import get_current_user, RoleChecker

router = APIRouter(prefix="/notifications", tags=["Notifications"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])

@router.get("", response_model=List[NotificationResponse], dependencies=[Depends(role_staff_or_admin)])
def list_notification_history(db: Session = Depends(get_db)):
    """
    Get historic log list of Twilio WhatsApp and SMTP email transmissions.
    """
    return db.query(Notification).order_by(Notification.created_at.desc()).all()

@router.post("/trigger-breach-alert", dependencies=[Depends(role_staff_or_admin)])
def manual_trigger_breach_alert(
    order_number: str,
    channel: str = "EMAIL",
    recipient: str = "customer@example.com",
    db: Session = Depends(get_db)
):
    """
    Simulates sending an alert if the SLA breach risk score exceeds thresholds.
    """
    if channel not in ["EMAIL", "WHATSAPP"]:
        raise HTTPException(status_code=400, detail="Invalid channel. Choose EMAIL or WHATSAPP.")
        
    content = (
        f"CRITICAL BREACH WARNING: Eyewear Order {order_number} has exceeded its predicted SLA TAT "
        f"threshold. Immediate expediting requested."
    )
    
    notification = Notification(
        channel=channel,
        recipient=recipient,
        content=content,
        status="SENT"  # marked sent for sandbox simulation
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return {"status": "success", "notification_id": notification.id, "message": "Alert processed."}
