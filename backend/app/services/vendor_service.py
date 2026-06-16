from sqlalchemy.orm import Session
from app.models import VendorPerformance
from typing import List, Dict, Any

class VendorService:
    @staticmethod
    def get_recommendations(db: Session) -> List[Dict[str, Any]]:
        """
        Rank vendors based on a multi-factor score:
        Score = (Reliability * 0.4) + (Performance History * 0.3) - (SLA Days * 2.0) - (Cost * 0.1)
        Returns the sorted list of vendors with scores and categorization.
        """
        vendors = db.query(VendorPerformance).all()
        if not vendors:
            return []
            
        recommendations = []
        for v in vendors:
            # Multi-factor score formulation
            score = (
                (v.reliability_score * 0.4) +
                (v.performance_history_score * 0.3) -
                (v.sla_days * 2.5) -
                (v.cost * 0.05)
            )
            
            recommendations.append({
                "id": v.id,
                "vendor_name": v.vendor_name,
                "cost": v.cost,
                "sla_days": v.sla_days,
                "reliability_score": v.reliability_score,
                "performance_history_score": v.performance_history_score,
                "score": round(score, 2)
            })
            
        # Sort by score descending
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        return recommendations
