import pandas as pd
import numpy as np

# Ladda prediktioner
try:
    df = pd.read_csv('data/processed/test_predictions.csv')
    df['eval_odds'] = df['odds_5m'].fillna(df['final_odds'])
    df['eval_prob'] = 1 / df['eval_odds']
    df['edge'] = df['pred_win_prob'] / df['eval_prob']
    
    # Filtrera lopp som har utfall
    history_df = df.dropna(subset=['finish_order', 'eval_odds'])
    
    print("ROI Analys (Fasta insatser 100kr):")
    for min_edge in np.arange(1.0, 3.1, 0.1):
        filtered = history_df[history_df['edge'] >= min_edge]
        if len(filtered) > 0:
            n_bets = len(filtered)
            cost = n_bets * 100
            wins = filtered[filtered['finish_order'] == 1]
            revenue = (wins['eval_odds'] * 100).sum()
            roi = (revenue - cost) / cost
            print(f"Edge >= {min_edge:.1f}: ROI = {roi:.2%}, Antal spel = {n_bets}")
            
except Exception as e:
    print(f"Fel vid analys: {e}")
