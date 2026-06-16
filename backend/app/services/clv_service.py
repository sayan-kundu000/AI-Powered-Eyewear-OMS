import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Customer, Order

class CLVService:
    @staticmethod
    def recalculate_clv(db: Session, customer_id: int) -> Customer:
        """
        Recalculate the Recency-Frequency-Monetary (RFM) metrics and CLV score for a single customer.
        """
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise ValueError("Customer not found.")
            
        # Get customer orders
        orders = db.query(Order).filter(
            Order.customer_id == customer_id,
            Order.payment_status == "PAID"
        ).all()
        
        if not orders:
            customer.purchase_frequency = 0
            customer.total_spent = 0.0
            customer.clv_score = 0.0
            customer.clv_category = "Bronze"
            db.commit()
            return customer
            
        # 1. Total spent (Monetary value)
        total_spent = sum(o.total_amount for o in orders)
        
        # 2. Purchase frequency (Frequency value)
        frequency = len(orders)
        
        # 3. Recency (Recency value: days since last purchase)
        last_order = max(o.created_at for o in orders)
        days_since_last = (datetime.datetime.utcnow() - last_order).days
        
        # Normalize Recency, Frequency, Monetary to construct CLV score
        # Recency score (decays over time)
        r_score = max(0, 100 - (days_since_last * 0.5))
        f_score = min(100, frequency * 20)  # capped at 5 orders for max frequency score
        m_score = min(100, total_spent / 100) # capped at 10,000 INR spending
        
        # Weighted CLV score
        clv_score = (r_score * 0.2) + (f_score * 0.4) + (m_score * 0.4)
        
        # Update customer table
        customer.total_spent = total_spent
        customer.purchase_frequency = frequency
        customer.clv_score = round(clv_score, 2)
        
        # Determine Category
        if clv_score >= 80:
            customer.clv_category = "Platinum"
        elif clv_score >= 55:
            customer.clv_category = "Gold"
        elif clv_score >= 30:
            customer.clv_category = "Silver"
        else:
            customer.clv_category = "Bronze"
            
        db.commit()
        db.refresh(customer)
        return customer

    @staticmethod
    def batch_update_all_clv(db: Session):
        """
        Runs CLV recalculations for all customers in the database.
        """
        customers = db.query(Customer).all()
        for c in customers:
            CLVService.recalculate_clv(db, c.id)
