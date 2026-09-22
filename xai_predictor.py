import numpy as np
import pandas as pd
import lightgbm as lgb
import shap
import logging
from datetime import timedelta, datetime

logger = logging.getLogger(__name__)

class XAIPredictor:
    def __init__(self):
        # Initializing the LightGBM Regressor
        self.model = lgb.LGBMRegressor(n_estimators=100, random_state=42)
        self.explainer = None
        
    def train(self, df, features, target):
        """Train the LightGBM model on historical data."""
        if df.empty:
            return False
            
        X = df[features]
        y = df[target]
        self.model.fit(X, y)
        self.explainer = shap.TreeExplainer(self.model)
        return True
        
    def forecast_14_days(self, recent_data, features):
        """Generate a 14-day inflation forecast cone and SHAP breakdowns."""
        if self.explainer is None or recent_data.empty:
            return None, None
            
        future_dates = [datetime.now() + timedelta(days=i) for i in range(1, 15)]
        
        # Base the future state on the latest known data point with some structural drift
        last_row = recent_data[features].iloc[-1:].copy()
        
        predictions = []
        shap_values_list = []
        
        for i in range(14):
            synthetic_row = last_row.copy()
            # Inject synthetic drift (e.g., fuel price shocks, seasonal adjustments)
            if len(features) > 0:
                synthetic_row[features[0]] = synthetic_row[features[0]] * (1 + np.random.normal(0, 0.015))
            
            pred = self.model.predict(synthetic_row)[0]
            shap_val = self.explainer.shap_values(synthetic_row)
            
            predictions.append({
                "date": future_dates[i].strftime("%Y-%m-%d"),
                "forecast": pred,
                "lower_bound": pred * 0.95,
                "upper_bound": pred * 1.05
            })
            
            # Map SHAP values to features for the waterfall breakdown
            shap_breakdown = {features[j]: shap_val[0][j] for j in range(len(features))}
            shap_breakdown['base_value'] = self.explainer.expected_value
            shap_values_list.append({
                "date": future_dates[i].strftime("%Y-%m-%d"),
                "breakdown": shap_breakdown
            })
            
        forecast_df = pd.DataFrame(predictions)
        return forecast_df, shap_values_list

