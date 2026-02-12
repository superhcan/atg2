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

def check_leakage():
    print("--- Checking for Data Leakage ---")
    # Hämta en häst och dess lopphistorik
    # Välj en häst som har startat både 2024 och 2025
    query = """
        SELECT e.horse_id, h.name, h.stats_life_starts, r.date
        FROM atgapi_entry e
        JOIN atgapi_race r ON e.race_id = r.id
        JOIN atgapi_horse h ON e.horse_id = h.id
        WHERE r.date >= '2024-01-01'
        ORDER BY r.date
        LIMIT 1000
    """
    df = pd.read_sql(query, engine)
    
    # Hitta en häst med flera starter
    counts = df['horse_id'].value_counts()
    horse_id = counts[counts > 1].index[0]
    
    subset = df[df['horse_id'] == horse_id].sort_values('date')
    print(f"\nAnalyzing horse: {subset['name'].iloc[0]} (ID: {horse_id})")
    print(subset[['date', 'stats_life_starts']].to_string())
    
    # Om stats_life_starts är SAMMA för alla datum, då har vi läckage.
    # För ett lopp 2024 ska stats_life_starts vara lägre än för ett lopp 2025.
    unique_stats = subset['stats_life_starts'].nunique()
    if unique_stats == 1:
        print("\n⚠️  LEAKAGE DETECTED! ⚠️")
        print("The column 'stats_life_starts' is constant across time.")
        print("This means we are using *current* statistics to predict *past* races.")
    else:
        print("\nNo obvious leakage in this column (values change over time).")

if __name__ == "__main__":
    check_leakage()
