import numpy as np
import pandas as pd
import joblib
import os
import datetime
from emission_calc import calculate_emissions, calculate_fuel_cost
from weather_api import get_marine_forecast, get_weather_at_time
from weather_survivability import evaluate_vessel_weather_risk

class QPSOOptimizer:
    def __init__(self, model_path=None):
        if model_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_path = os.path.join(base_dir, 'models', 'xgb_fuel_model.pkl')
            
        model_data = joblib.load(model_path)
        self.model = model_data['model']
        self.features = model_data['features']
        self.bounds = [(10.0, 24.0)]
        self.fuel_types = ['HFO', 'LNG', 'Methanol']

    def fetch_route_weather_cache(self, routes):
        from concurrent.futures import ThreadPoolExecutor
        route_weather_cache = {}
        
        for r in routes:
            route_weather_cache[r['route_id']] = [None] * len(r['waypoints'])
            
        def fetch_wp(r_idx, wp_idx, lat, lon):
            # Rounding to 1 decimal place dramatically increases cache hits while preserving weather accuracy
            return r_idx, wp_idx, get_marine_forecast(round(lat, 1), round(lon, 1))
            
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for r_idx, r in enumerate(routes):
                for wp_idx, wp in enumerate(r['waypoints']):
                    futures.append(executor.submit(fetch_wp, r_idx, wp_idx, wp['lat'], wp['lon']))
                    
            for future in futures:
                r_idx, wp_idx, forecast = future.result()
                route_id = routes[r_idx]['route_id']
                route_weather_cache[route_id][wp_idx] = forecast
                
        return route_weather_cache

    def objective_function(self, speed, df_input, fuel, dist_km, weight_cost, weight_emission, weather_risk_score):
        # Update speed in the pre-allocated dataframe (avoids expensive pd.DataFrame instantiation in loop)
        df_input['SOG'] = speed
        predicted_tpd = self.model.predict(df_input)[0]
        
        dist_nm = dist_km * 0.539957
        voyage_days = dist_nm / (speed * 24)
        total_fuel = predicted_tpd * voyage_days
        
        cost = calculate_fuel_cost(total_fuel, fuel)
        emissions = calculate_emissions(total_fuel, fuel)
        
        # Heavy penalty for unsafe weather routes
        risk_penalty = 0
        if weather_risk_score >= 85:
            risk_penalty = 1000  # SEVERE
        elif weather_risk_score >= 60:
            risk_penalty = 100   # HIGH
        elif weather_risk_score >= 30:
            risk_penalty = 10    # MODERATE
            
        fitness = (weight_cost * (cost / 100000)) + (weight_emission * (emissions / 1000)) + risk_penalty
        return fitness, cost, emissions, total_fuel, voyage_days

    def optimize(self, vessels_df, routes, departure_dt, weight_cost=0.5, weight_emission=0.5, num_particles=10, max_iter=20, top_n=3, speed_range=None):
        # Prefetch weather forecasts for the geographic routes
        route_cache = self.fetch_route_weather_cache(routes)
        all_plans = []
        
        for idx, vessel in vessels_df.iterrows():
            for r in routes:
                route_id = r['route_id']
                dist_km = r['total_distance_km']
                
                # Estimate Weather Risk Baseline for this Vessel + Route
                # Assume 15 knots nominal speed to generate ETA timeline
                timeline = []
                for i, wp in enumerate(r['waypoints']):
                    hours = (wp['dist_from_start_km'] * 0.539957) / 15.0
                    eta = departure_dt + datetime.timedelta(hours=hours)
                    
                    wp_forecast = route_cache[route_id][i]
                    weather_at_eta = get_weather_at_time(wp_forecast, eta)
                    if not weather_at_eta:
                        weather_at_eta = {'wind_speed_kmh': 15.0, 'wave_height_m': 1.0}
                        
                    weather_at_eta['segment_id'] = i
                    weather_at_eta['timestamp'] = eta
                    timeline.append(weather_at_eta)
                    
                risk_eval = evaluate_vessel_weather_risk(vessel, timeline)
                
                best_fuel_fitness = float('inf')
                best_fuel_plan = None
                
                for fuel in self.fuel_types:
                    # Pre-allocate DataFrame for ML model to speed up predictions by 100x
                    baseline_input = {f: 0 for f in self.features}
                    baseline_input['VesselType'] = 70
                    baseline_input['Length'] = vessel['length']
                    baseline_input['Width'] = vessel['width']
                    baseline_input['Draft'] = float(vessel.get('dwt', 50000))/10000 + 5
                    baseline_input['Cargo'] = float(vessel.get('dwt', 50000))
                    
                    fuel_col = f"Fuel_Type_{fuel}"
                    if fuel_col in baseline_input:
                        baseline_input[fuel_col] = 1
                    df_input = pd.DataFrame([baseline_input])
                    
                    b_min, b_max = speed_range if speed_range else self.bounds[0]
                    
                    if b_min == b_max:
                        # Skip QPSO and use exact manual speed if bounds are identical
                        gbest_speed = float(b_min)
                        gbest_fitness, f_cost, f_emis, f_fuel, f_days = self.objective_function(
                            gbest_speed, df_input, fuel, dist_km, weight_cost, weight_emission, risk_eval['overall_risk_score']
                        )
                        best_fuel_fitness = gbest_fitness
                    else:
                        # QPSO Speed Optimization
                        particles_speed = np.random.uniform(b_min, b_max, num_particles)
                        pbest_speed = np.copy(particles_speed)
                        pbest_fitness = np.full(num_particles, float('inf'))
                        
                        gbest_speed = particles_speed[0]
                        gbest_fitness = float('inf')
                        
                        for t in range(max_iter):
                            for i in range(num_particles):
                                fitness, _, _, _, _ = self.objective_function(
                                    particles_speed[i], df_input, fuel, dist_km, weight_cost, weight_emission, risk_eval['overall_risk_score']
                                )
                                if fitness < pbest_fitness[i]:
                                    pbest_fitness[i] = fitness
                                    pbest_speed[i] = particles_speed[i]
                                if fitness < gbest_fitness:
                                    gbest_fitness = fitness
                                    gbest_speed = particles_speed[i]
                                    
                            mbest = np.mean(pbest_speed)
                            alpha = 1.0 - 0.5 * (t / max_iter)
                            for i in range(num_particles):
                                phi = np.random.rand()
                                p = phi * pbest_speed[i] + (1 - phi) * gbest_speed
                                u = np.random.rand()
                                L = alpha * abs(mbest - particles_speed[i])
                                if np.random.rand() > 0.5:
                                    particles_speed[i] = p + L * np.log(1 / u)
                                else:
                                    particles_speed[i] = p - L * np.log(1 / u)
                                particles_speed[i] = np.clip(particles_speed[i], b_min, b_max)
                        
                        if gbest_fitness < best_fuel_fitness:
                            best_fuel_fitness = gbest_fitness
                            _, f_cost, f_emis, f_fuel, f_days = self.objective_function(
                                gbest_speed, df_input, fuel, dist_km, weight_cost, weight_emission, risk_eval['overall_risk_score']
                            )
                            
                    if best_fuel_fitness != float('inf'):
                        best_fuel_plan = {
                            'Vessel_Index': idx,
                            'Vessel_Name': vessel.get('ship_name', f'Vessel_{idx}'),
                            'Vessel_Type': vessel.get('Vessel_Type', 'Unknown'),
                            'Route_ID': route_id,
                            'Route_Distance_km': round(dist_km, 1),
                            'Optimal_Speed_Range_Knots': f"{round(gbest_speed-0.5, 1)} - {round(gbest_speed+0.5, 1)}",
                            'Target_Speed_Knots': round(gbest_speed, 2),
                            'Optimal_Fuel_Type': fuel,
                            'Predicted_Fuel_Tonnes': round(f_fuel, 2),
                            'Voyage_Duration_Days': round(f_days, 2),
                            'Total_Cost_USD': round(f_cost, 2),
                            'Total_CO2_Emissions_Tonnes': round(f_emis, 2),
                            'Fitness_Score': round(gbest_fitness, 4),
                            'Weather_Risk_Score': risk_eval['overall_risk_score'],
                            'Weather_Risk_Level': risk_eval['overall_risk_level'],
                            'Weather_Warnings': risk_eval['warnings'],
                            'Timeline': risk_eval['segment_details']
                        }
                
                if best_fuel_plan:
                    all_plans.append(best_fuel_plan)
                    
        all_plans = sorted(all_plans, key=lambda x: x['Fitness_Score'])
        return all_plans[:top_n]
