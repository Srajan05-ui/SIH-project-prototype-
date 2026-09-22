import requests
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class OpenSkySupply:
    def __init__(self):
        self.base_url = 'https://opensky-network.org/api/states/all'
        
    def get_live_capacity(self, bounding_box: Tuple[float, float, float, float] = None) -> int:
        """
        Fetches live ADS-B flight capacity (ICAO24 transponder signals).
        bounding_box format: (lamin, lomin, lamax, lomax)
        """
        params = {}
        if bounding_box:
            lamin, lomin, lamax, lomax = bounding_box
            params = {
                'lamin': lamin,
                'lomin': lomin,
                'lamax': lamax,
                'lomax': lomax
            }
            
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            states = data.get('states', [])
            return len(states) if states else 0
        except Exception as e:
            logger.error(f"Failed to fetch OpenSky ground truth radar data: {e}")
            return 0
