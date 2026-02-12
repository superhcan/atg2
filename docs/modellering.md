# Modellering & ROI-Analys

Hjärtat i ATG2:s beslutsstöd är en XGBoost-modell som tränas på historiska lopp för att prediktera vinstchanser.

## XGBoost Modell
- **Mål**: Prediktera sannolikheten för att en häst vinner loppet (`target_win`).
- **Features**: 
  - Grunddata: Distans, bana, startmetod, kön, ålder.
  - Form: Tidigare prestationer och prispengar.
  - Dynamiska: Odds-rörelser och omsättningstrender (under utveckling).

##ROI och "Edge"
Modellen används inte bara för att tippa vinnare, utan för att hitta spelvärde.
- **Implied Probability**: 1 / aktuellt odds.
- **Predikterad Sannolikhet**: Modellens beräknade vinstchans.
- **Edge**: Predikterad Sannolikhet / Implied Probability.

Exempel: Om en häst har oddset 4.00 (implied 25%) och modellen ger den 37.5% vinstchans, är edgen **1.5** (50% högre än marknaden).

## Träning
Scriptet `src/models/train_xgboost.py` sköter:
1. Inläsning av data.
2. Split i träning/test.
3. Hyperparameteroptimering.
4. Export av `model.json` och metadata.
