from __future__ import annotations

from math import isfinite

# Indicatieve NAR-ranges (netto aanvangsrendement) per type; eigen aannames, geen gepubliceerde marktdata.
NAR_RANGES: dict[str, tuple[float, float]] = {
    "Kantoor": (0.055, 0.075),
    "Winkel": (0.060, 0.080),
    "Bedrijfsruimte / logistiek": (0.050, 0.070),
    "Overig": (0.070, 0.090),
}


def nar_range(property_type: str) -> tuple[float, float]:
    try:
        return NAR_RANGES[property_type]
    except KeyError as error:
        raise ValueError("Onbekend type vastgoed.") from error


def calculate_valuation(
    *,
    area_m2: float,
    rent_per_m2: float,
    vacancy_rate: float,
    operating_cost_rate: float,
    yield_rate: float,
    purchase_costs: float,
    renovation_costs: float,
    financing_rate: float,
    loan_to_value: float,
    yield_rate_range: tuple[float, float] | None = None,
    transfer_tax_rate: float = 0.104,
    purchase_price: float = 0.0,
    annual_operating_costs: float | None = None,
    loan_fee_rate: float = 0.0,
    repayment_type: str = "interest_only",
    loan_term_years: int = 20,
) -> dict[str, float]:
    if yield_rate_range is not None and len(yield_rate_range) != 2:
        raise ValueError("De rendementseisrange moet uit twee waarden bestaan.")
    yield_rate_min, yield_rate_max = yield_rate_range or (yield_rate, yield_rate)
    numeric_inputs = [
        area_m2, rent_per_m2, vacancy_rate, operating_cost_rate, yield_rate,
        yield_rate_min, yield_rate_max, purchase_costs, renovation_costs,
        financing_rate, loan_to_value, transfer_tax_rate, purchase_price,
        loan_fee_rate, loan_term_years,
    ]
    if annual_operating_costs is not None:
        numeric_inputs.append(annual_operating_costs)
    if not all(isfinite(value) for value in numeric_inputs):
        raise ValueError("Alle invoer moet een eindig getal zijn.")
    if (
        area_m2 <= 0
        or rent_per_m2 < 0
        or yield_rate_min <= 0
        or yield_rate_max < yield_rate_min
        or not yield_rate_min <= yield_rate <= yield_rate_max
    ):
        raise ValueError("Controleer oppervlak, huur en de rendementseisrange.")
    if not 0 <= vacancy_rate <= 1:
        raise ValueError("Leegstand en oninbaar moeten tussen 0% en 100% liggen.")
    if not 0 <= operating_cost_rate <= 1:
        raise ValueError("Exploitatiekosten moeten tussen 0% en 100% liggen.")
    if not 0 <= transfer_tax_rate <= 1 or purchase_price < 0:
        raise ValueError("Controleer het belastingtarief en de koopprijs.")
    if purchase_costs < 0 or renovation_costs < 0 or financing_rate < 0:
        raise ValueError("Kosten en financieringsrente mogen niet negatief zijn.")
    if not 0 <= loan_to_value <= 1:
        raise ValueError("Controleer de loan-to-value.")
    if annual_operating_costs is not None and annual_operating_costs < 0:
        raise ValueError("Exploitatiekosten mogen niet negatief zijn.")
    if not 0 <= loan_fee_rate <= 1 or loan_term_years < 1:
        raise ValueError("Controleer de financieringskosten en looptijd.")
    if repayment_type not in {"interest_only", "annuity"}:
        raise ValueError("Kies aflossingsvrij of annuïtair.")

    gross_rent = area_m2 * rent_per_m2
    effective_rent = gross_rent * (1 - vacancy_rate)
    annual_operating_costs = (
        effective_rent * operating_cost_rate
        if annual_operating_costs is None
        else annual_operating_costs
    )
    noi = effective_rent - annual_operating_costs

    def price_excluding_buyer_costs(rent: float, nar: float) -> float:
        # NAR = NOI / (prijs + kosten koper); kosten koper = overige aankoopkosten + overdrachtsbelasting over de prijs.
        return max((rent / nar - purchase_costs) / (1 + transfer_tax_rate), 0.0)

    value = price_excluding_buyer_costs(noi, yield_rate)
    value_range_low = price_excluding_buyer_costs(noi, yield_rate_max)
    value_range_high = price_excluding_buyer_costs(noi, yield_rate_min)
    transfer_tax_base = max(value, purchase_price)
    transfer_tax = transfer_tax_base * transfer_tax_rate
    acquisition_price = purchase_price if purchase_price > 0 else value
    financing_basis = min(value, acquisition_price)
    loan_amount = financing_basis * loan_to_value
    financing_fees = loan_amount * loan_fee_rate
    total_cost = acquisition_price + purchase_costs + renovation_costs + transfer_tax + financing_fees
    interest_cost = loan_amount * financing_rate
    if repayment_type == "annuity" and loan_amount > 0:
        annual_debt_service = (
            loan_amount / loan_term_years
            if financing_rate == 0
            else loan_amount * financing_rate / (1 - (1 + financing_rate) ** -loan_term_years)
        )
    else:
        annual_debt_service = interest_cost
    principal_repayment = max(annual_debt_service - interest_cost, 0.0)
    yield_on_total_cost = noi / total_cost if total_cost > 0 else 0.0
    equity_required = total_cost - loan_amount
    cash_flow_after_debt_service = noi - annual_debt_service

    return {
        "gross_rent": gross_rent,
        "effective_rent": effective_rent,
        "annual_operating_costs": annual_operating_costs,
        "noi": noi,
        "value": value,
        "value_range_low": value_range_low,
        "value_range_high": value_range_high,
        "transfer_tax_base": transfer_tax_base,
        "transfer_tax": transfer_tax,
        "yield_on_total_cost": yield_on_total_cost,
        "acquisition_price": acquisition_price,
        "financing_basis": financing_basis,
        "financing_fees": financing_fees,
        "total_cost": total_cost,
        "loan_amount": loan_amount,
        "equity_required": equity_required,
        "interest_cost": interest_cost,
        "annual_debt_service": annual_debt_service,
        "principal_repayment": principal_repayment,
        "cash_flow_after_debt_service": cash_flow_after_debt_service,
    }