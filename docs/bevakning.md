# Automatisk Bevakning & JIT

För att fånga marknadsrörelser precis innan loppen startar använder ATG2 en automatiserad molnlösning via GitHub Actions.

## JIT (Just-In-Time) Övervakning
Istället för att hämta data dygnet runt, aktiveras en intensiv bevakning endast när det är dags för trav.

- **Källa**: `.github/workflows/odds_collector.yml`
- **Script**: `src/data/odds_monitor.py`
- **Schemaläggning**:
  - Lunchtrav (ca kl 11:50)
  - Kvällstrav (ca kl 17:50)

## Snapshot-intervall
Monitorn sparar ner fullständiga odds för Vinnare, Plats och Tvilling vid följande tidpunkter före start:
- 120, 60, 30 minuter (Långsiktiga trender)
- 15, 10, 5 minuter (Marknaden börjar sätta sig)
- 2, 1 minut (De sista tunga insatserna / "Smart Money")

## Datasync
Under en aktiv session skickas nyinsamlad data (Bronze JSON) tillbaka till projektet var 15:e minut via automatiska commits. Detta gör att det lokala datalagret alltid är uppdaterat inför analys.
