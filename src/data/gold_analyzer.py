import duckdb
import pandas as pd
import logging
from pathlib import Path

class GoldAnalyzer:
    """
    Analyserar Silver-data och skapar Gold-visningar för dashboarden.
    Använder DuckDB för blixtsnabb analys av Parquet-filer.
    """
    def __init__(self, silver_path="data/warehouse/silver", gold_path="data/warehouse/gold"):
        self.silver_path = Path(silver_path)
        self.gold_path = Path(gold_path)
        self.gold_path.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.con = duckdb.connect()

    def create_daily_summary(self, date_str):
        """Skapar en Gold-tabell med en sammanfattning för en specifik dag."""
        races_file = self.silver_path / f"races_{date_str}.parquet"
        horses_file = self.silver_path / f"horses_{date_str}.parquet"
        results_file = self.silver_path / f"results_{date_str}.parquet"
        
        if not races_file.exists() or not horses_file.exists():
            self.logger.warning(f"Saknar silver-data för {date_str}")
            return

        # Om resultat finns, joina in dem
        if results_file.exists():
            query = f"""
            SELECT 
                r.date,
                r.track_name,
                r.race_id,
                COUNT(h.horse_id) as n_horses,
                SUM(CASE WHEN res.scratched THEN 1 ELSE 0 END) as n_scratched,
                STRING_AGG(CASE WHEN res.scratched THEN h.horse_name ELSE NULL END, ', ') as scratched_list,
                STRING_AGG(CASE WHEN res.horse_id IS NOT NULL AND NOT res.scratched THEN h.horse_name ELSE NULL END, ', ') as horse_list
            FROM '{races_file}' r
            JOIN '{horses_file}' h ON r.race_id = h.race_id
            LEFT JOIN '{results_file}' res ON h.race_id = res.race_id AND h.horse_id = res.horse_id
            GROUP BY ALL
            ORDER BY r.race_id
            """
        else:
            query = f"""
            SELECT 
                r.date,
                r.track_name,
                r.race_id,
                COUNT(h.horse_id) as n_horses,
                0 as n_scratched,
                CAST(NULL AS VARCHAR) as scratched_list,
                STRING_AGG(h.horse_name, ', ') as horse_list
            FROM '{races_file}' r
            JOIN '{horses_file}' h ON r.race_id = h.race_id
            GROUP BY ALL
            ORDER BY r.race_id
            """
        
        try:
            summary_df = self.con.execute(query).df()
            target_file = self.gold_path / f"daily_summary_{date_str}.parquet"
            summary_df.to_parquet(target_file, index=False)
            self.logger.info(f"Guld-sammanfattning skapad: {target_file}")
            return summary_df
        except Exception as e:
            self.logger.error(f"Fel vid guld-analys: {e}")
            return None

if __name__ == "__main__":
    analyzer = GoldAnalyzer()
    today = "2026-02-05"
    print(f"Analyserar data för {today}...")
    df = analyzer.create_daily_summary(today)
    if df is not None:
        print("\nExempel på Guld-data:")
        print(df.head())
