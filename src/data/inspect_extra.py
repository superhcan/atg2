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

def inspect_table(table_name):
    print(f"\n--- {table_name} ---")
    try:
        df_cols = pd.read_sql(f"SELECT * FROM {table_name} LIMIT 0", engine)
        print(f"Columns: {list(df_cols.columns)}")
        print(pd.read_sql(f"SELECT COUNT(*) as count FROM {table_name}", engine).to_string(index=False))
        print("Sample:")
        print(pd.read_sql(f"SELECT * FROM {table_name} LIMIT 3", engine).to_string())
    except Exception as e:
        print(f"Error: {e}")

inspect_table('atgapi_horse')
inspect_table('atgapi_trainer')
inspect_table('atgapi_entryassignment')
