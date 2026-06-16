import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Order
from app.services.tat_service import TATService

logging.basicConfig(level=logging.INFO)

def main():
    print("Evaluating SLA Breach risks for active orders in the database...")
    db = SessionLocal()
    try:
        # Run prediction evaluations for all active orders
        results = TATService.predict_and_evaluate_all_active_orders(db)
        print(f"Successfully evaluated {len(results)} active orders.")
        
        high_risk_orders = [r for r in results if r["risk_level"] == "High"]
        print(f"Total High Risk orders flagged: {len(high_risk_orders)}")
        
        for r in high_risk_orders:
            print(f" - Order {r['order_number']}: expected remaining {r['expected_remaining_hours']}h, SLA remaining {r['remaining_sla_hours']}h")
    except Exception as e:
        print(f"Failed to execute evaluations: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
