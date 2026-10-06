from datetime import date
from html import escape
import re
from typing import Any

import streamlit as st

from reporting import euro, percent, report_pdf
from valuation import calculate_valuation


st.set_page_config(page_title="Bedrijfspand berekening", layout="wide")

with st.sidebar:
    st.header("Object en aannames")
    st.markdown("#### Kerngegevens")
    purchase_price = st.number_input(
        "Koopprijs (€)", min_value=0, value=0, step=10000,
        help="Vul 0 in om de berekende waarde als aanschafprijs te gebruiken.",
    )
    yield_rate_range = st.slider(
        "Rendementseis voor waardering (%)", 3.0, 15.0, (7.0, 9.0), 0.25,
        help="De laagste rendementseis geeft de hoogste waarde. Overige berekeningen gebruiken het midden van de range.",
    )
    yield_rate_range = (yield_rate_range[0] / 100, yield_rate_range[1] / 100)
    yield_rate = sum(yield_rate_range) / 2
    area_m2 = st.number_input("Verhuurbaar oppervlak (m²)", min_value=1, value=800, step=25)
    rent_per_m2 = st.number_input("Markthuur per jaar per m² (€)", min_value=0.0, value=85.0, step=5.0)
    vacancy_rate = st.slider("Leegstand en oninbaar (%)", 0, 100, 5) / 100

    value_growth_rate = st.slider("Verwachte waardestijging per jaar (%)", -10.0, 20.0, 2.0, 0.25) / 100

    st.markdown("#### Kosten en financiering")
    purchase_costs = st.number_input(
        "Overige aankoopkosten excl. overdrachtsbelasting (€)", min_value=0, value=25000, step=5000
    )
    renovation_costs = st.number_input("Investering / renovatie (€)", min_value=0, value=50000, step=5000)

    st.markdown("##### Exploitatiekosten")
    detailed_operating_costs = st.checkbox("Exploitatiekosten uitsplitsen", value=False)
    operating_cost_items = {}
    if detailed_operating_costs:
        st.caption("Vul de verwachte jaarlijkse kosten in.")
        operating_cost_items = {
            "Onderhoud": st.number_input("Onderhoud per jaar (€)", min_value=0, value=0, step=1000),
            "Verzekering": st.number_input("Verzekering per jaar (€)", min_value=0, value=0, step=500),
            "OZB en eigenaarslasten": st.number_input("OZB en eigenaarslasten per jaar (€)", min_value=0, value=0, step=500),
            "Beheer": st.number_input("Beheer per jaar (€)", min_value=0, value=0, step=500),
            "Overig": st.number_input("Overige exploitatiekosten per jaar (€)", min_value=0, value=0, step=500),
        }
        operating_cost_rate = 0.0
        annual_operating_costs = sum(operating_cost_items.values())
    else:
        operating_cost_rate = st.slider("Exploitatiekosten (% van effectieve huur)", 0, 40, 15) / 100
        annual_operating_costs = None

    loan_to_value = st.slider(
        "Loan-to-value (%)", 0, 100, 65,
        help="Berekend over de laagste van de koopprijs en indicatieve waarde; bij koopprijs 0 over de indicatieve waarde.",
    ) / 100
    if loan_to_value > 0:
        financing_rate = st.slider("Financieringsrente (%)", 0.0, 12.0, 5.0, 0.25) / 100
        repayment_type_label = st.selectbox("Aflossingsvorm", ["Annuïtair", "Aflossingsvrij"])
        repayment_type = "annuity" if repayment_type_label == "Annuïtair" else "interest_only"
        loan_term_years = st.slider("Looptijd financiering (jaar)", 1, 30, 20)
        loan_term_label = f"{loan_term_years} jaar"
        loan_fee_rate = st.number_input(
            "Eenmalige financieringskosten (% van lening)", min_value=0.0, max_value=10.0, value=1.0, step=0.1
        ) / 100
    else:
        financing_rate = 0.0
        repayment_type_label = "Geen financiering"
        repayment_type = "interest_only"
        loan_term_years = 20
        loan_term_label = "Niet van toepassing"
        loan_fee_rate = 0.0
    transfer_tax_rate = st.number_input(
        "Overdrachtsbelasting (%)", min_value=0.0, max_value=25.0, value=10.4, step=0.1
    ) / 100

    st.markdown("#### Rapport")
    object_name = st.text_input("Objectnaam voor rapport", value="Bedrijfspand")

calc_inputs = {
    "area_m2": area_m2,
    "rent_per_m2": rent_per_m2,
    "vacancy_rate": vacancy_rate,
    "operating_cost_rate": operating_cost_rate,
    "yield_rate": yield_rate,
    "yield_rate_range": yield_rate_range,
    "purchase_costs": purchase_costs,
    "renovation_costs": renovation_costs,
    "financing_rate": financing_rate,
    "loan_to_value": loan_to_value,
    "transfer_tax_rate": transfer_tax_rate,
    "purchase_price": purchase_price,
    "value_growth_rate": value_growth_rate,
    "annual_operating_costs": annual_operating_costs,
    "loan_fee_rate": loan_fee_rate,
    "repayment_type": repayment_type,
    "loan_term_years": loan_term_years,
}
result = calculate_valuation(**calc_inputs)
inputs: dict[str, Any] = {
    **calc_inputs,
    "detailed_operating_costs": detailed_operating_costs,
    "operating_cost_items": operating_cost_items,
    "repayment_type_label": repayment_type_label,
    "loan_term_label": loan_term_label,
}

inputs["acquisition_price"] = result["acquisition_price"]
inputs["annual_operating_costs"] = result["annual_operating_costs"]
report_date = date.today().strftime("%d-%m-%Y")
pdf_data = report_pdf(object_name.strip() or "Bedrijfspand", report_date, inputs, result)
filename = re.sub(r"[^A-Za-z0-9_-]+", "-", object_name.strip()).strip("-") or "bedrijfspand"

title_column, download_column = st.columns([4, 1])
title_column.title("Indicatieve waardering")
title_column.caption(f"{object_name.strip() or 'Bedrijfspand'}  ·  Rapportdatum {report_date}")
download_column.download_button(
    "Download PDF",
    data=pdf_data,
    file_name=f"waarderingsrapport-{filename}.pdf",
    mime="application/pdf",
    icon=":material/download:",
    use_container_width=True,
)

st.markdown("#### Kerncijfers")
first_row = st.columns(2)
first_row[0].metric(
    "Indicatieve waarde",
    f"{euro(result['value_range_low'])} - {euro(result['value_range_high'])}",
)
first_row[1].metric("Totale investering", euro(result["total_cost"]))
second_row = st.columns(2)
second_row[0].metric("Eigen inbreng", euro(result["equity_required"]))
second_row[1].metric("Kasstroom na rente en aflossing per jaar", euro(result["cash_flow_after_debt_service"]))

st.markdown("#### Rendement")
return_row = st.columns(3)
return_row[0].metric("Rendement exclusief waardegroei", percent(result["yield_on_total_cost"]))
return_row[1].metric("Rendement inclusief waardegroei", percent(result["yield_including_value_growth"]))
return_row[2].metric("Kasstroomrendement op eigen inbreng", percent(result["cash_on_cash_return"]))

st.divider()
income_column, investment_column = st.columns(2, gap="large")


def render_detail_table(rows: list[tuple[str, str]]) -> None:
    body = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>" for label, value in rows
    )
    st.markdown(
        f'<table class="valuation-table"><tbody>{body}</tbody></table>',
        unsafe_allow_html=True,
    )


st.markdown(
    """
    <style>
    .valuation-table { width: 100%; border-collapse: collapse; margin: 0 0 1.2rem; }
    .valuation-table tr { border-bottom: 1px solid rgba(120, 140, 135, .25); }
    .valuation-table th, .valuation-table td { padding: .58rem .35rem; text-align: left; }
    .valuation-table th { color: #75817e; font-size: .86rem; font-weight: 400; }
    .valuation-table td { color: inherit; font-size: .92rem; font-weight: 600; text-align: right; }
    </style>
    """,
    unsafe_allow_html=True,
)

with income_column:
    st.markdown("#### Huur en waardering")
    render_detail_table([
        ("Bruto jaarhuur", euro(result["gross_rent"])),
        ("Effectieve jaarhuur", euro(result["effective_rent"])),
        ("Exploitatiekosten / jaar", euro(result["annual_operating_costs"])),
        ("Netto bedrijfsresultaat (NOI)", euro(result["noi"])),
        ("Rendementseis (range)", f"{percent(yield_rate_range[0])} - {percent(yield_rate_range[1])}"),
        ("Centrale rendementseis", percent(yield_rate)),
        ("Indicatieve waarde (range)", f"{euro(result['value_range_low'])} - {euro(result['value_range_high'])}"),
        ("Verwachte waardestijging per jaar", percent(value_growth_rate)),
        ("Grondslag waardestijging", euro(result["value_growth_basis"])),
        ("Waardestijging per jaar", euro(result["annual_value_growth"])),
        ("Rendement exclusief waardegroei", percent(result["yield_on_total_cost"])),
        ("Rendement inclusief waardegroei", percent(result["yield_including_value_growth"])),
    ])
    if detailed_operating_costs:
        st.markdown("#### Uitsplitsing jaarlijkse exploitatiekosten")
        render_detail_table([(name, euro(amount)) for name, amount in operating_cost_items.items()])

with investment_column:
    st.markdown("#### Aankoop en financiering")
    render_detail_table([
        ("Aanschafprijs", euro(result["acquisition_price"])),
        ("Grondslag overdrachtsbelasting", euro(result["transfer_tax_base"])),
        ("Overdrachtsbelasting", euro(result["transfer_tax"])),
        ("Overige aankoopkosten", euro(purchase_costs)),
        ("Investering / renovatie", euro(renovation_costs)),
        ("Totale investering incl. financieringskosten", euro(result["total_cost"])),
        ("LTV-grondslag", euro(result["financing_basis"])),
        ("Financiering", euro(result["loan_amount"])),
        ("Eenmalige financieringskosten", euro(result["financing_fees"])),
        ("Rentelasten / jaar", euro(result["interest_cost"])),
        ("Aflossing eerste jaar", euro(result["principal_repayment"])),
        ("Rente- en aflossingslasten per jaar", euro(result["annual_debt_service"])),
    ])

with st.expander("Alle gebruikte uitgangspunten", expanded=False):
    assumption_left, assumption_right = st.columns(2)
    with assumption_left:
        operating_cost_label = "Gespecificeerd per kostenpost" if detailed_operating_costs else percent(operating_cost_rate)
        render_detail_table([
            ("Verhuurbaar oppervlak", f"{area_m2:,.0f} m²"),
            ("Markthuur per m² / jaar", euro(rent_per_m2)),
            ("Leegstand en oninbaar", percent(vacancy_rate)),
            ("Exploitatiekosten", operating_cost_label),
            ("Rendementseis (range)", f"{percent(yield_rate_range[0])} - {percent(yield_rate_range[1])}"),
            ("Centrale rendementseis", percent(yield_rate)),
            ("Verwachte waardestijging", percent(value_growth_rate)),
        ])
    with assumption_right:
        render_detail_table([
            ("Koopprijs", euro(purchase_price) if purchase_price else "Niet opgegeven"),
            ("Aanschafprijs in berekening", euro(result["acquisition_price"])),
            ("Overdrachtsbelastingtarief", percent(transfer_tax_rate)),
            ("Loan-to-value", percent(loan_to_value)),
            ("LTV-grondslag", euro(result["financing_basis"])),
            ("Financieringsrente", percent(financing_rate)),
            ("Aflossingsvorm", repayment_type_label),
            ("Looptijd", loan_term_label),
            ("Financieringskosten", percent(loan_fee_rate)),
        ])

st.info(
    "Deze berekening is indicatief. De ingevulde standaardwaarden zijn voorbeeld-aannames, "
    "geen marktdata. Controleer de objectgegevens, fiscale grondslag en toepasselijke regels "
    "voordat je resultaten voor een transactie gebruikt. Verwachte waardestijging is onzeker "
    "en geen gegarandeerd rendement of kasstroom."
)

