from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import PaymentCreate, PaymentVerify, PaymentResponse
from app.api.auth import get_current_user, RoleChecker
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])

role_staff_or_admin = RoleChecker(["STORE_STAFF", "LAB_TECH"])

@router.post("/create", response_model=dict, dependencies=[Depends(role_staff_or_admin)])
def create_payment_order(req: PaymentCreate, db: Session = Depends(get_db)):
    """
    Initialize a payment request with Razorpay.
    """
    try:
        data = PaymentService.create_order(db, req.order_id, req.amount)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify", response_model=dict, dependencies=[Depends(role_staff_or_admin)])
def verify_payment_signature(req: PaymentVerify, db: Session = Depends(get_db)):
    """
    Verify payment signature returned by the client-side checkout.
    """
    success = PaymentService.verify_signature(
        db, req.order_id, req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature
    )
    if not success:
        raise HTTPException(status_code=400, detail="Invalid cryptographic payment signature")
    return {"status": "success", "message": "Payment verified and recorded"}

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Asynchronous webhook handler to capture external captures, failed payments, or refunds.
    """
    payload_bytes = await request.body()
    # In production, verify signature against raw payload bytes:
    # Razorpay uses HMAC SHA256 of the payload using webhook secret
    
    import json
    try:
        payload = json.loads(payload_bytes.decode())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    handled = PaymentService.handle_webhook(db, payload, x_razorpay_signature or "")
    if not handled:
        return {"status": "unhandled_or_ignored"}
        
    return {"status": "success"}
