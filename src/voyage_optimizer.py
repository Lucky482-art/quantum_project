import datetime
from qpso_optimizer import QPSOOptimizer
from explainability import generate_voyage_explanation

class VoyageOptimizer:
    def __init__(self):
        self.qpso = QPSOOptimizer()

    def run_full_optimization(self, capable_fleet, routes, initial_departure_dt, w_cost, w_emis, speed_range=None):
        """
        Runs the optimizer across multiple departure times to find the safest weather window.
        Returns the absolute best plan, alternatives, and an explainable AI summary.
        """
        departure_windows = [
            {"label": "On Time", "dt": initial_departure_dt},
            {"label": "+12 Hours", "dt": initial_departure_dt + datetime.timedelta(hours=12)},
            {"label": "+24 Hours", "dt": initial_departure_dt + datetime.timedelta(hours=24)}
        ]
        
        all_window_plans = []
        
        for window in departure_windows:
            # Evaluate QPSO for this departure time window
            plans = self.qpso.optimize(
                capable_fleet, routes, window["dt"], 
                weight_cost=w_cost, weight_emission=w_emis, 
                num_particles=5, max_iter=10, top_n=5,
                speed_range=speed_range
            )
            
            for p in plans:
                p["Departure_Label"] = window["label"]
                p["Departure_Time"] = window["dt"]
                all_window_plans.append(p)
                
        # Sort all plans across all departure windows by fitness score
        all_window_plans = sorted(all_window_plans, key=lambda x: x['Fitness_Score'])
        
        if not all_window_plans:
            return None
            
        top_plan = all_window_plans[0]
        
        # Collect alternatives (unique Route/Vessel combos)
        alternatives = []
        seen = set()
        seen.add(f"{top_plan['Vessel_Index']}_{top_plan['Route_ID']}_{top_plan['Departure_Label']}")
        
        for p in all_window_plans[1:]:
            key = f"{p['Vessel_Index']}_{p['Route_ID']}_{p['Departure_Label']}"
            if key not in seen:
                seen.add(key)
                alternatives.append(p)
            if len(alternatives) >= 2: # Keep top 2 alternatives
                break
                
        # Generate explanations
        cargo_demand = top_plan.get('Cargo_Demand', 25000) # Fallback, should be injected
        cargo_type = top_plan.get('Cargo_Type', 'Unknown Cargo')
        
        explanation = generate_voyage_explanation(top_plan, alternatives, cargo_type, cargo_demand)
        
        return {
            "top_plan": top_plan,
            "alternatives": alternatives,
            "explanation": explanation,
            "all_window_plans": all_window_plans
        }
