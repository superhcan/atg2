import pandas as pd
from sqlalchemy import create_engine

# Konfiguration
db_config = {
    "host": "192.168.0.22",
    "port": "5432",
    "database": "atg_db",
    "user": "atg",
    "password": "atgpass"
}
connection_str = f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
engine = create_engine(connection_str)

def check_missing_period():
    print("--- Checking Missing Period (2026-01-08 to 2026-02-01) ---")
    
    # 1. Kolla alla lopp i perioden oavsett land
    query_all = """
        SELECT date, track_country_code, COUNT(*) as n_races
        FROM atgapi_race
        WHERE date BETWEEN '2026-01-08' AND '2026-02-01'
        GROUP BY date, track_country_code
        ORDER BY date
    """
    df_all = pd.read_sql(query_all, engine)
    print("\nAlla lopp i DB för perioden:")
    print(df_all)
    
    # 2. Kolla odds-täckning för dessa lopp
    # Vi kollar om det finns odds snapshots för dessa lopp
    # Denna query kan vara tung om snapshots tabellen är stor, men vi filtrerar på datum via race.
    # Egentligen måste vi joina race_id.
    
    print("\nKollar odds-täckning (kan ta några sekunder)...")
    # Förenklad check: Vi kollar om vi HAR odds i vår 'enriched' csv om vi har den kvar?
    # Nej, vi kollar DB för sanningen.
    
    # Vi kan behöva optimera frågan.
    query_odds_optimized = """
        SELECT r.date, r.track_country_code, COUNT(DISTINCT s.race_id) as n_races_with_odds
        FROM atgapi_race r
        LEFT JOIN racing_ml_odds_snapshot s ON r.id = s.race_id 
            AND s.minutes_to_start BETWEEN 3 AND 40
        WHERE r.date BETWEEN '2026-01-08' AND '2026-02-01'
        AND r.track_country_code = 'SE' -- Vi fokuserar på SE eftersom det är det vi filtrerar på
        GROUP BY r.date, r.track_country_code
        ORDER BY r.date
    """
    
    df_odds = pd.read_sql(query_odds_optimized, engine)
    print("\nOdds-täckning för SVENSKA lopp (SE) i perioden:")
    print(df_odds)

if __name__ == "__main__":
    check_missing_period()
