import random
from typing import Dict, Any, List

class TwinService:
    @staticmethod
    def simulate_order_flow(
        scenario: str, order_load: int, lab_capacity: int, vendor_reliability: float
    ) -> Dict[str, Any]:
        """
        Runs a stochastic Monte Carlo simulation representing order throughput through the lab and logistics pipelines.
        
        Scenarios:
        - "standard": Baseline operations.
        - "spike": High seasonal order volume (e.g., Black Friday).
        - "vendor_failure": Delays in importing/sourcing lenses.
        - "lab_outage": Lab staff shortage or machine calibration failure.
        """
        # Baseline stage durations (in hours)
        base_durations = {
            "validation": 2.0,
            "allocation": 1.0,
            "lab_cutting": 6.0,
            "coating": 12.0,
            "assembly": 4.0,
            "qc": 2.0,
            "shipping": 18.0
        }
        
        num_simulations = 200
        sla_breach_count = 0
        total_tat = 0.0
        stage_bottlenecks = {k: 0.0 for k in base_durations.keys()}
        
        # Load factors
        load_factor = max(1.0, order_load / 100.0)
        
        for _ in range(num_simulations):
            order_tat = 0.0
            
            for stage, base_hours in base_durations.items():
                # Apply stochastic variability
                variance = random.uniform(0.7, 1.4)
                stage_time = base_hours * variance
                
                # Apply capacity factors (queue delays)
                if stage in ["lab_cutting", "coating", "assembly"]:
                    # Spikes increase cutting/coating/assembly queue duration
                    queue_multiplier = 1.0 + (load_factor * 0.15)
                    if lab_capacity < 80:
                        # Staff shortage increases processing delay
                        queue_multiplier *= (100.0 / max(10, lab_capacity))
                    stage_time *= queue_multiplier
                    
                # Apply vendor factors
                if stage == "allocation" and random.random() > vendor_reliability:
                    # Sourcing delay if vendor fails
                    stage_time += random.uniform(24.0, 72.0)
                    
                # Scenario specific modifiers
                if scenario == "lab_outage" and stage in ["lab_cutting", "coating"]:
                    stage_time *= random.uniform(1.8, 3.0)
                elif scenario == "vendor_failure" and stage == "allocation":
                    stage_time += random.uniform(48.0, 96.0)
                elif scenario == "spike":
                    stage_time *= random.uniform(1.2, 1.8)
                    
                order_tat += stage_time
                stage_bottlenecks[stage] += stage_time
                
            # If total TAT exceeds 72 hours (3 days), consider it a breach in standard orders
            if order_tat > 72.0:
                sla_breach_count += 1
            total_tat += order_tat
            
        avg_tat = total_tat / num_simulations
        breach_rate = (sla_breach_count / num_simulations) * 100.0
        
        # Average the bottlenecks
        avg_bottlenecks = {k: round(v / num_simulations, 2) for k, v in stage_bottlenecks.items()}
        
        return {
            "scenario": scenario,
            "simulated_orders": order_load,
            "average_predicted_tat_hours": round(avg_tat, 2),
            "estimated_sla_breach_rate_pct": round(breach_rate, 2),
            "stage_breakdown_hours": avg_bottlenecks,
            "confidence_score": 95.0 if num_simulations >= 100 else 75.0
        }
