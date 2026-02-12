# Datalager: Bronze, Silver & Gold

ATG2 använder en "Medallion Architecture" för att hantera dataflödet effektivt.

## 1. Bronze (Rådata)
- **Plats**: `data/warehouse/bronze/`
- **Format**: JSON
- **Innehåll**: Oförändrad rådata direkt från ATG API. Sparas med tidsstämpel för att möjliggöra historisk omspelning (replay).
- **Viktiga typer**: `calendar`, `games`, `vp`, `vinnare`, `plats`, `tvilling`.

## 2. Silver (Strukturerad data)
- **Plats**: `data/warehouse/silver/`
- **Format**: Parquet
- **Transformation**: JSON-filer parsas och slås ihop till tabeller.
- **Viktiga filer**:
  - `races_YYYY-MM-DD.parquet`: Grunddata om loppen (distans, bana, startmetod).
  - `horses_YYYY-MM-DD.parquet`: Startlistor och häststats.
  - `results_YYYY-MM-DD.parquet`: Slutgiltiga resultat och odds.
  - `odds_trends_YYYY-MM-DD.parquet`: Tidsserier av odds och omsättning för V/P/T.

## 3. Gold (Analysfärdig data)
- **Plats**: `data/warehouse/gold/`
- **Format**: Parquet
- **Syfte**: Aggregerad data optimerad för maskininlärning och dashboards.
- **Exempel**: Daily summaries, ROI-beräkningar och feature sets för XGBoost.

## Datapipelinen
Körs via `src/data/run_pipeline.py` eller manuellt via:
1. `atg_collector.py` (Hämta)
2. `silver_parser.py` (Transformera)
3. `gold_analyzer.py` (Aggregera)
