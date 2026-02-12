import sys
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.data.atg_collector import ATGClient
from src.data.silver_parser import SilverParser
from src.data.gold_analyzer import GoldAnalyzer

def fill_gaps(start_date_str, end_date_str):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    collector = ATGClient()
    parser = SilverParser()
    analyzer = GoldAnalyzer()

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    delta = end_date - start_date
    for i in range(delta.days + 1):
        target_date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        logger.info(f"=== Processing {target_date} ===")
        
        # 1. Bronze
        logger.info(f"Step 1: Fetching (Bronze) for {target_date}")
        collector.crawl_day(target_date)
        
        # 2. Silver
        logger.info(f"Step 2: Parsing (Silver) for {target_date}")
        parser.parse_games_to_races(target_date)
        parser.parse_results(target_date)
        parser.parse_odds_time_series(target_date)
        
        # 3. Gold
        logger.info(f"Step 3: Analyzing (Gold) for {target_date}")
        analyzer.create_daily_summary(target_date)

    logger.info("✅ Gap filling complete!")

if __name__ == "__main__":
    # Fill gap from 2026-02-08 to 2026-02-11
    fill_gaps("2026-02-08", "2026-02-11")
