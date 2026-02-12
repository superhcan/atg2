# Projekthistorik & Milstolpar

Här loggas de viktigaste framstegen och besluten som tagits under projektets gång.

## Milstolpar

### 2026-02-12: Optimering & Molnbevakning
- **95% snabbare insamling**: Optimerade `atg_collector.py` för att prioritera V/P/T-pooler.
- **GitHub Actions**: Driftsatte JIT-övervakning i molnet dygnet runt.
- **Data Gap Fill**: Fyllde i historisk data för perioden 8-11 februari.
- **Omsättningsspårning**: Implementerade parsing av turnover för Tvilling-poolen.

### 2026-02-05: Liveodds & Tidsserier
- **Odds Monitor**: Skapade den första versionen av realtidsövervakaren.
- **Bronze -> Silver**: Implementerade den första tidsserien för odds-snapshots.

### 2024-02-04: Grundläggning & Datalager
- **Project Init**: Grundstruktur för datalager (Bronze/Silver/Gold).
- **Svenskt filter**: Bestämde att fokusera 100% på svenska banaer (`countryCode == 'SE'`).

## Historiska Resultat (Exempel från initial körning)
Vid den första testkörningen (2026-02-04) identifierades följande hästar med hög edge:
- **#3 - V.P.G.** (Edge: 6.99)
- **#5 - Listas Champion** (Edge: 1.99)
- **#5 - Loke Lovebyte** (Edge: 2.37)
