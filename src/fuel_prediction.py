import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os

def train_fuel_model():
    print("Loading training data...")
    df = pd.read_csv('../data/training_data.csv')
    
    # Define features and target
    features = ['VesselType', 'Length', 'Width', 'Draft', 'Cargo', 'SOG', 'Fuel_Type']
    target = 'Fuel_Consumption_tpd'
    
    # We need to one-hot encode the categorical 'Fuel_Type' feature
    X = pd.get_dummies(df[features], columns=['Fuel_Type'])
    y = df[target]
    
    print(f"Features: {X.columns.tolist()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training XGBoost Regressor...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    predictions = model.predict(X_test)
    mse = mean_squared_error(y_test, predictions)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, predictions)
    
    print(f"Model Evaluation -> RMSE: {rmse:.4f}, R-squared: {r2:.4f}")
    
    # Save the model and the feature names used for training
    os.makedirs('../models', exist_ok=True)
    model_data = {
        'model': model,
        'features': X.columns.tolist()
    }
    joblib.dump(model_data, '../models/xgb_fuel_model.pkl')
    print("Model saved to models/xgb_fuel_model.pkl")

if __name__ == "__main__":
    train_fuel_model()
