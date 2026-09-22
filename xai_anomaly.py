import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import shap
import logging

logger = logging.getLogger(__name__)

class XAIAnomalyEngine:
    def __init__(self):
        # Unsupervised Isolation Forest Anomaly Detector
        self.model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        self.explainer = None
        self.features = []
        
    def fit(self, df: pd.DataFrame, features: list):
        if df.empty or len(features) == 0:
            return False
            
        self.features = features
        X = df[self.features].fillna(0)
        self.model.fit(X)
        
        # Wrap the trained tree model with SHAP TreeExplainer
        self.explainer = shap.TreeExplainer(self.model)
        return True
        
    def detect_and_explain(self, df: pd.DataFrame):
        """
        Executes Isolation Forest to find outliers, generates local Shapley feature attributions.
        Returns the scored DataFrame and a list of SHAP breakdowns for anomalous points.
        """
        if df.empty or self.explainer is None:
            return df, []
            
        X = df[self.features].fillna(0)
        df = df.copy()
        
        # -1 indicates anomaly, 1 indicates normal
        df['anomaly_score'] = self.model.decision_function(X)
        df['is_anomaly'] = self.model.predict(X)
        
        anomalies = df[df['is_anomaly'] == -1]
        shap_explanations = []
        
        if not anomalies.empty:
            X_anomalies = anomalies[self.features]
            shap_values = self.explainer.shap_values(X_anomalies)
            
            for i, (idx, row) in enumerate(anomalies.iterrows()):
                breakdown = {self.features[j]: shap_values[i][j] for j in range(len(self.features))}
                breakdown['base_value'] = self.explainer.expected_value
                
                shap_explanations.append({
                    'index': idx,
                    'route': row.get('route', 'Unknown'),
                    'breakdown': breakdown
                })
                
        return df, shap_explanations
