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

def check_future():
    print("--- Checking for Future Races ---")
    query = """
        SELECT date, COUNT(*) as n_races
        FROM atgapi_race
        WHERE date >= '2026-02-04'
        GROUP BY date
        ORDER BY date
    """
    df = pd.read_sql(query, engine)
    print(df)

if __name__ == "__main__":
    check_future()
