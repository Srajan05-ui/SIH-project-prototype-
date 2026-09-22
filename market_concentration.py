import networkx as nx
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class MarketConcentration:
    def __init__(self):
        self.graph = nx.Graph()
        
    def build_network(self, routes_df):
        """Builds a network topology graph from a dataframe of routes."""
        if routes_df.empty or 'origin' not in routes_df.columns or 'destination' not in routes_df.columns:
            return
            
        for _, row in routes_df.iterrows():
            self.graph.add_edge(row['origin'], row['destination'], weight=row.get('volume', 1))
            
    def calculate_hhi(self, market_share_df):
        """
        Calculates the Herfindahl-Hirschman Index (HHI) for a route.
        Expects dataframe with columns: 'route', 'airline', 'market_share' (percentage 0-100)
        """
        results = []
        if market_share_df.empty or 'route' not in market_share_df.columns:
            return pd.DataFrame(results)
            
        for route, group in market_share_df.groupby('route'):
            # HHI is sum of squared market shares
            hhi = (group['market_share'] ** 2).sum()
            results.append({'route': route, 'hhi': hhi})
        return pd.DataFrame(results)
        
    def flag_cartel_risks(self, hhi_df, price_spikes_df):
        """
        Trigger a "CRITICAL CARTEL/MONOPOLY RISK" if HHI > 2500 and there is a concurrent adjusted fare spike.
        """
        if hhi_df.empty or price_spikes_df.empty:
            return pd.DataFrame()
            
        merged = pd.merge(hhi_df, price_spikes_df, on='route', how='left')
        merged['cartel_risk_flag'] = (merged['hhi'] > 2500) & (merged['has_spike'] == True)
        
        # Add string status for UI rendering
        merged['status'] = merged['cartel_risk_flag'].apply(
            lambda x: '🔴 CRITICAL CARTEL/MONOPOLY RISK' if x else '🟢 COMPETITIVE CORRIDOR'
        )
        return merged
