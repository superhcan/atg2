import pandas as pd
import numpy as np

def run_analysis():
    print("--- SNABBANALYS AV DATASET ---")
    
    # Ladda data
    try:
        df = pd.read_csv('data/processed/race_data.csv')
        df['date'] = pd.to_datetime(df['date'])
    except Exception as e:
        print(f"Kunde inte ladda filen: {e}")
        return

    print(f"Totalt antal rader: {len(df)}")
    print(f"Datumintervall: {df['date'].min().date()} till {df['date'].max().date()}")

    # Split
    split_date = pd.to_datetime('2026-01-05')
    train_df = df[df['date'] < split_date]
    test_df = df[df['date'] >= split_date]

    print(f"\nSPLIT-DATUM: {split_date.date()}")
    print(f"Träningsset: {len(train_df)} rader ({(len(train_df)/len(df))*100:.1f}%)")
    print(f"Testset:     {len(test_df)} rader ({(len(test_df)/len(df))*100:.1f}%)")

    # Odds data check
    print("\n--- ODDS-TILLGÄNGLIGHET (5 min innan) ---")
    train_cov = train_df['odds_5m'].notna().mean() * 100
    test_cov = test_df['odds_5m'].notna().mean() * 100
    
    print(f"I Träningsset: {train_cov:.1f}% av starterna har odds_5m")
    print(f"I Testset:     {test_cov:.1f}% av starterna har odds_5m")
    
    # Check coverage in late 2025 specifically for training
    late_2025 = train_df[train_df['date'] >= '2025-12-01']
    if not late_2025.empty:
        late_cov = late_2025['odds_5m'].notna().mean() * 100
        print(f"I Träningsset (Dec 2025): {late_cov:.1f}% har odds_5m")

if __name__ == "__main__":
    run_analysis()
