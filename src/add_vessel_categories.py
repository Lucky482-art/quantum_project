import pandas as pd
import os

def enhance_vessel_data():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(base_dir, 'data', 'Cleaned_ships_data.csv')
    output_path = os.path.join(base_dir, 'data', 'enhanced_ships_data.csv')
    
    print(f"Reading data from: {input_path}")
    df = pd.read_csv(input_path)
    
    # Ensure columns exist
    df['dwt'] = pd.to_numeric(df.get('dwt', 0), errors='coerce').fillna(0)
    df['length'] = pd.to_numeric(df.get('length', 0), errors='coerce').fillna(0)
    
    # Categorize based on rules
    def categorize(row):
        # MVP Rules for deterministic categorization based on ship features
        # If it's already set in the dataset (due to previous manual tests), preserve it if valid
        existing = row.get('Vessel_Type', '')
        if pd.notna(existing) and existing in [
            "Container ships", "Bulk carriers", "Tanker ships", 
            "RoRo ships", "General cargo ships", "Reefer ships"
        ]:
            return existing
            
        name = str(row.get('ship_name', '')).upper()
        dwt = row['dwt']
        
        if 'TANK' in name or 'LNG' in name or 'OIL' in name:
            return 'Tanker ships'
        elif 'CONTAINER' in name or 'BOX' in name:
            return 'Container ships'
        elif 'BULK' in name or 'STAR' in name:
            return 'Bulk carriers'
        elif 'RORO' in name or 'CAR' in name or 'AUTO' in name:
            return 'RoRo ships'
        elif 'REEF' in name or 'COOL' in name or 'ICE' in name:
            return 'Reefer ships'
        
        # Fallback to characteristics
        if dwt > 150000:
            return 'Bulk carriers'
        elif dwt > 80000:
            return 'Tanker ships'
        elif dwt > 40000:
            return 'Container ships'
        elif dwt > 20000:
            return 'RoRo ships'
        elif dwt > 10000:
            return 'Reefer ships'
        else:
            return 'General cargo ships'
            
    df['Vessel_Type'] = df.apply(categorize, axis=1)
    
    # Inject one ultra-large MVP ship per category to prevent "Too Big to Sail" bugs
    ultra_ships = [
        {"Company_Name": "SIH Demo Fleet", "ship_name": "Mega Tanker", "built_year": 2023, "gt": 200000, "dwt": 350000, "length": 350, "width": 60, "Vessel_Type": "Tanker ships"},
        {"Company_Name": "SIH Demo Fleet", "ship_name": "Mega Container", "built_year": 2023, "gt": 200000, "dwt": 350000, "length": 350, "width": 60, "Vessel_Type": "Container ships"},
        {"Company_Name": "SIH Demo Fleet", "ship_name": "Mega Bulk", "built_year": 2023, "gt": 200000, "dwt": 350000, "length": 350, "width": 60, "Vessel_Type": "Bulk carriers"},
        {"Company_Name": "SIH Demo Fleet", "ship_name": "Mega RoRo", "built_year": 2023, "gt": 150000, "dwt": 350000, "length": 300, "width": 55, "Vessel_Type": "RoRo ships"},
        {"Company_Name": "SIH Demo Fleet", "ship_name": "Mega General Cargo", "built_year": 2023, "gt": 100000, "dwt": 350000, "length": 250, "width": 45, "Vessel_Type": "General cargo ships"},
        {"Company_Name": "SIH Demo Fleet", "ship_name": "Mega Reefer", "built_year": 2023, "gt": 120000, "dwt": 350000, "length": 260, "width": 48, "Vessel_Type": "Reefer ships"},
    ]
    
    df_ultra = pd.DataFrame(ultra_ships)
    df_combined = pd.concat([df_ultra, df], ignore_index=True)
    
    print(f"Writing enhanced data to: {output_path}")
    df_combined.to_csv(output_path, index=False)
    
    print("\nFleet Breakdown:")
    print(df_combined['Vessel_Type'].value_counts())
    
if __name__ == '__main__':
    enhance_vessel_data()
