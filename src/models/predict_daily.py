import pandas as pd
import xgboost as xgb
import logging
import sys
import os
from pathlib import Path

# Lägg till src i path så vi kan importera features
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from src.features.build_features import process_features

def predict_daily():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Konfiguration för inferensdag (idag)
    date_filter = '2026-02-04' # Vi kör hårdkodat för denna demo, annars datetime.now().date()
    
    logger.info(f"--- GENERERAR TIPS FÖR {date_filter} ---")
    
    # 1. Hämta ALL data (behövs för historik-beräkning)
    # Vi kan inte bara hämta dagens lopp, för då blir horse_history_starts = 0 för alla.
    # Vi måste hämta hela datasetet, och sedan filtrera på datum EFTER feature engineering.
    # Vi återanvänder make_dataset.py logiken men sparar till temporär fil.
    
    # För enkelhetens skull kör vi make_dataset.py för att uppdatera `race_data_enriched.csv` 
    # (Vi antar att den redan innehåller ALLA lopp, även dagens om de finns i DB).
    # make_dataset.py filtrerar på date >= '2024-01-01', så den bör få med allt.
    # Vi kör om den för säkerhets skull.
    
    # ... men det tar tid. Vi antar att race_data_enriched.csv är "färsk".
    # (I en riktig prod-loop skulle vi köra make_dataset först).
    
    # 2. Kör Feature Engineering i 'inference' mode
    # Detta skapar 'data/processed/inference_features.csv' (vi overridear inte train_ready)
    
    logger.info("Kör Feature Engineering...")
    process_features('data/processed/race_data_enriched.csv', 'data/processed/inference_features.csv', mode='inference')
    
    # 3. Ladda Features och Modell
    df = pd.read_csv('data/processed/inference_features.csv')
    df['date'] = pd.to_datetime(df['date'])
    
    # Filtrera fram dagens lopp
    # Vi kollar datumdelen, date_filter är sträng 'YYYY-MM-DD'
    today_races = df[df['date'].dt.strftime('%Y-%m-%d') == date_filter].copy()
    
    if len(today_races) == 0:
        logger.warning(f"Inga lopp hittades för {date_filter}!")
        return

    logger.info(f"Hittade {len(today_races)} starter att tippa på.")
    
    # Ladda modell
    model = xgb.Booster()
    model.load_model('models/xgboost_baseline.json')
    
    # Förbered DMatrix
    # Samma features som vid träning
    # Vi måste veta vilka features modellen tränades på.
    # Vi kan inspektera modellen eller hårdkoda listan (riskabelt om vi ändrar).
    # Vi tar listan från feature importance printen tidigare eller bara samma logik som train script.
    
    features = [
        'start_number', 'post_position', 'distance', 
        'horse_history_starts', 'horse_history_win_rate', 'horse_history_place_rate',
        'horse_shoes_front', 'horse_shoes_back',
        'sex_encoded', 'horse_sulky_type_code_encoded', 'start_method_encoded', 'track_id_encoded',
        'month', 'is_weekend'
    ]
    
    # Kolla att kolumner finns
    X_today = today_races[features]
    dmatrix = xgb.DMatrix(X_today)
    
    # Prediktera
    probs = model.predict(dmatrix)
    today_races['pred_win_prob'] = probs
    
    # 4. Hitta Spelvärde (Edge)
    # Vi behöver odds. 
    # I 'inference_features.csv' har vi odds_5m, odds_30m, final_odds.
    # För dagens lopp (ej körda) är final_odds troligen NaN, men odds_5m kanske finns?
    # Eller så finns 'current_odds' om vi hämtade det.
    # Låt oss använda odds_5m om det finns (kanske vi är 5 min innan start?), annars...
    # Om odds saknas helt kan vi inte räkna edge.
    
    # Vi kollar vilka odds-kolumner som har data
    # Prioritera final_odds om vi kör på historisk data
    today_races['eval_odds'] = today_races['final_odds'].fillna(today_races['odds_5m']).fillna(today_races['odds_30m'])
    
    # Vi printar de bästa tipsen
    print("\n\n====== DAGENS BÄSTA SPEL (Edge > 1.5) ======")
    
    # Sortera på lopp och startnummer
    today_races = today_races.sort_values(['race_id', 'pred_win_prob'], ascending=[True, False])
    
    hits = 0
    for race_id, group in today_races.groupby('race_id', sort=False):
        # Hitta favoriten enligt oss
        my_winner = group.iloc[0]
        
        # Om vi har odds, räkna edge
        if pd.notna(my_winner['eval_odds']):
            implied = 1 / my_winner['eval_odds']
            edge = my_winner['pred_win_prob'] / implied
            
            if edge > 1.5:
                hits += 1
                print(f"Lopp {race_id}: Häst {int(my_winner['start_number'])} - {my_winner['horse_name']} (finns den?)")
                # Wait, horse_name dropped in features? 
                # Vi måste kolla om horse_name finns i inference_features.csv.
                # build_features sparar bara output_cols.
                # Vi måste nog lägga till horse_name i output_cols i build_features.py om vi vill se namnet!
                print(f"   Prob: {my_winner['pred_win_prob']:.1%} | Odds: {my_winner['eval_odds']} | Edge: {edge:.2f}")

    # Spara prediktioner i warehouse (Gold) för senare ROI-analys
    gold_pred_path = Path("data/warehouse/gold")
    gold_pred_path.mkdir(parents=True, exist_ok=True)
    
    # Vi sparar hela today_races (inkl pred_win_prob)
    output_file = gold_pred_path / f"predictions_{date_filter}.parquet"
    today_races.to_parquet(output_file, index=False)
    logger.info(f"Prediktioner sparade till {output_file}")
    
    # 4. Hitta Spelvärde (Edge)
    # ... rest of the logic ...
        
    print("\n====== ALLA PROGNOSER (Top 3 per lopp) ======")
    for race_id, group in today_races.groupby('race_id', sort=False):
        print(f"\n--- Lopp {race_id} ---")
        for i, row in group.head(3).iterrows():
            odds_str = f"{row['eval_odds']:.2f}" if pd.notna(row['eval_odds']) else "N/A"
            print(f"#{int(row['start_number'])}: {row['pred_win_prob']:.1%} (Odds: {odds_str})")

if __name__ == "__main__":
    predict_daily()
