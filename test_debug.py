import sys
import os
sys.path.append(os.path.abspath('src'))
import pandas as pd
import datetime
from map_module import generate_routes
from qpso_optimizer import QPSOOptimizer

def test_debug():
    src = (18.94, 72.83)
    dest = (1.27, 103.80)
    
    print("Generating routes...")
    routes = generate_routes(src, dest)
    
    print("Loading fleet...")
    fleet = pd.read_csv('data/Cleaned_ships_data.csv')
    fleet['Cargo'] = pd.to_numeric(fleet['dwt'], errors='coerce')
    fleet['Length'] = pd.to_numeric(fleet['length'], errors='coerce')
    fleet['Width'] = pd.to_numeric(fleet['width'], errors='coerce')
    fleet = fleet.dropna(subset=['Cargo', 'Length', 'Width'])
    
    # Filter for Tankers
    tankers = fleet[fleet['Vessel_Type'] == 'Tanker ships'].head(1)
    
    dep_dt = datetime.datetime.now()
    
    opt = QPSOOptimizer()
    print("Running optimize...")
    
    # We will instrument QPSOOptimizer.optimize to see what is failing
    plans = opt.optimize(tankers, routes, dep_dt, top_n=1, num_particles=5, max_iter=10)
    
    if plans:
        print(f"Found {len(plans)} plans.")
    else:
        print("No plans found.")

if __name__ == '__main__':
    test_debug()
