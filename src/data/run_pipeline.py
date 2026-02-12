import sys
import os
from pathlib import Path

# Lägg till projektets rotmapp i sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from src.data.atg_collector import ATGClient
from src.data.silver_parser import SilverParser
from src.data.gold_analyzer import GoldAnalyzer
from datetime import datetime, timedelta
import logging

def run_daily_pipeline(days_forward=7):
    """
    Kör hela pipelinen för dagens lopp och ett antal dagar framåt.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    collector = ATGClient()
    parser = SilverParser()
    analyzer = GoldAnalyzer()

    start_date = datetime.now()
    
    for i in range(days_forward + 1):
        target_date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        logger.info(f"\n===== Bearbetar {target_date} =====")
        
        # 1. Bronze (Fetch)
        logger.info("Steg 1: Hämtar data (Bronze)...")
        collector.crawl_day(target_date)
        
        # 2. Silver (Parse)
        logger.info("Steg 2: Transformerar data (Silver)...")
        parser.parse_games_to_races(target_date)
        parser.parse_results(target_date)
        
        # 3. Gold (Analyze)
        logger.info("Steg 3: Analyserar data (Gold)...")
        analyzer.create_daily_summary(target_date)

    logger.info("\n✅ Pipeline klar!")

if __name__ == "__main__":
    # För test kör vi bara 2 dagar framåt för att det ska gå snabbt
    run_daily_pipeline(days_forward=2)
