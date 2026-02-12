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

def inspect_table(table_name, date_col=None):
    print(f"\n--- {table_name} ---")
    try:
        # Hämta kolumner
        df_cols = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", engine)
        print(f"Columns: {list(df_cols.columns)}")
        
        # Kolla datumintervall om möjligt
        if date_col:
            query = f"SELECT MIN({date_col}) as min_date, MAX({date_col}) as max_date, COUNT(*) as count FROM {table_name}"
            df_dates = pd.read_sql(query, engine)
            print(df_dates.to_string(index=False))
        else:
             print(pd.read_sql(f"SELECT COUNT(*) as count FROM {table_name}", engine).to_string(index=False))

    except Exception as e:
        print(f"Error reading {table_name}: {e}")

# 1. Kolla Races för att se tidsspann
inspect_table('atgapi_race', 'date')

# 2. Kolla Odds Snapshots
inspect_table('odds_snapshots_entryoddssnapshot', 'fetched_at') 
inspect_table('racing_ml_odds_snapshot', 'snapshot_time') 

# 3. Kolla driver info
inspect_table('atgapi_driver')
inspect_table('atgapi_entryassignment')


# 3. Kolla racing_ml_start_features
inspect_table('racing_ml_start_features')
# If it has a date column, query it manually below
try:
    print("Checking date range for racing_ml_start_features (joining with race if needed)...")
    # Assuming it has race_id, we can join to check dates
    query = """
        SELECT MIN(r.date) as min_date, MAX(r.date) as max_date, COUNT(*) as count 
        FROM racing_ml_start_features f
        JOIN atgapi_race r ON f.race_id = r.id
    """
    print(pd.read_sql(query, engine))
except Exception as e:
    print(f"Could not join with race: {e}")



