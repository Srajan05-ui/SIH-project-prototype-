import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)

class Tier(Enum):
    TIER_2_DIRECT = 2
    TIER_1_GOOGLE = 1
    TIER_0_DGCA = 0

class SystemOrchestrator:
    def __init__(self):
        self.current_tier = Tier.TIER_2_DIRECT
        self.error_count = 0
        self.max_errors = 3
        self.status_matrix = []
        
    def log_status(self, message):
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        log_entry = {"time": timestamp, "tier": self.current_tier.name, "message": message}
        self.status_matrix.append(log_entry)
        logger.info(f"[{self.current_tier.name}] {message}")
        
    def degrade_tier(self):
        """Handles graceful fallback down the degradation ladder."""
        if self.current_tier == Tier.TIER_2_DIRECT:
            self.current_tier = Tier.TIER_1_GOOGLE
            self.log_status("Degrading to Tier 1 (Google Flights wrappers via fast-flights).")
        elif self.current_tier == Tier.TIER_1_GOOGLE:
            self.current_tier = Tier.TIER_0_DGCA
            self.log_status("Degrading to Tier 0 (Static DGCA Tariff PDF ingestion).")
        else:
            self.log_status("Already at minimum tier (Tier 0). Manual intervention required.")
            
        self.error_count = 0
            
    def execute_pipeline(self, scrape_func):
        """
        Executes an arbitrary scrape function. Degrades tier if successive failures occur.
        """
        self.log_status(f"Executing extraction pipeline at {self.current_tier.name}")
        try:
            result = scrape_func(self.current_tier)
            if not result:
                raise Exception("Empty result returned from scraper.")
            self.error_count = 0 # Reset counter on success
            return result
        except Exception as e:
            self.error_count += 1
            self.log_status(f"Extraction failed: {str(e)}. Error count: {self.error_count}/{self.max_errors}")
            if self.error_count >= self.max_errors:
                self.degrade_tier()
            return None

