# ATG2 - Intelligent Travanalys

ATG2 är ett avancerat system för att samla in trazinformation och förutsäga vinnare med hjälp av maskininlärning. Genom att kombinera historisk statistik med realtidsbevakning av odds-rörelser ("Smart Money") hjälper systemet till att hitta spelvärda hästar med en statistisk fördel.

## 🚀 Snabbstart

1. **Installera beroenden**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Hämta dagens data**:
   ```bash
   python src/data/run_pipeline.py
   ```
3. **Starta Dashboard**:
   ```bash
   streamlit run src/dashboard/app.py
   ```

## 📚 Dokumentation

All detaljerad dokumentation finns nu samlad i mappen `docs/`:

- [**Arkitekturbeskrivning**](docs/arkitektur.md) - Hur systemet hänger ihop.
- [**Datalager**](docs/datalager.md) - Om Bronze, Silver och Gold-nivåerna.
- [**Automatisk Bevakning**](docs/bevakning.md) - GitHub Actions och JIT-övervakning.
- [**Modellering & ROI**](docs/modellering.md) - XGBoost och beräkning av "edge".
- [**Projekthistorik**](docs/historik.md) - Logg över utförda uppgifter och milstolpar.

---
*Detta projekt är utvecklat för analys och utbildning. Spela ansvarsfullt.*
