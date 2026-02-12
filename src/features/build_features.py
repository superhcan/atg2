import pandas as pd
import logging
from pathlib import Path
from sklearn.preprocessing import LabelEncoder

def process_features(input_path, output_path, mode='train'):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info(f"Läser in {input_path}...")
    df = pd.read_csv(input_path, low_memory=False)
    
    # 1. Rensa data som inte är lopp (t.ex. kval, premielopp)
    # I 'train' mode måste vi ha finish_order.
    # I 'inference' mode behåller vi allt (men finish_order kan vara NaN).
    
    initial_len = len(df)
    
    if mode == 'train':
        df = df.dropna(subset=['finish_order', 'date'])
        logger.info(f"TRAIN MODE: Tog bort rader utan finish_order/date. {initial_len} -> {len(df)}")
    else:
        df = df.dropna(subset=['start_time'])
        logger.info(f"INFERENCE MODE: Behåller rader utan finish_order. {initial_len} -> {len(df)}")
    
    # 2. Skapa Target Variabel
    df['target_win'] = (df['finish_order'] == 1).astype(int)
    
    # 3. Feature Engineering
    
    # Datumfunktioner
    df['date'] = pd.to_datetime(df['date'])
    df['start_time'] = pd.to_datetime(df['start_time'], utc=True)
    # Patch: Om start_time saknas, använd datumet som fallback för sortering/feature-extraktion
    df['start_time'] = df['start_time'].fillna(df['date'].dt.tz_localize('UTC'))
    df['month'] = df['date'].dt.month
    df['day_of_week'] = df['date'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # --- Rolling History (Replaces static DB stats) ---
    logger.info("Beräknar historik (rolling stats)...")
    
    # Sortera på datum/tid för att säkerställa att vi inte ser framtiden
    df = df.sort_values(['date', 'start_time'])
    
    # Vi behöver wins för att räkna historik
    # target_win finns redan.
    
    # Gruppera per häst
    # shift(1) är kritiskt! Vi vill veta stats FÖRE detta lopp.
    # cumsum() räknar ihop allt fram till raden
    
    # Hästens starter
    df['horse_history_starts'] = df.groupby('horse_id').cumcount()
    
    # Hästens vinster
    df['horse_history_wins'] = df.groupby('horse_id')['target_win'].transform(lambda x: x.shift(1).fillna(0).cumsum())
    
    # Hästens segerprocent
    # Hantera division med noll
    df['horse_history_win_rate'] = df['horse_history_wins'] / df['horse_history_starts']
    df['horse_history_win_rate'] = df['horse_history_win_rate'].fillna(0)
    
    # Hästens placeringar (Top 3)
    df['target_top3'] = (df['finish_order'] <= 3).astype(int)
    df['horse_history_top3'] = df.groupby('horse_id')['target_top3'].transform(lambda x: x.shift(1).fillna(0).cumsum())
    df['horse_history_place_rate'] = df['horse_history_top3'] / df['horse_history_starts']
    df['horse_history_place_rate'] = df['horse_history_place_rate'].fillna(0)

    # Kön - One-Hot eller Label Encoding
    df['sex'] = df['sex'].fillna('unknown')
    
    # Utrustning
    df['horse_shoes_front'] = df['horse_shoes_front'].fillna(False).astype(int)
    df['horse_shoes_back'] = df['horse_shoes_back'].fillna(False).astype(int)
    
    # Sulky
    df['horse_sulky_type_code'] = df['horse_sulky_type_code'].fillna('unknown')
    
    # Startmetod
    df['start_method'] = df['start_method'].fillna('unknown')
    
    # Distans
    df['distance'] = df['distance'].fillna(2140)
    
    # Label Encoding
    cat_cols = ['sex', 'horse_sulky_type_code', 'start_method', 'sport', 'track_id']
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = df[col].astype(str)
        df[col + '_encoded'] = le.fit_transform(df[col])
        
    # Välj ut kolumner för träning
    # Nu använder vi våra EGNA beräknade features istället för de läckande DB-kolumnerna
    features = [
        'start_number', 'post_position', 'distance', 
        'horse_history_starts', 'horse_history_win_rate', 'horse_history_place_rate', # NEW
        'horse_shoes_front', 'horse_shoes_back',
        'sex_encoded', 'horse_sulky_type_code_encoded', 'start_method_encoded', 'track_id_encoded',
        'month', 'is_weekend'
    ]
    
    # Lägg till 'age' om vi litar på den (den fanns med i SELECT, så vi behåller den, men med nypa salt)
    # df['age'] har tagits bort från SELECT i make_dataset.py om vi följde texten noga, 
    # men vi tog nog bara bort money/stats?
    # I make_dataset.py tog jag bort "h.age, h.money...". Så age finns INTE kvar.
    # Bra, då tar vi bort den från features listan.
    
    # Vi kollar snabbt om age finns i df.columns
    if 'age' in df.columns:
        features.append('age')
        df['age'] = df['age'].fillna(df['age'].median())
    
    # Men eftersom vi tog bort den i make_dataset.py nu, så kommer den inte finnas.
    # Vi kan räkna ut den om vi vill? Nej. Användaren sa "trippelkolla läckage". Bättre att inte ha med den än att ha fel.
    
    # --- Marknads-features (Odds-trender) ---
    odds_trends_path = Path(f"data/warehouse/silver/odds_trends_{df['date'].iloc[0].strftime('%Y-%m-%d')}.parquet")
    if odds_trends_path.exists():
        logger.info("Beräknar marknads-features (odds-trender)...")
        odds_trends = pd.read_parquet(odds_trends_path)
        
        # Enkel trend: Sista oddset vs första tillgängliga snapshotet
        # Vi grupperar per häst och tar första/sista
        trends = odds_trends.sort_values('timestamp').groupby(['race_id', 'horse_id']).agg(
            first_odds=('odds_vinnare', 'first'),
            last_odds=('odds_vinnare', 'last'),
            odds_count=('odds_vinnare', 'count')
        ).reset_index()
        
        trends['odds_drop_percentage'] = (trends['first_odds'] - trends['last_odds']) / trends['first_odds']
        
        # Joina in i huvud-df
        df = df.merge(trends[['race_id', 'horse_id', 'odds_drop_percentage']], on=['race_id', 'horse_id'], how='left')
        df['odds_drop_percentage'] = df['odds_drop_percentage'].fillna(0)
    else:
        df['odds_drop_percentage'] = 0
    
    market_features = ['odds_drop_percentage']

    output_cols = ['race_id', 'horse_id', 'date', 'start_time', 'finish_order', 'target_win', 'final_odds', 'odds_5m', 'odds_30m', 'horse_name'] + features + market_features
    
    logger.info(f"Sparar {len(df)} rader till {output_path}")
    df[output_cols].to_csv(output_path, index=False)

if __name__ == "__main__":
    import sys
    
    input_f = 'data/processed/race_data.csv'
    output_f = 'data/processed/train_ready.csv'
    mode = 'train'
    
    if len(sys.argv) > 1:
        input_f = sys.argv[1]
    if len(sys.argv) > 2:
        output_f = sys.argv[2]
    if len(sys.argv) > 3:
        # Hantera både 'mode=inference' och 'inference'
        mode = sys.argv[3].split('=')[-1]
        
    process_features(input_f, output_f, mode=mode)
