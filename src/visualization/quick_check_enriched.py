import pandas as pd
import numpy as np

def run_analysis():
    print("--- FEATURE PREVIEW (ENRICHED) ---")
    
    # Ladda data enriched
    try:
        df = pd.read_csv('data/processed/race_data_enriched.csv')
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        print(f"Kunde inte ladda filen: {e}")
        return

    print(f"Totalt antal rader: {len(df)}")
    print("Kolumner:", list(df.columns))

    print("\nSaknade värden (Feature coverage):")
    cols_to_check = ['horse_name', 'age', 'sex', 'horse_shoes_front', 'horse_sulky_type_code', 'finish_order']
    print(df[cols_to_check].isna().mean() * 100)

    print("\nExempel på data:")
    print(df[['race_id', 'start_number', 'horse_name', 'age', 'sex', 'horse_shoes_front', 'odds_5m']].head().to_string())

if __name__ == "__main__":
    run_analysis()
