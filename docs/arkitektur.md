# Projektarkitektur: ATG2

Detta projekt är ett automatiserat system för insamling, processering och analys av travdata från ATG. Målet är att identifiera marknadsrörelser ("Smart Money") och använda maskininlärning för att hitta spelvärda lopp.

## Systemöversikt

Systemet är uppdelat i fyra huvudmoduler:

1.  **Datainsamling (Bronze)**: Hämtar rå JSON-data från ATG:s API.
2.  **Datatransformering (Silver)**: Strukturerar och rensar rådata till Parquet-filer.
3.  **Analys & Guld (Gold)**: Skapar aggregerade sammanfattningar och beräknar statistik.
4.  **Bevakning (Live)**: JIT-övervakning av odds i realtid via GitHub Actions.

## Teknisk Stack

- **Språk**: Python 3.x
- **Datalagring**: Parquet (lokalt datalager), PostgreSQL (historisk databas)
- **Modellering**: XGBoost
- **Dashboard**: Streamlit
- **Automation**: GitHub Actions

## Filstruktur

- `src/data/`: Kod för insamling och parsing.
- `src/models/`: Träning och prediktion.
- `src/dashboard/`: Streamlit-app för visualisering.
- `docs/`: Detaljerad projektdokumentation.
- `.github/workflows/`: Automationslogik.
