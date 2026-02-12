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
- .github/workflows/: Automationslogik.

## Arbetsflöde (Git)

För att bibehålla ordning och kvalitet följer projektet dessa principer:

1.  **Branching**: Ingen kod pushas direkt till `main` förutom akuta fixar. Ny funktionalitet utvecklas i feature-branches (t.ex. `feat/ny-funktion`).
2.  **Pull Requests**: När en funktion är klar skapas en PR mot `main`.
3.  **Granskning**: Kod ska granskas mot projektets regler i `.cursorrules`.

## Continuous Integration (CI)

Varje push och Pull Request triggar automatiskt ett CI-workflow (`ci.yml`) som genomför följande steg:

1.  **Kodstilsanalys (Linting)**: Använder `ruff` för att säkerställa att Python-koden är ren och följer vedertagna mönster.
2.  **Tester**: Kör enhetstester via `pytest` för att verifiera att logiken i datlagren (Bronze/Silver/Gold) fungerar som förväntat.
