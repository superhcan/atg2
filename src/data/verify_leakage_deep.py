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

def verify_deep():
    print("--- DEEP LEAKAGE CHECK ---")
    
    # Kollar om 'age' är statisk för en häst över tid
    print("\n1. Checking STATIC AGE...")
    query = """
        SELECT e.horse_id, h.name, h.age, r.date
        FROM atgapi_entry e
        JOIN atgapi_race r ON e.race_id = r.id
        JOIN atgapi_horse h ON e.horse_id = h.id
        WHERE r.date >= '2024-01-01'
        ORDER BY r.date
        LIMIT 5000 
    """
    df = pd.read_sql(query, engine)
    
    # Hitta häst med starter i både början av 2024 och slutet av 2025 (eller över årsskiftet)
    # Vi behöver inte vara så specifika, bara kolla om age varierar för SAMMA horse_id
    grouped = df.groupby('horse_id')['age'].nunique()
    variying_age = grouped[grouped > 1]
    static_age = grouped[grouped == 1]
    
    print(f"Hästar med varierande ålder: {len(variying_age)}")
    print(f"Hästar med statisk ålder (trots >1 rad): {len(static_age[static_age.index.isin(df['horse_id'].value_counts()[df['horse_id'].value_counts() > 1].index)])}")

    if len(variying_age) == 0:
        print("⚠️  ALL HORSES HAVE STATIC AGE. LEAKAGE CONFIRMED.")
    else:
        print("✅ Some horses change age.")
        
    print("\n2. Verifying ROLLING STATS logic (locally)...")
    # Ladda processed data
    try:
        df_processed = pd.read_csv('data/processed/train_ready.csv')
        # Check columns
        print("Columns in train_ready:", df_processed.columns.tolist())
        
        # Vi kör bara en logik-check på den första hästen vi hittar med >3 starter
        # Eftersom vi inte har horse_id i train_ready får vi vara kreativa.
        # Men vänta, vi har horse_history_starts.
        # Om vi sorterar på horse_history_starts, borde vi se sekvenser.
        # Men utan horse_id kan vi inte garantera att det är samma häst.
        # Vi borde ha sparat horse_id i train_ready för debugging. :facepalm:
        
        print("Skipping detailed local check due to missing ID columns. Trusting the logic in build_features.py if step 1 passes.")

    except Exception as e:
        print(f"Error checking local csv: {e}")

if __name__ == "__main__":
    verify_deep()
