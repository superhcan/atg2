import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys
from datetime import datetime

# Lägg till src i path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))

st.set_page_config(page_title="Trav AI Dashboard", layout="wide")

st.title("🏇 Trav AI - Analys & Tips")

# --- Tabs ---
tab1, tab2, tab3 = st.tabs(["📊 Historisk Analys (ROI)", "🔮 Dagens Tips", "📅 Digitalt Program"])

# --- TAB 1: Historisk Analys ---
with tab1:
    st.header("Modellens Prestanda")
    
    # --- Modellinställningar (Sidebar) ---
    st.sidebar.header("Modell & Strategi")
    
    metadata = None
    tracks_lookup = {}
    versions_dir = 'models/versions'
    available_versions = ["Senaste (Default)"]
    if os.path.exists(versions_dir):
        versions = sorted(os.listdir(versions_dir), reverse=True)
        available_versions += versions
        
    selected_version = st.sidebar.selectbox("Välj Modellersion", available_versions)
    
    # Ladda prediktioner
    # --- Datakälla (Live vs CSV) ---
    data_source = st.sidebar.radio("Datakälla", ["Live (Datalager)", "Test-set (CSV)"])
    
    try:
        if data_source == "Test-set (CSV)":
            if selected_version == "Senaste (Default)":
                pred_file = 'data/processed/test_predictions.csv'
                model_path = 'models/xgboost_latest.json'
            else:
                version_path = os.path.join(versions_dir, selected_version)
                pred_file = os.path.join(version_path, 'predictions.csv')
                model_path = os.path.join(version_path, 'model.json')
            
            df = pd.read_csv(pred_file)
            df['date'] = pd.to_datetime(df['date'])
        else:
            # Ladda alla prediktioner och resultat från Datalagret
            import duckdb
            con = duckdb.connect()
            gold_dir = 'data/warehouse/gold'
            silver_dir = 'data/warehouse/silver'
            
            # Hämta alla datum vi har prediktioner för
            all_preds = []
            if os.path.exists(gold_dir):
                for f in os.listdir(gold_dir):
                    if f.startswith("predictions_") and f.endswith(".parquet"):
                        d_str = f.replace("predictions_", "").replace(".parquet", "")
                        res_file = os.path.join(silver_dir, f"results_{d_str}.parquet")
                        if os.path.exists(res_file):
                            query = f"""
                            SELECT 
                                p.*, 
                                res.scratched,
                                res.final_odds as official_final_odds,
                                CASE WHEN res.finish_order = 1 THEN 1 ELSE 0 END as target_win
                            FROM '{os.path.join(gold_dir, f)}' p
                            LEFT JOIN '{res_file}' res ON p.race_id = res.race_id AND p.horse_id = res.horse_id
                            """
                            day_df = con.execute(query).df()
                            all_preds.append(day_df)
            
            if not all_preds:
                st.warning("Ingen live-data (prediktioner + resultat) hittades i datalagret ännu.")
                st.stop()
            
            df = pd.concat(all_preds)
            df['date'] = pd.to_datetime(df['date'])
            # Mappa kolumner för att matcha CSV-formatet i ROI-logiken
            if 'pred_win_prob' in df.columns:
                # Prioritera officiella final_odds om de finns, annars prediction-time data
                df['eval_odds'] = df['official_final_odds'].fillna(df['final_odds']).fillna(df['odds_5m']).fillna(df['odds_30m'])
            
            model_path = 'models/xgboost_baseline.json'
        
        if metadata:
            st.sidebar.success(f"**Modell-info:**\n- Tränad: {metadata['timestamp']}\n- AUC: {metadata['metrics']['auc']:.3f}\n- Features: {len(metadata['features'])} st")
            
    except Exception as e:
        st.error(f"Kunde inte hitta data för vald version: {e}")
        st.stop()
        
    # --- Land-filtrering (Sverige-fokus) ---
    tracks_lookup_path = 'data/warehouse/tracks_lookup.json'
    tracks_lookup = {}
    if os.path.exists(tracks_lookup_path):
        import json
        with open(tracks_lookup_path, 'r') as f:
            tracks_lookup = json.load(f)
    
    # Extrahera track_id från race_id (Format: YYYY-MM-DD_TRACKID_RACENUM)
    def get_country(race_id):
        try:
            parts = str(race_id).split('_')
            if len(parts) >= 2:
                tid = parts[1]
                return tracks_lookup.get(tid, {}).get('country', 'SE') # SE som fallback
            return 'SE'
        except Exception:
            return 'SE'

    df['country'] = df['race_id'].apply(get_country)
    df['track_name'] = df['race_id'].apply(lambda rid: tracks_lookup.get(str(rid).split('_')[1], {}).get('name', 'Okänd') if len(str(rid).split('_')) >= 2 else 'Okänd')
    
    # Filtrera bort utländska lopp (Användarens önskemål)
    df = df[df['country'] == 'SE'].copy()

    # --- Datumintervall för Analys ---
    min_data_date = df['date'].min().date()
    max_data_date = df['date'].max().date()
    
    date_range = st.sidebar.date_input(
        "Välj Datumintervall",
        value=(min_data_date, max_data_date),
        min_value=min_data_date,
        max_value=max_data_date
    )
    
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        st.subheader(f"Analys för perioden {start_date} till {end_date}")
        df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)].copy()
    elif isinstance(date_range, datetime):
        st.subheader(f"Analys för {date_range}")
        df = df[df['date'].dt.date == date_range].copy()
    else:
        # Fallback if range is partially selected
        st.subheader(f"Analys från {date_range[0]}")
        df = df[df['date'].dt.date >= date_range[0]].copy()

    min_edge = st.sidebar.slider("Minimum Edge", 1.0, 3.0, 1.2, 0.1)
    start_bankroll = st.sidebar.number_input("Startbankrulle (SEK)", value=10000, step=1000)
    strategy = st.sidebar.selectbox("Insatsstrategi", ["Fasta Insatser (100kr)", "Full Kelly", "Halv Kelly (Säkrare)"])
    
    # Använd odds_5m eller final_odds
    if 'eval_odds' not in df.columns:
        df['eval_odds'] = df['odds_5m'].fillna(df['final_odds'])
    
    # Beräkna edge för ROI-analys
    if 'eval_odds' in df.columns and 'pred_win_prob' in df.columns:
        df['eval_prob'] = 1 / df['eval_odds']
        df['edge'] = df['pred_win_prob'] / df['eval_prob']

    # Filtrera data
    # Vi vill bara se lopp som faktiskt har gått (finish_order finns eller vi har live-resultat)
    # I 'Live' läge använder vi target_win (beräknat från finish_order) i dropna
    if data_source == "Live (Datalager)":
        history_df = df.dropna(subset=['target_win', 'eval_odds']).copy()
    else:
        history_df = df.dropna(subset=['finish_order', 'eval_odds']).copy()
    
    # Sortera på datum för korrekt simulering
    history_df = history_df.sort_values(['date', 'start_time'])
    
    # Applicera Edge-filter
    filtered_df = history_df[history_df['edge'] >= min_edge].copy()
    
    # --- Bankroll Simulation ---
    current_bankroll = start_bankroll
    bankroll_history = [start_bankroll]
    stakes = []
    profits = []
    
    for i, row in filtered_df.iterrows():
        # Beräkna insats
        if strategy == "Fasta Insatser (100kr)":
            stake = 100
        else:
            # Kelly: f = (p(b+1) - 1) / b
            # b = odds - 1
            # p = pred_win_prob
            b = row['eval_odds'] - 1
            p = row['pred_win_prob']
            if b > 0:
                f = (p * (b + 1) - 1) / b
            else:
                f = 0
            
            # Justera för Halv Kelly
            if "Halv" in strategy:
                f = f * 0.5
                
            # Max insats (säkerhet): Aldrig mer än 20% av rullen
            f = min(f, 0.20)
            f = max(0, f) # Ingen negativ insats
            
            stake = current_bankroll * f
            
        # Simulera utfall
        if row['target_win'] == 1:
            profit = stake * (row['eval_odds'] - 1)
        else:
            profit = -stake
            
        current_bankroll += profit
        
        # Spara metrics
        stakes.append(stake)
        profits.append(profit)
        bankroll_history.append(current_bankroll)
        
    filtered_df['stake'] = stakes
    filtered_df['profit'] = profits
    filtered_df['cum_bankroll'] = bankroll_history[1:]
    # Skapa ett sekventiellt index för x-axeln om det är samma dag
    filtered_df['spels_nummer'] = range(1, len(filtered_df) + 1)
    
    # --- KPI Metrics ---
    n_bets = len(filtered_df)
    n_wins = filtered_df['target_win'].sum()
    win_rate = n_wins / n_bets if n_bets > 0 else 0
    total_profit = current_bankroll - start_bankroll
    roi = total_profit / sum(stakes) if sum(stakes) > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Antal Spel", n_bets)
    col2.metric("Vinstprocent", f"{win_rate:.1%}")
    col3.metric("Nuvarande Bankrulle", f"{int(current_bankroll)} kr", delta=f"{int(total_profit)} kr")
    col4.metric("ROI (Return on Investment)", f"{roi:.2%}")
    
    # --- ROI Chart ---
    st.subheader(f"Bankrulle-utveckling ({strategy})")
    if n_bets > 0:
        # Vi använder spels_nummer för en snyggare kurva per spelad häst
        fig = px.line(filtered_df, x='spels_nummer', y='cum_bankroll', 
                     title=f"Strategi: {strategy} | Start: {start_bankroll} kr | Edge > {min_edge}", 
                     labels={'cum_bankroll': 'Kronor', 'spels_nummer': 'Spel nummer'},
                     hover_data=['date', 'horse_name', 'stake', 'profit'])
        
        # Snygga till diagrammet
        fig.add_hline(y=start_bankroll, line_dash="dash", line_color="red", annotation_text="Start")
        st.plotly_chart(fig, use_container_width=True, key=f"roi_chart_{strategy}")
    else:
        st.info("Inga spel hittades med dessa filter.")

    # --- Data Table ---
    st.subheader("Senaste Spelen")
    st.dataframe(filtered_df[['date', 'race_id', 'start_number', 'horse_name', 'pred_win_prob', 'eval_odds', 'edge', 'stake', 'profit', 'cum_bankroll']].sort_values('date', ascending=False).style.format({'pred_win_prob': '{:.1%}', 'eval_odds': '{:.2f}', 'edge': '{:.2f}', 'stake': '{:.0f}', 'profit': '{:.0f}', 'cum_bankroll': '{:.0f}'}))

# --- TAB 2: Dagens Tips ---
with tab2:
    st.header("🔮 Kommande Lopp")
    
    # Vi kan köra predict_daily.py logik här, eller läsa en genererad fil.
    # För interaktivitet kör vi logiken live (om det inte är för tungt).
    # Vi behöver importera predict_daily logiken, men anpassad för att returnera dataframe.
    
    st.info("Här visas tips för lopp som ännu inte avgjorts (idag/imorgon).")
    
    # Knapp för att uppdatera
    if st.button("Hämta Dagens Tips"):
        with st.spinner("Analyserar dagens lopp..."):
            # Vi anropar vår funktion (måste importera den eller kopiera logiken)
            # För enkelhetens skull kör vi 'predict_daily.py' som ett sub-process och läser output?
            # Nej, vi har tillgång till koden. Men predict_daily.py är ett script.
            # Vi borde refaktorisera predict_daily.py till att ha en returnerande funktion.
            # Men för nu läser vi bara 'data/processed/inference_features.csv' om den är färsk?
            # Nej, vi kör scriptet via os.system för att generera log och output?
            # Bäst: Import predict_daily function (om vi fixade den).
            
            # Vi gör en snabblösning: Kör predict_daily.py i bakgrunden och fånga output?
            # Eller snyggare: Refaktorera `src/models/predict_daily.py` (redan gjort, men den printar bara).
            
            # Vi läser `data/processed/inference_features.csv` som skapades nyss av predict_daily.py?
            # Den innehåller alla lopp. Vi måste filtrera på dagens datum.
            try:
                # Kör predict daily för att vara säker på att vi har färska features
                # os.system("python src/models/predict_daily.py") # Kan ta tid
                
                # För demo: Läs befintlig
                inf_df = pd.read_csv('data/processed/inference_features.csv')
                inf_df['date'] = pd.to_datetime(inf_df['date'])
                
                # Datumfilter: Idag eller framtid
                today = pd.Timestamp.now().normalize() # Idag kl 00:00
                # Justera datumfilter för att matcha din demo ("2026-02-04")
                demo_date = pd.Timestamp("2026-02-04")
                
                future_races = inf_df[inf_df['date'] >= demo_date].copy()
                
                if len(future_races) == 0:
                    st.warning("Inga kommande lopp hittades i datan.")
                else:
                    # Vi behöver ladda modellen och prediktera här för att få färska probs
                    import xgboost as xgb
                    model = xgb.Booster()
                    model.load_model(model_path)
                    
                    features = [
                        'start_number', 'post_position', 'distance', 
                        'horse_history_starts', 'horse_history_win_rate', 'horse_history_place_rate',
                        'horse_shoes_front', 'horse_shoes_back',
                        'sex_encoded', 'horse_sulky_type_code_encoded', 'start_method_encoded', 'track_id_encoded',
                        'month', 'is_weekend'
                    ]
                    
                    dtest = xgb.DMatrix(future_races[features])
                    future_races['pred_win_prob'] = model.predict(dtest)
                    
                    # Visa bästa spelen
                    # Odds finns kanske?
                    if 'odds_5m' in future_races.columns:
                        future_races['odds'] = future_races['odds_5m']
                        # Beräkna edge
                        future_races['edge'] = future_races.apply(lambda row: (row['pred_win_prob'] * row['odds']) if pd.notna(row['odds']) else 0, axis=1)
                    else:
                        future_races['odds'] = None
                        future_races['edge'] = 0
                        
                    best_bets = future_races[future_races['edge'] > 1.2].sort_values('edge', ascending=False)
                    
                    st.subheader("💎 Heta Tips (Edge > 1.2)")
                    st.dataframe(best_bets[['date', 'race_id', 'start_number', 'horse_name', 'pred_win_prob', 'odds', 'edge', 'horse_history_win_rate']])
                    
                    st.subheader("Alla Lopp")
                    st.dataframe(future_races[['date', 'race_id', 'start_number', 'horse_name', 'pred_win_prob', 'odds']].sort_values(['date', 'race_id', 'pred_win_prob'], ascending=[True, True, False]))
                    
            except Exception as e:
                st.error(f"Ett fel uppstod: {e}")

# --- TAB 3: Digitalt Program ---
with tab3:
    st.header("📅 Digitalt Program")
    st.write("Ett modernt, elektroniskt travprogram med sko-information, vagnrapporter och tränardata.")
    
    # Datumväljare (standard idag)
    prog_date = st.date_input("Välj datum för programmet", value=datetime.today(), key="prog_date_picker")
    prog_date_str = prog_date.strftime("%Y-%m-%d")
    
    silver_races = f'data/warehouse/silver/races_{prog_date_str}.parquet'
    silver_horses = f'data/warehouse/silver/horses_{prog_date_str}.parquet'
    
    if os.path.exists(silver_races) and os.path.exists(silver_horses):
        import duckdb
        con = duckdb.connect()
        
        # Hämta lopp sorterade på starttid (istället för bara loppnummer)
        r_df = con.execute(f"SELECT * FROM '{silver_races}' ORDER BY start_time").df()
        
        if not r_df.empty:
            race_options = [f"Lopp {row['race_num']}: {row['track_name']} ({row['start_time'].split('T')[-1][:5] if row['start_time'] else '??:??'})" for i, row in r_df.iterrows()]
            selected_race_label = st.selectbox("Välj lopp i programmet", race_options)
            
            # Hämta valt lopp-index
            sel_idx = race_options.index(selected_race_label)
            race = r_df.iloc[sel_idx]
            
            # Visa lopp-info
            st.markdown(f"### Lopp {race['race_num']} - {race['track_name']}")
            st.markdown(f"**Distans:** {race['distance']}m | **Startmetod:** {race['start_method']} | **Status:** {race['status']}")
            
            # Hästar
            results_file = f'data/warehouse/silver/results_{prog_date_str}.parquet'
            has_results = os.path.exists(results_file)
            
            if has_results:
                h_query = f"""
                SELECT 
                    h.start_num as Nr,
                    h.post_position as Spår,
                    h.horse_name as Häst,
                    h.age as Ålder,
                    h.sex as Kön,
                    h.money as Prispengar,
                    h.driver_name as Kusk,
                    h.trainer_name as Tränare,
                    h.shoes_front, h.shoes_back,
                    h.sulky_type as Vagn,
                    res.scratched,
                    res.horse_id IS NOT NULL as is_winner
                FROM '{silver_horses}' h
                LEFT JOIN '{results_file}' res ON h.race_id = res.race_id AND h.horse_id = res.horse_id
                WHERE h.race_id = '{race['race_id']}'
                ORDER BY h.start_num
                """
            else:
                h_query = f"""
                SELECT 
                    start_num as Nr,
                    post_position as Spår,
                    horse_name as Häst,
                    age as Ålder,
                    sex as Kön,
                    money as Prispengar,
                    driver_name as Kusk,
                    trainer_name as Tränare,
                    shoes_front, shoes_back,
                    sulky_type as Vagn,
                    FALSE as scratched,
                    FALSE as is_winner
                FROM '{silver_horses}'
                WHERE race_id = '{race['race_id']}'
                ORDER BY start_num
                """
            h_df = con.execute(h_query).df()
            
            # Formatera
            def format_horse_name(row):
                name = row['Häst']
                if row['scratched']:
                    return f"❌ {name} (Struken)"
                if row['is_winner']:
                    return f"🏆 {name}"
                return name

            h_df['Häst'] = h_df.apply(format_horse_name, axis=1)
            h_df['Skor'] = h_df.apply(lambda r: ("👟" if r['shoes_front'] else "🦶") + ("👟" if r['shoes_back'] else "🦶"), axis=1)
            h_df['Kön'] = h_df['Kön'].map({'stallion': 'H', 'mare': 'S', 'gelding': 'V'}).fillna(h_df['Kön'])
            h_df['Prispengar'] = h_df['Prispengar'].apply(lambda x: f"{int(x/100):,} kr" if pd.notna(x) else "0 kr")
            
            # Visa snygg tabell
            st.dataframe(h_df[['Nr', 'Spår', 'Häst', 'Ålder', 'Kön', 'Kusk', 'Tränare', 'Skor', 'Vagn', 'Prispengar']], 
                         hide_index=True, use_container_width=True)
            
            st.caption("🏆 = Vinnare, ❌ = Struken | 👟 = Skor, 🦶 = Barfota | H = Hingst, S = Sto, V = Valack")
        else:
            st.info("Inga lopp hittades i datalagret för detta datum.")
    else:
        st.warning(f"Ingen programdata finns för {prog_date_str}. Kör 'Daily Pipeline' för att hämta framtida data eller byt datum.")
        if st.button("Hämta data för de kommande 3 dagarna nu"):
            with st.spinner("Hämtar data..."):
                import os
                # Vi kör pipelinen i bakgrunden (kortare version 3 dagar)
                os.system("python3 src/data/run_pipeline.py")
                st.success("Data hämtad! Ladda om sidan.")
