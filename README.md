# Bedrijfspand berekening

Een interactieve Streamlit-rekentool voor een indicatieve bedrijfspandberekening. De invoervelden staan links; de resultaten worden direct bijgewerkt. De resultatenpagina bevat een overzichtelijke businesscase en een downloadbaar PDF-rapport.

## Omgeving starten

Vereist Python 3.12 of hoger.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open daarna de lokale URL die Streamlit in de terminal toont (standaard `http://localhost:8501`).

## Tests

Voer vanuit de projectmap met de virtuele omgeving actief uit:

```powershell
python -m unittest discover -s tests -v
```

## Berekening

De berekening gebruikt jaarlijkse bedragen. Percentages worden als decimalen in de formules gebruikt: 8% is bijvoorbeeld 0,08. De waardering gebruikt uitsluitend het netto aanvangsrendement (NAR). De gebruiker kiest een type vastgoed (kantoor, winkel, bedrijfsruimte/logistiek of overig); daarbij hoort op de achtergrond een indicatieve NAR-range (zie `NAR_RANGES` in `valuation.py`). Het midden van die range is de centrale aanname voor alle overige uitkomsten. De ranges zijn eigen voorbeeld-aannames, geen gepubliceerde marktdata. Waardestijging van het onderliggende vastgoed maakt geen deel uit van het model.

### Huur en waarde

Het NAR is gedefinieerd als de NOI gedeeld door de koopprijs plus kosten koper (overdrachtsbelasting en overige aankoopkosten). De indicatieve waarde is daarom de koopprijs **exclusief** kosten koper.

| Uitkomst | Formule |
| --- | --- |
| Bruto jaarhuur | Verhuurbaar oppervlak × markthuur per m² per jaar |
| Effectieve jaarhuur | Bruto jaarhuur × (1 − leegstand en oninbaar) |
| Exploitatiekosten, percentage | Effectieve jaarhuur × exploitatiekostenpercentage |
| Exploitatiekosten, uitgesplitst | Som van onderhoud, verzekering, OZB/eigenaarslasten, beheer en overige kosten |
| NOI (netto bedrijfsresultaat) | Effectieve jaarhuur − exploitatiekosten |
| Centrale NAR | (Laagste NAR + hoogste NAR) ÷ 2 |
| Centrale indicatieve waarde | max((NOI ÷ centrale NAR − overige aankoopkosten) ÷ (1 + overdrachtsbelastingtarief), 0) |
| Lage waardegrens | Idem, met de hoogste NAR |
| Hoge waardegrens | Idem, met de laagste NAR |

De NAR is positief. Een hogere NAR geeft een lagere waarde. Als de NOI negatief is, worden de indicatieve waarde en beide grenzen op nul gezet.

### Aankoop en belasting

| Uitkomst | Formule |
| --- | --- |
| Aanschafprijs | Opgegeven koopprijs als die groter is dan nul; anders de centrale indicatieve waarde |
| Grondslag overdrachtsbelasting | max(centrale indicatieve waarde, opgegeven koopprijs) |
| Overdrachtsbelasting | Grondslag overdrachtsbelasting × ingevoerd tarief (standaard 10,4%) |
| Totale investering | Aanschafprijs + overige aankoopkosten + renovatie + overdrachtsbelasting + eenmalige financieringskosten |

### Financiering en kasstroom

De financieringsgrondslag is de laagste van de centrale indicatieve waarde en aanschafprijs. Bij een niet-opgegeven koopprijs is de aanschafprijs gelijk aan de centrale indicatieve waarde.

| Uitkomst | Formule |
| --- | --- |
| Financieringsgrondslag | min(centrale indicatieve waarde, aanschafprijs) |
| Lening | Financieringsgrondslag × loan-to-value (LTV) |
| Eenmalige financieringskosten | Lening × financieringskostenpercentage |
| Rentelasten per jaar | Lening × financieringsrente |
| Jaarlast, aflossingsvrij | Rentelasten per jaar |
| Jaarlast, annuïtair | Lening × rente ÷ (1 − (1 + rente)<sup>−looptijd</sup>); bij 0% rente: lening ÷ looptijd |
| Aflossing in jaar één | max(jaarlast − rentelasten, 0) |
| Eigen inbreng | Totale investering − lening |
| Kasstroom na rente en aflossing | NOI − jaarlijkse rente- en aflossingslast |

De annuïteit gebruikt jaarlijkse rente- en betaalperioden. De getoonde aflossing is die van het eerste jaar; bij annuïtair aflossen verandert de verhouding tussen rente en aflossing daarna.

### Rendement

| Uitkomst | Formule |
| --- | --- |
| Rendement op totale investering | NOI ÷ totale investering |

Het rendement op totale investering gebruikt de **totale investering** als noemer. De aankoop-, belasting-, financierings- en rendementscijfers worden berekend met de centrale NAR, niet afzonderlijk met beide uiteinden van de range.

Dit is een indicatief model, geen volledige taxatie of financieringsaanbieding. Controleer onder meer de fiscale grondslag, het toepasselijke overdrachtsbelastingtarief, btw-regels, huurcontracten, onderhoud en financieringsvoorwaarden. Niet ingevoerde kosten en belastingen worden niet automatisch meegenomen. De NAR-ranges en overige standaardwaarden zijn voorbeelden en geen marktdata.