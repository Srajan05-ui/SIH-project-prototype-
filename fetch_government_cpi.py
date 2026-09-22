import pandas as pd
import logging
from datetime import datetime
# Assuming mospi_esankhyiki is an available package for the API
try:
    import mospi_esankhyiki as mospi
except ImportError:
    mospi = None
    logging.warning("mospi_esankhyiki package not found. Please install it or use the REST API.")

logger = logging.getLogger(__name__)

class GovernmentDataIngestor:
    def __init__(self):
        self.client = mospi.Client() if mospi else None

    def fetch_headline_cpi(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetches the All-India Headline CPI (Rural+Urban) from the MoSPI portal.
        """
        if not self.client:
            logger.error("MoSPI client is not initialized.")
            return pd.DataFrame()

        try:
            logger.info(f"Fetching MoSPI CPI data from {start_date} to {end_date}...")
            
            # Example query structure based on standard macro data wrappers
            data = self.client.get_indicator(
                indicator_code="CPI_HEADLINE_COMBINED",
                frequency="Monthly",
                start_date=start_date,
                end_date=end_date,
                region="All India"
            )
            
            if not data:
                logger.warning("No data returned from MoSPI.")
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            
            # Clean and structure for index_chain_calc.py
            df['date'] = pd.to_datetime(df['release_date'])
            df = df.sort_values('date')
            df.set_index('date', inplace=True)
            
            logger.info("Successfully ingested MoSPI macroeconomic baselines.")
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch data from MoSPI eSankhyiki: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingestor = GovernmentDataIngestor()
    # Example usage fetching the last 12 months
    cpi_data = ingestor.fetch_headline_cpi(start_date="2022-01-01", end_date="2023-01-01")
    if not cpi_data.empty:
        print(cpi_data.head())

