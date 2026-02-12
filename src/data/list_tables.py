import pandas as pd
from sqlalchemy import create_engine, inspect

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

def list_tables():
    print("--- Listing All Tables in Database ---")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    for table in tables:
        print(f"- {table}")
        
    print("\n--- Checking Row Counts for Race-like tables ---")
    for table in tables:
        if 'race' in table or 'lopp' in table:
            try:
                count = pd.read_sql(f"SELECT COUNT(*) FROM {table}", engine).iloc[0,0]
                print(f"{table}: {count} rows")
            except Exception:
                pass

if __name__ == "__main__":
    list_tables()
