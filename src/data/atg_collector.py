import requests
import json
import logging
from datetime import datetime
from pathlib import Path

class ATGClient:
    """
    Klient för att hämta data direkt från ATG:s publika API.
    """
    BASE_URL = "https://www.atg.se/services/racinginfo/v1/api"
    
    def __init__(self, bronze_path="data/warehouse/bronze"):
        self.bronze_path = Path(bronze_path)
        self.bronze_path.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _fetch(self, endpoint):
        url = f"{self.BASE_URL}/{endpoint}"
        self.logger.info(f"Hämtar: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Fel vid hämtning från {url}: {e}")
            return None

    def save_raw(self, data, category, identifier, sub_dir=None):
        """Sparar rådata i Bronze-lagret som JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if not sub_dir:
            sub_dir = datetime.now().strftime("%Y-%m-%d")
        
        target_dir = self.bronze_path / category / sub_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{identifier}_{timestamp}.json"
        with open(target_dir / filename, "w") as f:
            json.dump(data, f, indent=2)
        
        return target_dir / filename

    def get_calendar(self, date_str=None):
        """Hämtar kalender för en specifik dag (YYYY-MM-DD)."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        data = self._fetch(f"calendar/day/{date_str}")
        if data:
            self.save_raw(data, "calendar", date_str, sub_dir=date_str)
        return data

    def get_game(self, game_id, date_str=None):
        """Hämtar detaljer för ett spel."""
        data = self._fetch(f"games/{game_id}")
        if data:
            # Om datum inte skickas med, försök extrahera från game_id (t.ex. V75_2026-02-05_6_1)
            if not date_str and "_" in game_id:
                parts = game_id.split("_")
                if len(parts) > 1:
                    date_str = parts[1]
            
            self.save_raw(data, "games", game_id, sub_dir=date_str)
        return data

    def crawl_day(self, date_str=None):
        """Huvudmetod för att hämta ALLT för en dag."""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        self.logger.info(f"--- Startar crawl för {date_str} ---")
        
        # 1. Kalender
        calendar = self.get_calendar(date_str)
        if not calendar:
            return
        
        # 2. Loopa igenom spel - OPTIMERING: Hämta bara de stora spelen (V*, GS*, LD)
        # De stora spelen innehåller all information om de ingående loppen och hästarna.
        # Att hämta varje Trio/Vinnare/Plats separat innebär hundratals onödiga anrop.
        prioritized_types = ["V75", "V86", "V64", "V65", "V5", "V4", "GS75", "LD", "V3", "vinnare", "plats", "tvilling"]
        all_game_ids = []
        
        for game_type, games in calendar.get("games", {}).items():
            if game_type in prioritized_types:
                for game in games:
                    game_id = game.get("id")
                    if game_id:
                        all_game_ids.append(game_id)
        
        # Om inga stora spel finns (ovanligt), hämta de första 20 spelen som fallback
        if not all_game_ids:
            for game_type, games in calendar.get("games", {}).items():
                for game in games[:20]:
                    game_id = game.get("id")
                    if game_id:
                        all_game_ids.append(game_id)

        self.logger.info(f"Hittade {len(all_game_ids)} relevanta spel (optimerat från totalt antal).")
        
        for g_id in all_game_ids:
            self.get_game(g_id, date_str=date_str)

if __name__ == "__main__":
    client = ATGClient()
    print("Kör fullständig crawl för idag...")
    client.crawl_day()
