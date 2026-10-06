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

De berekening gebruikt jaarlijkse bedragen. Percentages worden als decimalen in de formules gebruikt: 8% is bijvoorbeeld 0,08. De rendementseis heeft een onder- en bovengrens; het midden van die range is de centrale aanname voor alle overige uitkomsten.

### Huur en waarde

| Uitkomst | Formule |
| --- | --- |
| Bruto jaarhuur | Verhuurbaar oppervlak × markthuur per m² per jaar |
| Effectieve jaarhuur | Bruto jaarhuur × (1 − leegstand en oninbaar) |
| Exploitatiekosten, percentage | Effectieve jaarhuur × exploitatiekostenpercentage |
| Exploitatiekosten, uitgesplitst | Som van onderhoud, verzekering, OZB/eigenaarslasten, beheer en overige kosten |
| NOI (netto bedrijfsresultaat) | Effectieve jaarhuur − exploitatiekosten |
| Centrale rendementseis | (Laagste rendementseis + hoogste rendementseis) ÷ 2 |
| Centrale indicatieve waarde | max(NOI ÷ centrale rendementseis, 0) |
| Lage waardegrens | max(NOI ÷ hoogste rendementseis, 0) |
| Hoge waardegrens | max(NOI ÷ laagste rendementseis, 0) |

De rendementseis is positief. Een hogere rendementseis geeft een lagere waarde. Als de NOI negatief is, worden de indicatieve waarde en beide grenzen op nul gezet.

### Aankoop en belasting

| Uitkomst | Formule |
| --- | --- |
| Aanschafprijs | Opgegeven koopprijs als die groter is dan nul; anders de centrale indicatieve waarde |
| Grondslag overdrachtsbelasting | max(centrale indicatieve waarde, opgegeven koopprijs) |
| Overdrachtsbelasting | Grondslag overdrachtsbelasting × ingevoerd tarief (standaard 10,4%) |
| Initiële projectinvestering | Aanschafprijs + overige aankoopkosten + renovatie + overdrachtsbelasting |
| Totale investering | Initiële projectinvestering + eenmalige financieringskosten |

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
| Kasstroom na rente | NOI − rentelasten |
| Kasstroom na rente en aflossing | NOI − jaarlijkse rente- en aflossingslast |
| Kasstroomrendement op eigen inbreng | Kasstroom na rente en aflossing ÷ eigen inbreng; 0 als eigen inbreng niet positief is |

De annuïteit gebruikt jaarlijkse rente- en betaalperioden. De getoonde aflossing is die van het eerste jaar; bij annuïtair aflossen verandert de verhouding tussen rente en aflossing daarna.

### Waardegroei en rendement

| Uitkomst | Formule |
| --- | --- |
| Grondslag waardestijging | Aanschafprijs |
| Verwachte waardestijging per jaar | Grondslag waardestijging × ingevoerd waardestijgingspercentage |
| Totaalrendement in euro's, inclusief waardegroei | NOI + verwachte waardestijging per jaar |
| Rendement op totale investering, exclusief waardegroei | NOI ÷ totale investering |
| Rendement op totale investering, inclusief waardegroei | (NOI + verwachte waardestijging per jaar) ÷ totale investering |
| Kasstroomrendement op eigen inbreng | Kasstroom na rente en aflossing ÷ eigen inbreng; 0 als eigen inbreng niet positief is |

De twee rendementscijfers op totale investering gebruiken de **totale investering** als noemer. Het kasstroomrendement gebruikt de **eigen inbreng** als noemer. Waardegroei is een aanname, geen kasstroom of garantie. De aankoop-, belasting-, financierings- en rendementscijfers worden berekend met de centrale rendementseis, niet afzonderlijk met beide uiteinden van de range.

Dit is een indicatief model, geen volledige taxatie of financieringsaanbieding. Controleer onder meer de fiscale grondslag, het toepasselijke overdrachtsbelastingtarief, btw-regels, huurcontracten, onderhoud en financieringsvoorwaarden. Niet ingevoerde kosten en belastingen worden niet automatisch meegenomen. De standaardwaarden zijn voorbeelden en geen marktdata.