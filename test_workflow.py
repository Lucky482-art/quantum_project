import sys
import os
sys.path.append(os.path.abspath('src'))
import pandas as pd
import datetime
from map_module import generate_routes
from qpso_optimizer import QPSOOptimizer

def run_tests():
    print("--- Test 1: Liquid Cargo Routing ---")
    src = (18.94, 72.83)
    dest = (1.27, 103.80)
    
    routes = generate_routes(src, dest)
    print(f"Generated {len(routes)} routes.")
    
    fleet = pd.read_csv('data/Cleaned_ships_data.csv')
    fleet['Cargo'] = pd.to_numeric(fleet['dwt'], errors='coerce')
    fleet['Length'] = pd.to_numeric(fleet['length'], errors='coerce')
    fleet['Width'] = pd.to_numeric(fleet['width'], errors='coerce')
    fleet = fleet.dropna(subset=['Cargo', 'Length', 'Width'])
    
    # Filter for Tankers
    tankers = fleet[fleet['Vessel_Type'] == 'Tanker ships'].head(3)
    print(f"Found {len(tankers)} tankers.")
    
    dep_dt = datetime.datetime.now()
    
    opt = QPSOOptimizer()
    plans = opt.optimize(tankers, routes, dep_dt, top_n=1)
    
    if plans:
        p = plans[0]
        print(f"Top Plan: {p['Vessel_Name']} on {p['Route_ID']}")
        print(f"Risk: {p['Weather_Risk_Level']}")
        for seg in p['Timeline']:
            print(f"  ETA: {seg['timestamp']} | Risk: {seg['risk_level']} | Wave: {seg['wave_height_m']}m")
    else:
        print("No plans found.")
        
if __name__ == '__main__':
    run_tests()
