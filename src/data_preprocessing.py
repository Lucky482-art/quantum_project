import pandas as pd
import numpy as np
import os

def preprocess_data():
    print("Loading AIS dataset...")
    # Load a subset to keep training fast for the MVP prototype
    df = pd.read_csv('../data/processed_AIS_dataset.csv', nrows=200000)
    
    # Filter valid sailing conditions
    df = df[(df['SOG'] > 5) & (df['SOG'] < 25)]  # Speed between 5 and 25 knots
    df = df[df['dist_km'] > 10]
    df = df[df['Draft'] > 2]
    df = df[df['Length'] > 50]
    
    # Select features
    features = ['VesselType', 'Length', 'Width', 'Draft', 'Cargo', 'SOG', 'dist_km']
    df = df[features].copy()
    
    print("Engineering Target Variables...")
    # Engineer 'Fuel_Type' (Randomly assigned for the prototype)
    np.random.seed(42)
    fuel_types = ['HFO', 'LNG', 'Methanol']
    df['Fuel_Type'] = np.random.choice(fuel_types, size=len(df), p=[0.7, 0.2, 0.1])
    
    # Engineer 'Fuel_Consumption_tpd' (Tonnes Per Day)
    # Using Admiralty formula approximation: Fuel ~ Displacement^(2/3) * Speed^3
    # Displacement approx = L * W * Draft * 0.7 (Block coefficient)
    displacement = df['Length'] * df['Width'] * df['Draft'] * 0.7
    
    # Base constant to scale it to realistic values (e.g., 50-150 tpd for large vessels)
    k_constant = 0.000002
    
    # Different fuel types have different energy densities affecting consumption volume
    # HFO is baseline. LNG has higher energy density (need less mass). Methanol has lower (need more mass).
    efficiency_multiplier = {'HFO': 1.0, 'LNG': 0.85, 'Methanol': 2.1}
    df['Efficiency_Mult'] = df['Fuel_Type'].map(efficiency_multiplier)
    
    # Calculate fuel consumption in tonnes per day
    df['Fuel_Consumption_tpd'] = k_constant * (displacement**(2/3)) * (df['SOG']**3) * df['Efficiency_Mult']
    
    # Add some noise to make it realistic for ML
    noise = np.random.normal(1.0, 0.05, len(df))
    df['Fuel_Consumption_tpd'] = df['Fuel_Consumption_tpd'] * noise
    
    # Calculate total fuel for the voyage (dist_km to nautical miles / speed / 24)
    df['dist_nm'] = df['dist_km'] * 0.539957
    df['Voyage_Days'] = df['dist_nm'] / (df['SOG'] * 24)
    df['Total_Fuel_Consumption'] = df['Fuel_Consumption_tpd'] * df['Voyage_Days']
    
    # Drop temp columns
    df = df.drop(columns=['Efficiency_Mult', 'dist_nm', 'Voyage_Days'])
    
    # Clean any NaNs
    df = df.dropna()
    
    print(f"Dataset processed. Shape: {df.shape}")
    print(df.head())
    
    # Save training dataset
    df.to_csv('../data/training_data.csv', index=False)
    print("Saved to data/training_data.csv")

if __name__ == "__main__":
    preprocess_data()
