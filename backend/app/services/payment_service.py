import hmac
import hashlib
import logging
import requests
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Payment, Order
from app.services.event_bus import event_bus

logger = logging.getLogger("payment_service")

class PaymentService:
    @staticmethod
    def create_order(db: Session, order_id: int, amount: float) -> dict:
        """
        Creates a Razorpay Order. Falls back to mock order details if not configured.
        """
        url = "https://api.razorpay.com/v1/orders"
        auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET)
        
        payload = {
            "amount": int(amount * 100),  # Razorpay expects amount in paise
            "currency": "INR",
            "receipt": f"receipt_order_{order_id}",
            "notes": {
                "order_id": str(order_id)
            }
        }

        # Check if using mock key
        if settings.RAZORPAY_KEY_ID == "rzp_test_mockkeyid123":
            logger.info("Using Mock Razorpay credentials.")
            mock_id = f"order_mock_{order_id}xyz"
            # Create a pending payment log in the DB
            payment = Payment(
                order_id=order_id,
                amount=amount,
                payment_gateway="Razorpay",
                transaction_id=mock_id,
                status="PENDING"
            )
            db.add(payment)
            db.commit()
            return {"id": mock_id, "amount": amount, "currency": "INR", "status": "created"}

        try:
            response = requests.post(url, json=payload, auth=auth, timeout=10)
            if response.status_code == 200:
                data = response.json()
                payment = Payment(
                    order_id=order_id,
                    amount=amount,
                    payment_gateway="Razorpay",
                    transaction_id=data["id"],
                    status="PENDING"
                )
                db.add(payment)
                db.commit()
                return data
            else:
                logger.error(f"Razorpay order creation failed: {response.text}")
                raise Exception(f"Razorpay Error: {response.text}")
        except Exception as e:
            logger.error(f"Error communicating with Razorpay: {e}")
            raise Exception("Payment gateway error.")

    @staticmethod
    def verify_signature(
        db: Session, order_id: int, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str
    ) -> bool:
        """
        Verify Razorpay cryptographic signature.
        """
        # If mock credentials, verify automatically
        if settings.RAZORPAY_KEY_ID == "rzp_test_mockkeyid123":
            logger.info("Mock payment verification success.")
            PaymentService._mark_order_paid(db, order_id, razorpay_payment_id)
            return True

        msg = f"{razorpay_order_id}|{razorpay_payment_id}"
        generated_signature = hmac.new(
            settings.RAZORPAY_SECRET.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(generated_signature, razorpay_signature):
            PaymentService._mark_order_paid(db, order_id, razorpay_payment_id)
            return True
            
        logger.warning("Razorpay Signature mismatch!")
        return False

    @staticmethod
    def handle_webhook(db: Session, webhook_payload: dict, stripe_sig: str) -> bool:
        """
        Handle Razorpay payment webhooks.
        """
        # Razorpay payload usually has an event: payment.captured, payment.failed
        event = webhook_payload.get("event")
        entity = webhook_payload.get("payload", {}).get("payment", {}).get("entity", {})
        
        razorpay_payment_id = entity.get("id")
        razorpay_order_id = entity.get("order_id")
        amount = entity.get("amount", 0) / 100.0
        
        # Look up matching payment record
        payment = db.query(Payment).filter(Payment.transaction_id == razorpay_order_id).first()
        if not payment:
            # Try finding order by notes if order_id is in there
            order_id = entity.get("notes", {}).get("order_id")
            if order_id:
                payment = db.query(Payment).filter(Payment.order_id == int(order_id)).first()

        if payment:
            if event == "payment.captured":
                payment.status = "SUCCESS"
                payment.transaction_id = razorpay_payment_id
                PaymentService._mark_order_paid(db, payment.order_id, razorpay_payment_id)
            elif event == "payment.failed":
                payment.status = "FAILED"
                order = db.query(Order).filter(Order.id == payment.order_id).first()
                if order:
                    order.payment_status = "FAILED"
            db.commit()
            return True
            
        return False

    @staticmethod
    def _mark_order_paid(db: Session, order_id: int, tx_id: str):
        order = db.query(Order).filter(Order.id == order_id).first()
        if order:
            order.payment_status = "PAID"
            # Move state forward to FRAME_ALLOCATED or LENS_ALLOCATED
            from app.services.order_fsm import OrderFSM
            
            # Record payment success in payment logs
            payment = db.query(Payment).filter(Payment.order_id == order_id).first()
            if payment:
                payment.status = "SUCCESS"
                payment.transaction_id = tx_id
                
            db.commit()
            
            # Emit event
            event_bus.publish("PaymentProcessed", {
                "order_id": order_id,
                "amount": order.total_amount,
                "status": "PAID"
            })
            
            # Transition state machine
            try:
                # If prescription exists and is validated, go to FRAME_ALLOCATED
                if order.prescription_id:
                    OrderFSM.transition_to(db, order, "PRESCRIPTION_RECEIVED", reason="Payment success")
                    OrderFSM.transition_to(db, order, "PRESCRIPTION_VALIDATED", reason="Prescription auto-validated")
            except Exception as e:
                logger.error(f"FSM transition after payment failed: {e}")
