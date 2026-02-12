# -*- coding: utf-8 -*-
import click
import logging
from pathlib import Path

@click.command()
@click.argument('output_filepath', type=click.Path())
def main(output_filepath):
    """ Hämtar data från databasen (READ ONLY) och sparar som en samlad CSV/Parquet.
        Kombinerar grunddata (2024-) med detaljerad oddsdata (sent 2025-).
    """
    logger = logging.getLogger(__name__)
    logger.info('Startar datainläsning från databas (READ ONLY)...')
    
    # Databaskonfiguration
    db_config = {
        "host": "192.168.0.22",
        "port": "5432",
        "database": "atg_db",
        "user": "atg",
        "password": "atgpass"
    }

    from sqlalchemy import create_engine
    import pandas as pd
    
    # Skapa anslutningssträng
    connection_str = f"postgresql+psycopg2://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    engine = create_engine(connection_str)

    try:
        # 1. Hämta grunddata: Lopp, Startlistor och Hästinformation
        logger.info("Hämtar grunddata (Race + Entry + Horse) från 2024-01-01...")
        query_base = """
            SELECT 
                r.id as race_id, r.date, r.start_time, r.track_id, r.distance, r.start_method, r.sport, 
                e.id as entry_id, e.start_number, e.horse_id, e.post_position,
                e.final_odds, e.finish_order,
                e.horse_shoes_front, e.horse_shoes_back, 
                e.horse_sulky_type_code,
                h.name as horse_name, h.sex
            FROM atgapi_race r
            JOIN atgapi_entry e ON r.id = e.race_id
            LEFT JOIN atgapi_horse h ON e.horse_id = h.id
            WHERE r.date >= '2024-01-01'
            AND r.track_country_code = 'SE'
        """
        df_base = pd.read_sql(query_base, engine)
        logger.info(f"Hämtade {len(df_base)} rader grunddata.")

        # 2. Hämta odds-snapshots för perioden där det finns (t.ex. från 2025-12-01)
        # Vi är intresserade av odds ca 30 min (t.ex. 25-35 min) och 5 min (3-7 min) innan start.
        logger.info("Hämtar odds-snapshots (RacingMlOddsSnapshot)...")
        
        # För att inte hämta ALLT, filtrerar vi på datum i where-satsen om möjligt, 
        # men snapshot-tabellen har kanske inte datum direkt. Vi joinar eller filtrerar på IDn om vi kan.
        # Enklast är att hämta snapshots som matchar våra race_ids, men det blir en tung query.
        # Vi hämtar snapshots där minutes_to_start är relevant.
        
        query_snapshots = """
            SELECT 
                race_id, start_number, minutes_to_start, odds, snapshot_time
            FROM racing_ml_odds_snapshot
            WHERE minutes_to_start BETWEEN 3 AND 40
            AND snapshot_time >= '2025-12-01'
        """
        df_snaps = pd.read_sql(query_snapshots, engine)
        logger.info(f"Hämtade {len(df_snaps)} odds-snapshots.")

        # 3. Bearbeta snapshots för att hitta "30 min" och "5 min"
        # Vi vill ha EN rad per häst+lopp med kolumnerna odds_30m, odds_5m.
        
        # Hitta snapshot närmast 30 min (t.ex. mellan 25 och 35)
        df_30m = df_snaps[(df_snaps['minutes_to_start'] >= 25) & (df_snaps['minutes_to_start'] <= 35)].copy()
        # Sortera så vi kan ta den närmaste/senaste om det finns dubbletter, eller bara ta medel?
        # Vi tar den som är närmast 30 min? Eller bara första bästa.
        # Låt oss sortera på abs(diff från 30) och ta första.
        df_30m['diff_30'] = (df_30m['minutes_to_start'] - 30).abs()
        df_30m = df_30m.sort_values('diff_30').groupby(['race_id', 'start_number']).first().reset_index()
        df_30m = df_30m[['race_id', 'start_number', 'odds']].rename(columns={'odds': 'odds_30m'})

        # Hitta snapshot närmast 5 min
        df_5m = df_snaps[(df_snaps['minutes_to_start'] >= 3) & (df_snaps['minutes_to_start'] <= 7)].copy()
        df_5m['diff_5'] = (df_5m['minutes_to_start'] - 5).abs()
        df_5m = df_5m.sort_values('diff_5').groupby(['race_id', 'start_number']).first().reset_index()
        df_5m = df_5m[['race_id', 'start_number', 'odds']].rename(columns={'odds': 'odds_5m'})

        # 4. Joina ihop allt
        logger.info("Joinar ihop dataset...")
        df_final = pd.merge(df_base, df_30m, on=['race_id', 'start_number'], how='left')
        df_final = pd.merge(df_final, df_5m, on=['race_id', 'start_number'], how='left')

        # Spara
        output_path = Path(output_filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Om filändelse är csv sparar vi csv, annars pickle/parquet
        if output_path.suffix == '.csv':
            df_final.to_csv(output_path, index=False)
        else:
            df_final.to_pickle(output_path)
            
        logger.info(f"Sparade slutgiltigt dataset till {output_path} med {len(df_final)} rader.")
        
    except Exception as e:
        logger.error(f"Ett fel uppstod: {e}")
        raise e

if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    # inte används direkt men praktiskt
    project_dir = Path(__file__).resolve().parents[2]

    main()
