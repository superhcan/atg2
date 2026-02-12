import time
import logging
from datetime import datetime, timedelta
# Lägg till projektets rotmapp i path
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

import argparse
from src.data.atg_collector import ATGClient

class OddsMonitor:
    def __init__(self):
        self.client = ATGClient()
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Snapshot-fönster (minuter innan start - enligt användarens krav)
        self.windows = [60, 30, 5, 1]
        self.processed_snapshots = set() # (game_id, window)
        
        # Cache för kalendern för att undvika onödiga hämtningar/sparande
        self.cached_calendar = None
        self.last_calendar_fetch = datetime.min

    def get_upcoming_games(self):
        """Hämtar dagens lopp och deras starttider. Uppdaterar kalender var 10:e minut."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        
        # Uppdatera kalendern om det var mer än 10 minuter sen sist
        if not self.cached_calendar or (now - self.last_calendar_fetch).total_seconds() > 600:
            self.logger.info("🔄 Uppdaterar kalendern...")
            # Vi sätter save=False när vi bara pollar för att inte fylla disken med tusentals filer
            self.cached_calendar = self.client.get_calendar(date_str, save=False)
            self.last_calendar_fetch = now
            
        if not self.cached_calendar:
            return []
        
        calendar = self.cached_calendar
        events_to_track = []
        
        # Vi går igenom alla banor (tracks)
        for track in calendar.get("tracks", []):
            # Och alla lopp på varje bana
            for race in track.get("races", []):
                race_id = race.get("id")
                start_time_str = race.get("startTime")
                
                if not race_id or not start_time_str:
                    continue
                    
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", ""))
                    
                    # Vi lägger till bevakning för loppets Vinnare och Plats
                    game_prefix = f"vinnare_{race_id}"
                    events_to_track.append({
                        "id": game_prefix,
                        "race_id": race_id,
                        "start_time": start_time
                    })
                    
                except Exception as e:
                    self.logger.error(f"Kunde inte tolka lopp {race_id}: {e}")
                    
        return events_to_track

    def run(self, max_duration_hours=None):
        self.logger.info(f"🎬 Startar Odds Monitor (Mode: Daemon, Max duration: {max_duration_hours if max_duration_hours else 'Infinite'})")
        start_time_monitor = datetime.now()
        
        while True:
            try:
                now = datetime.now()
                
                # Check for session timeout
                if max_duration_hours:
                    elapsed = (now - start_time_monitor).total_seconds() / 3600
                    if elapsed > max_duration_hours:
                        self.logger.info(f"⏱ Session timeout ({max_duration_hours}h nådd). Avslutar.")
                        break

                games = self.get_upcoming_games()
                
                if not games:
                    self.logger.info("📭 Inga spel hittades för idag.")
                    time.sleep(60)
                    continue

                active_games = 0
                for game in games:
                    game_id = str(game["id"])
                    start_time = game["start_time"]
                    
                    if not isinstance(start_time, datetime):
                        continue
                        
                    # Hur långt är det kvar?
                    # Vi använder total_seconds() och sen jämförelse på minutnivå
                    time_diff_sec = (start_time - now).total_seconds()
                    diff_min = time_diff_sec / 60
                    
                    if diff_min < -5: # Loppet har passerat (vi tillåter 5 min eftersläp för säkerhet)
                        continue
                    
                    active_games += 1
                        
                    for window in self.windows:
                        # Vi tillåter ett litet fönster (+/- 45 sekunder) för att fånga rätt minut
                        # 0.75 minuter = 45 sekunder
                        if (window - 0.75) <= diff_min <= (window + 0.75) and (game_id, window) not in self.processed_snapshots:
                            self.logger.info(f"📸 Tar snapshot för {game_id} ({window} min kvar, diff={diff_min:.1f})")
                            self.client.get_game(game_id)
                            self.processed_snapshots.add((game_id, window))
                            break
                
                # Om inga kommande spel finns kvar
                if active_games == 0 and (now - start_time_monitor).total_seconds() > 3600:
                    self.logger.info("🏁 Inga fler aktiva lopp att bevaka. Avslutar.")
                    break

                # Vänta 20 sekunder för att säkerställa att vi inte missar 1-minutsfönstret
                time.sleep(20)
                
            except KeyboardInterrupt:
                self.logger.info("Odds Monitor stoppad av användaren.")
                break
            except Exception as e:
                self.logger.error(f"Oväntat fel i loopen: {e}")
                time.sleep(60)

if __name__ == "__main__":
    monitor = OddsMonitor()
    # Vi kör i daemon-läge som standard nu för molnet
    duration = float(os.getenv("MONITOR_DURATION_HOURS", 6))
    monitor.run(max_duration_hours=duration)
