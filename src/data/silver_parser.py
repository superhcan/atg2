import pandas as pd
import json
import logging
from pathlib import Path
from datetime import datetime
import duckdb

class SilverParser:
    """
    Transformerar rå JSON-data (Bronze) till strukturerade Parquet-filer (Silver).
    """
    def __init__(self, bronze_path="data/warehouse/bronze", silver_path="data/warehouse/silver"):
        self.bronze_path = Path(bronze_path)
        self.silver_path = Path(silver_path)
        self.silver_path.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def parse_games_to_races(self, date_str):
        """Extraherar lopp-data från games-filer för ett specifikt datum."""
        source_dir = self.bronze_path / "games" / date_str
        if not source_dir.exists():
            self.logger.warning(f"Ingen data hittades för {date_str}")
            return
        
        all_races = []
        all_horses = []
        
        for json_file in source_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                game_id = data.get("id")
                # Ett game (t.ex. V75) har flera lopp (races)
                races = data.get("races", [])
                
                for race in races:
                    start_time_str = race.get("startTime", "")
                    if not start_time_str or start_time_str[:10] != date_str:
                        continue # Skippa lopp som inte går på detta datumet
                        
                    track = race.get("track", {})
                    country_code = track.get("countryCode", "SE")
                    
                    # FILTRERING: Endast svenska lopp
                    if country_code != "SE":
                        continue
                        
                    race_id = race.get("id")
                    if not race_id: continue
                    
                    race_info = {
                        "date": date_str,
                        "race_num": race.get("number"),
                        "race_id": race_id,
                        "track_id": track.get("id"),
                        "track_name": track.get("name"),
                        "country": country_code,
                        "distance": race.get("distance"),
                        "start_method": race.get("startMethod"),
                        "start_time": start_time_str,
                        "status": race.get("status")
                    }
                    all_races.append(race_info)
                    
                    # Extrahera hästar
                    starts = race.get("starts", [])
                    for start in starts:
                        horse = start.get("horse", {})
                        trainer = horse.get("trainer", {})
                        shoes = horse.get("shoes", {})
                        sulky = start.get("sulky", {})
                        
                        horse_info = {
                            "race_id": race.get("id"),
                            "start_num": start.get("number"),
                            "horse_id": horse.get("id"),
                            "horse_name": horse.get("name"),
                            "age": horse.get("age"),
                            "sex": horse.get("sex"),
                            "money": horse.get("money"),
                            "driver_id": start.get("driver", {}).get("id"),
                            "driver_name": start.get("driver", {}).get("firstName", "") + " " + start.get("driver", {}).get("lastName", ""),
                            "trainer_name": trainer.get("firstName", "") + " " + trainer.get("lastName", ""),
                            "post_position": start.get("postPosition"),
                            "distance": start.get("distance"),
                            # Skor: front/back
                            "shoes_front": shoes.get("front", {}).get("hasShoe", True) if shoes else True,
                            "shoes_back": shoes.get("back", {}).get("hasShoe", True) if shoes else True,
                            # Vagn
                            "sulky_type": sulky.get("type", {}).get("text", "Vanlig") if sulky else "Vanlig",
                            "sulky_color": sulky.get("colour", {}).get("text", "") if sulky else "",
                        }
                        all_horses.append(horse_info)
                        
            except Exception as e:
                self.logger.error(f"Fel vid parsning av {json_file}: {e}")
        
        if all_races:
            races_df = pd.DataFrame(all_races).drop_duplicates()
            races_df.to_parquet(self.silver_path / f"races_{date_str}.parquet", index=False)
            self.logger.info(f"Sparade {len(races_df)} lopp till Silver ({date_str})")
            
        if all_horses:
            horses_df = pd.DataFrame(all_horses).drop_duplicates()
            horses_df.to_parquet(self.silver_path / f"horses_{date_str}.parquet", index=False)
            self.logger.info(f"Sparade {len(horses_df)} hästar till Silver ({date_str})")

    def parse_results(self, date_str):
        """Extraherar resultat-data från games-filer för ett specifikt datum."""
        source_dir = self.bronze_path / "games" / date_str
        if not source_dir.exists():
            self.logger.warning(f"Ingen data hittades för {date_str}")
            return
        
        all_results = []
        
        # Vi kollar alla JSON-filer i games-mappen
        for json_file in source_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                races = data.get("races", [])
                for race in races:
                    race_id = race.get("id")
                    res_data = race.get("result")
                    if not res_data:
                        continue
                        
                    starts = race.get("starts", [])
                    for start in starts:
                        horse = start.get("horse", {})
                        res = start.get("result", {})
                        
                        all_results.append({
                            "date": date_str,
                            "race_id": race_id,
                            "horse_id": horse.get("id"),
                            "horse_name": horse.get("name"),
                            "start_num": start.get("number"),
                            "scratched": start.get("scratched", False),
                            "place": res.get("place"),
                            "finish_order": res.get("finishOrder"),
                            "final_odds": res.get("finalOdds")
                        })
                        
            except Exception as e:
                self.logger.error(f"Fel vid parsning av resultat i {json_file}: {e}")
        
        if all_results:
            results_df = pd.DataFrame(all_results).drop_duplicates()
            # Om vi har flera rader för samma häst/lopp (pga flera filer), behåll den som har flesta icke-null
            # Eller sortera på timestamp om det fanns i filnamnet.
            results_df.to_parquet(self.silver_path / f"results_{date_str}.parquet", index=False)
            self.logger.info(f"Sparade {len(results_df)} resultatrader till Silver ({date_str})")

    def parse_odds_time_series(self, date_str):
        """Extraherar alla odds-snapshots för att skapa tidsserier."""
        source_dir = self.bronze_path / "games" / date_str
        if not source_dir.exists():
            return
        
        all_odds_map = {} # (race_id, horse_id, timestamp) -> data_dict
        
        for json_file in source_dir.glob("*.json"):
            try:
                parts = json_file.stem.split("_")
                ts_str = f"{parts[-2]}_{parts[-1]}"
                timestamp = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
                
                with open(json_file, "r") as f:
                    data = json.load(f)
                
                # Prova att hämta spårning på lopp-nivå först
                races = data.get("races", [])
                for race in races:
                    race_id = race.get("id")
                    starts = race.get("starts", [])
                    for start in starts:
                        horse_id = start.get("horse", {}).get("id")
                        key = (race_id, horse_id, timestamp)
                        
                        if key not in all_odds_map:
                            all_odds_map[key] = {
                                "race_id": race_id,
                                "horse_id": horse_id,
                                "timestamp": timestamp,
                                "odds_vinnare": None,
                                "odds_plats": None,
                                "turnover_vinnare": 0.0,
                                "turnover_plats": 0.0,
                                "turnover_tvilling": 0.0
                            }
                        
                        pools = start.get("pools", {})
                        v_pool = pools.get("vinnare", {})
                        p_pool = pools.get("plats", {})
                        
                        if v_pool.get("odds"):
                            all_odds_map[key]["odds_vinnare"] = v_pool.get("odds") / 100.0
                            all_odds_map[key]["turnover_vinnare"] = v_pool.get("turnover", 0) / 100.0
                        if p_pool.get("minOdds"):
                            all_odds_map[key]["odds_plats"] = p_pool.get("minOdds") / 100.0
                            all_odds_map[key]["turnover_plats"] = p_pool.get("turnover", 0) / 100.0

                # Specialhantering för Tvilling-omsättning (ligger ofta på Game-nivå)
                game_pools = data.get("pools", {})
                if "tvilling" in game_pools:
                    tv_pool = game_pools["tvilling"]
                    tv_turnover = tv_pool.get("turnover", 0) / 100.0
                    
                    # Applicera på alla hästar i de lopp som detta spel omfattar
                    for r_id in data.get("races", []):
                        if isinstance(r_id, dict): r_id = r_id.get("id")
                        for (rk, hk, tk), val in all_odds_map.items():
                            if rk == r_id and tk == timestamp:
                                val["turnover_tvilling"] = tv_turnover

            except Exception as e:
                self.logger.error(f"Fel vid parsning av odds i {json_file}: {e}")
                continue
        
        if all_odds_map:
            odds_df = pd.DataFrame(all_odds_map.values())
            odds_df.to_parquet(self.silver_path / f"odds_trends_{date_str}.parquet", index=False)
            self.logger.info(f"Sparade {len(odds_df)} odds-snapshots till Silver ({date_str})")

if __name__ == "__main__":
    parser = SilverParser()
    today = "2026-02-05"
    print(f"Parsar data för {today}...")
    parser.parse_games_to_races(today)
    parser.parse_results(today)
    parser.parse_odds_time_series(today)
