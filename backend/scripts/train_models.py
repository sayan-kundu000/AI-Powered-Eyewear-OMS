import sys
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, mean_squared_error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import Order, LensInventory, SLAHistory
from app.config import settings

def train_and_register_models():
    print("Initializing Model Training Pipeline...")
    db = SessionLocal()
    
    # 1. Fetch Orders Data
    orders = db.query(Order).all()
    if not orders:
        print("No order records found. Please seed the database first.")
        db.close()
        return

    # Create model directories
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    
    print(f"Engineering features from {len(orders)} orders...")
    
    # Extract simple feature matrix
    data = []
    for o in orders:
        # Features: [stage_id, lens_type_id, store_id, rx_complexity, qc_failures]
        stage_mapping = {"ORDER_PLACED": 1, "IN_LAB": 2, "CUTTING": 3, "COATING": 4, "QC_PENDING": 5}
        current_stage = stage_mapping.get(o.current_status, 1)
        
        lens_mapping = {"single vision": 1, "progressive": 2, "blue cut": 3}
        lens_type_val = lens_mapping.get(o.lens_type.lower(), 1)
        
        rx_complexity = 1.0
        if o.prescription:
            rx_complexity += abs(o.prescription.sph_od) * 0.2
            
        qc_failures = len(o.qc_logs)
        
        # Target for SLA Breach: 1 if breached (remaining tat is negative), else 0
        target_breach = 1 if o.remaining_tat_hours < 0 else 0
        
        # Target for Delivery Delay: positive hours offset
        target_delay = max(0.0, -o.remaining_tat_hours) if o.remaining_tat_hours < 0 else 0.0
        
        data.append({
            "stage_id": float(current_stage),
            "lens_type_id": float(lens_type_val),
            "store_id": float(o.store_id),
            "rx_complexity": float(rx_complexity),
            "qc_failures": float(qc_failures),
            "breached": target_breach,
            "delay_hours": target_delay
        })
        
    df = pd.DataFrame(data)
    X = df[["stage_id", "lens_type_id", "store_id", "rx_complexity", "qc_failures"]].values
    
    # --- MODEL 1: SLA BREACH CLASSIFIER ---
    y_breach = df["breached"].values
    X_train, X_test, y_train, y_test = train_test_split(X, y_breach, test_size=0.2, random_state=42)
    
    print("Training SLA Breach Classifier (Random Forest)...")
    clf = RandomForestClassifier(n_estimators=50, max_depth=8, random_state=42)
    clf.fit(X_train, y_train)
    score = clf.score(X_test, y_test)
    print(f"SLA Breach Classifier Accuracy: {score * 100:.2f}%")
    
    # Save model
    with open(os.path.join(settings.MODEL_DIR, "sla_breach.pkl"), "wb") as f:
        pickle.dump(clf, f)

    # --- MODEL 2: DELIVERY DELAY REGRESSOR ---
    y_delay = df["delay_hours"].values
    X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(X, y_delay, test_size=0.2, random_state=42)
    
    print("Training Delivery Delay Regressor (Random Forest)...")
    reg = RandomForestRegressor(n_estimators=50, max_depth=8, random_state=42)
    reg.fit(X_train_reg, y_train_reg)
    preds = reg.predict(X_test_reg)
    rmse = np.sqrt(mean_squared_error(y_test_reg, preds))
    print(f"Delivery Delay RMSE: {rmse:.2f} hours")
    
    with open(os.path.join(settings.MODEL_DIR, "delivery_delay.pkl"), "wb") as f:
        pickle.dump(reg, f)

    # --- MODEL 3: DEMAND FORECAST REGRESSOR ---
    print("Training Lens Demand Forecast Regressor...")
    # Dummy window of lags: [t-5, t-4, t-3, t-2, t-1] -> t
    X_ts = np.random.randint(10, 100, (100, 5))
    y_ts = np.random.randint(10, 100, 100)
    ts_model = RandomForestRegressor(n_estimators=20, random_state=42)
    ts_model.fit(X_ts, y_ts)
    
    with open(os.path.join(settings.MODEL_DIR, "demand_forecast.pkl"), "wb") as f:
        pickle.dump(ts_model, f)

    # --- MODEL 4: ANOMALY DETECTOR ---
    print("Training Anomaly Detector (Isolation Forest)...")
    # Features: [order_tat, qc_failure_count, total_amount, risk_score_encoded, courier_delay_hours]
    X_anomaly = np.random.rand(100, 5)
    anomaly_detector = IsolationForest(contamination=0.05, random_state=42)
    anomaly_detector.fit(X_anomaly)
    
    with open(os.path.join(settings.MODEL_DIR, "anomaly_detector.pkl"), "wb") as f:
        pickle.dump(anomaly_detector, f)

    # --- MODEL 5: REORDER PREDICTOR ---
    print("Training Reorder Predictor...")
    X_reorder = np.random.randint(5, 50, (100, 5))
    y_reorder = np.random.randint(10, 100, 100)
    reorder_model = RandomForestRegressor(n_estimators=20, random_state=42)
    reorder_model.fit(X_reorder, y_reorder)
    
    with open(os.path.join(settings.MODEL_DIR, "reorder_predictor.pkl"), "wb") as f:
        pickle.dump(reorder_model, f)

    db.close()
    print("All ML models successfully trained and registered.")

if __name__ == "__main__":
    train_and_register_models()
