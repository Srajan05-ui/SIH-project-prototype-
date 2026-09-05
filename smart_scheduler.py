import schedule
import time
import subprocess
import logging
import sys
import datetime

# Configure logging to output to both console and file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/scheduler.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("smart_scheduler")

def run_data_pipeline():
    """Executes the daily data pipeline via the run_prototype.ps1 script."""
    logger.info("="*50)
    logger.info("STARTING DAILY DATA PIPELINE: %s", datetime.datetime.now().strftime("%Y-%m-%d"))
    logger.info("="*50)
    
    try:
        # Run the powershell script that orchestrates the entire pipeline
        result = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", "run_prototype.ps1"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Pipeline executed successfully!")
        logger.debug(f"Output:\n{result.stdout}")
        
    except subprocess.CalledProcessError as e:
        logger.error("Pipeline execution failed with exit code %s", e.returncode)
        logger.error(f"Error Output:\n{e.stderr}")
    except Exception as e:
        logger.exception("An unexpected error occurred while running the pipeline.")
        
    logger.info("="*50)
    logger.info("PIPELINE RUN COMPLETED")
    logger.info("="*50)

def main():
    logger.info("Starting Smart Scheduler Daemon...")
    
    # --- TEST SCHEDULE ---
    # Uncomment the next line to test the scheduler every 1 minute.
    # schedule.every(1).minutes.do(run_data_pipeline)
    
    # --- PRODUCTION SCHEDULE ---
    # Run the pipeline three times a day as requested: 4 AM, 12 PM, and 7 PM.
    # Schedule 5 minutes early so data is ready EXACTLY on the hour
    schedule.every().day.at("03:55").do(run_data_pipeline)
    schedule.every().day.at("11:55").do(run_data_pipeline)
    schedule.every().day.at("18:55").do(run_data_pipeline)
    schedule.every().day.at("19:55").do(run_data_pipeline)
    schedule.every().day.at("22:55").do(run_data_pipeline)
    
    # Calculate the very next run time for logging
    next_run = min(job.next_run for job in schedule.jobs)
    logger.info(f"Next pipeline run scheduled for: {next_run}")
    
    # Catch-up logic: Run immediately once when the PC boots up and this script starts, 
    # to ensure we don't miss data if the PC was shut down during a scheduled time.
    logger.info("PC Boot/Restart detected: Running immediate catch-up scrape before entering schedule...")
    run_data_pipeline()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
