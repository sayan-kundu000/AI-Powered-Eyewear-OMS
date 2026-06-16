import os
import pickle
import json
import logging
import datetime
import redis
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier, XGBRegressor
from app.config import settings
from app.models import PredictionLog
from sqlalchemy.orm import Session

logger = logging.getLogger("models_registry")

class MLModelRegistry:
    def __init__(self):
        self.model_dir = settings.MODEL_DIR
        self.models = {}
        self.model_versions = {
            "sla_breach": "v1.0.0",
            "delivery_delay": "v1.0.0",
            "demand_forecast": "v1.0.0",
            "anomaly_detector": "v1.0.0",
            "reorder_predictor": "v1.0.0"
        }
        self.redis_client = None
        try:
            self.redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            logger.info("MLModelRegistry connected to Redis successfully for prediction caching.")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis cache in MLModelRegistry: {e}. Caching disabled.")
            
        self.initialize_models()

    def initialize_models(self):
        """
        Loads models from disk or fits baseline models on initialization.
        """
        model_names = ["sla_breach", "delivery_delay", "demand_forecast", "anomaly_detector", "reorder_predictor"]
        for name in model_names:
            path = os.path.join(self.model_dir, f"{name}.pkl")
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        self.models[name] = pickle.load(f)
                    logger.info(f"Loaded ML model: {name} ({self.model_versions[name]})")
                except Exception as e:
                    logger.error(f"Error loading {name}: {e}. Initializing a default model.")
                    self.train_default_model(name)
            else:
                self.train_default_model(name)

    def train_default_model(self, name: str):
        """
        Fits a default/mock model to ensure the API never fails.
        """
        logger.info(f"Fitting fallback model for: {name}")
        np.random.seed(42)
        X_dummy = np.random.rand(100, 5)
        
        if name == "sla_breach":
            y_dummy = np.random.randint(0, 2, 100)
            clf = RandomForestClassifier(n_estimators=10, random_state=42)
            clf.fit(X_dummy, y_dummy)
            self.models[name] = clf
            
        elif name == "delivery_delay":
            y_dummy = np.random.rand(100) * 48  # delay hours
            reg = RandomForestRegressor(n_estimators=10, random_state=42)
            reg.fit(X_dummy, y_dummy)
            self.models[name] = reg
            
        elif name == "demand_forecast":
            # Time-series regression: inputting lag features
            y_dummy = np.random.randint(10, 100, 100)
            reg = RandomForestRegressor(n_estimators=10, random_state=42)
            reg.fit(X_dummy, y_dummy)
            self.models[name] = reg
            
        elif name == "anomaly_detector":
            # Isolation Forest detects outliers
            detector = IsolationForest(contamination=0.05, random_state=42)
            detector.fit(X_dummy)
            self.models[name] = detector
            
        elif name == "reorder_predictor":
            y_dummy = np.random.randint(5, 50, 100)
            reg = RandomForestRegressor(n_estimators=10, random_state=42)
            reg.fit(X_dummy, y_dummy)
            self.models[name] = reg

        self.save_model_to_disk(name)

    def save_model_to_disk(self, name: str):
        path = os.path.join(self.model_dir, f"{name}.pkl")
        try:
            with open(path, "wb") as f:
                pickle.dump(self.models[name], f)
            logger.info(f"Saved ML model to disk: {name}")
        except Exception as e:
            logger.error(f"Error saving {name} model: {e}")

    def _get_cached_prediction(self, cache_key: str) -> Optional[Any]:
        if self.redis_client:
            try:
                val = self.redis_client.get(cache_key)
                if val is not None:
                    return json.loads(val)
            except Exception as e:
                logger.error(f"Redis cache read error: {e}")
        return None

    def _set_cached_prediction(self, cache_key: str, value: Any, expire_seconds: int = 1800):
        if self.redis_client:
            try:
                self.redis_client.setex(cache_key, expire_seconds, json.dumps(value))
            except Exception as e:
                logger.error(f"Redis cache write error: {e}")

    def predict_sla_breach(self, db: Session, order_id: int, features: List[float]) -> float:
        """
        Predict probability of SLA breach.
        Input features: [current_stage_id, lens_type_id, store_id, rx_complexity, qc_failures]
        """
        feat_str = ",".join(map(str, features))
        cache_key = f"ml_cache:sla_breach:{feat_str}"
        
        cached_val = self._get_cached_prediction(cache_key)
        if cached_val is not None:
            logger.info(f"Cache hit for SLA Breach prediction (Order {order_id})")
            return float(cached_val)

        model = self.models.get("sla_breach")
        feat_arr = np.array([features])
        
        # Predict probability of class 1 (Breached)
        prob = float(model.predict_proba(feat_arr)[0][1])
        
        # Log Prediction
        self._log_prediction(db, order_id, "SLA_BREACH", features, {"breach_probability": prob})
        self._set_cached_prediction(cache_key, prob, expire_seconds=1800)
        return prob

    def predict_delivery_delay(self, db: Session, order_id: int, features: List[float]) -> Tuple[float, float]:
        """
        Predict expected delivery delay in hours and delay probability.
        Input features: [courier_id, dest_region_id, weather_severity, inventory_availability, historical_delay]
        """
        feat_str = ",".join(map(str, features))
        cache_key = f"ml_cache:delivery_delay:{feat_str}"
        
        cached_val = self._get_cached_prediction(cache_key)
        if cached_val is not None:
            logger.info(f"Cache hit for Delivery Delay prediction (Order {order_id})")
            return float(cached_val[0]), float(cached_val[1])

        reg = self.models.get("delivery_delay")
        feat_arr = np.array([features])
        
        predicted_hours = float(reg.predict(feat_arr)[0])
        # Simple logistic mapping to get probability
        delay_prob = 1.0 / (1.0 + np.exp(- (predicted_hours - 12.0) / 6.0))
        
        output = (predicted_hours, float(delay_prob))
        self._log_prediction(db, order_id, "DELIVERY_DELAY", features, {
            "predicted_delay_hours": predicted_hours,
            "delay_probability": float(delay_prob)
        })
        self._set_cached_prediction(cache_key, output, expire_seconds=1800)
        return predicted_hours, float(delay_prob)

    def forecast_demand(self, db: Session, last_30_days_data: List[float], days_ahead: int = 30) -> List[float]:
        """
        Forecast lens demand for future period.
        """
        feat_str = ",".join(map(str, last_30_days_data)) + f":{days_ahead}"
        cache_key = f"ml_cache:demand_forecast:{feat_str}"
        
        cached_val = self._get_cached_prediction(cache_key)
        if cached_val is not None:
            logger.info("Cache hit for Demand Forecast prediction")
            return list(cached_val)

        reg = self.models.get("demand_forecast")
        # Prepare sliding window forecasting
        predictions = []
        current_window = list(last_30_days_data[-5:])  # Use last 5 values as lags
        
        for _ in range(days_ahead):
            feat_arr = np.array([current_window[-5:]])
            pred_val = float(reg.predict(feat_arr)[0])
            predictions.append(max(0.0, pred_val))
            current_window.append(pred_val)
            
        self._log_prediction(db, None, "DEMAND_FORECAST", last_30_days_data, {"forecast": predictions})
        self._set_cached_prediction(cache_key, predictions, expire_seconds=3600)
        return predictions

    def detect_anomaly(self, db: Session, order_id: int, features: List[float]) -> Dict[str, Any]:
        """
        Isolation Forest anomaly detection.
        Input features: [order_tat, qc_failure_count, total_amount, risk_score_encoded, courier_delay_hours]
        Returns: is_anomaly (bool), anomaly_score (float)
        """
        feat_str = ",".join(map(str, features))
        cache_key = f"ml_cache:anomaly_detection:{feat_str}"
        
        cached_val = self._get_cached_prediction(cache_key)
        if cached_val is not None:
            logger.info(f"Cache hit for Anomaly Detection (Order {order_id})")
            return dict(cached_val)

        detector = self.models.get("anomaly_detector")
        feat_arr = np.array([features])
        
        pred = int(detector.predict(feat_arr)[0])  # 1 for normal, -1 for anomaly
        decision_score = float(detector.decision_function(feat_arr)[0])
        
        is_anomaly = (pred == -1)
        output_data = {"is_anomaly": is_anomaly, "score": decision_score}
        self._log_prediction(db, order_id, "ANOMALY_DETECTION", features, output_data)
        self._set_cached_prediction(cache_key, output_data, expire_seconds=3600)
        
        return output_data

    def predict_reorder_needs(self, db: Session, inventory_history: List[float]) -> Dict[str, Any]:
        """
        Predict restock quantity and urgency score.
        Input: [stock_quantity, sales_velocity_7d, lead_time_days, reorder_point, reserved_stock]
        """
        feat_str = ",".join(map(str, inventory_history))
        cache_key = f"ml_cache:reorder_predictor:{feat_str}"
        
        cached_val = self._get_cached_prediction(cache_key)
        if cached_val is not None:
            logger.info("Cache hit for Reorder Needs prediction")
            return dict(cached_val)

        reg = self.models.get("reorder_predictor")
        feat_arr = np.array([inventory_history])
        
        predicted_qty = max(0, int(reg.predict(feat_arr)[0]))
        # Calculate urgency score 0-100 based on stock level relative to reorder point
        stock, sales_vel, lead_time, reorder_pt, reserved = inventory_history
        urgency = 0.0
        if stock <= reorder_pt:
            urgency = min(100.0, ((reorder_pt - stock) / max(1, reorder_pt)) * 100.0 + 20)
            
        output = {
            "recommended_reorder_qty": predicted_qty,
            "urgency_score": round(urgency, 2)
        }
        self._set_cached_prediction(cache_key, output, expire_seconds=1800)
        return output

    def _log_prediction(self, db: Session, order_id: Optional[int], p_type: str, inputs: List[float], outputs: dict):
        log_entry = PredictionLog(
            order_id=order_id,
            model_name=self.__class__.__name__,
            prediction_type=p_type,
            inputs=json.dumps(inputs),
            outputs=json.dumps(outputs)
        )
        db.add(log_entry)
        db.commit()

registry = MLModelRegistry()

