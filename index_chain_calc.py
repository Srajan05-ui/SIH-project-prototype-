import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import logging

logger = logging.getLogger(__name__)

class IndexCalculator:
    def __init__(self):
        pass

    def apply_hedonic_pricing(self, df):
        """
        Runs Linear Regression on ticket metadata to strip quality premiums.
        Returns calculated 'adjusted_pure_fare' column.
        """
        if df.empty or 'fare' not in df.columns:
            return df
            
        features = ['meal_included', 'baggage_kg', 'seat_pitch']
        # Defensively ensure required columns exist
        for f in features:
            if f not in df.columns:
                df[f] = 0
                
        X = df[features].fillna(0)
        y = df['fare']
        
        if len(df) > 1:
            model = LinearRegression()
            model.fit(X, y)
            quality_premium = model.predict(X)
            intercept = model.intercept_
            df['adjusted_pure_fare'] = y - quality_premium + intercept
        else:
            df['adjusted_pure_fare'] = df['fare']
            
        return df

    def calculate_chained_fisher_index(self, current_period_df, base_period_df):
        """
        Calculates the Superlative Chained Fisher Ideal Index.
        Expects df with columns: 'adjusted_pure_fare', 'volume', 'route'
        """
        if current_period_df.empty or base_period_df.empty:
            return 100.0
            
        merged = pd.merge(base_period_df, current_period_df, on='route', suffixes=('_0', '_t'))
        
        if merged.empty:
            return 100.0
            
        p0 = merged['adjusted_pure_fare_0']
        pt = merged['adjusted_pure_fare_t']
        q0 = merged['volume_0']
        qt = merged['volume_t']
        
        laspeyres = np.sum(pt * q0) / np.sum(p0 * q0)
        paasche = np.sum(pt * qt) / np.sum(p0 * qt)
        
        # Geometric mean of Laspeyres and Paasche
        fisher = np.sqrt(laspeyres * paasche)
        
        return fisher * 100.0

