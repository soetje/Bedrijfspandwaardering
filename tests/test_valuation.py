import math
import unittest

from valuation import NAR_RANGES, calculate_valuation, nar_range


BASE_INPUTS = {
    "area_m2": 800,
    "rent_per_m2": 85,
    "vacancy_rate": 0.05,
    "operating_cost_rate": 0.15,
    "yield_rate": 0.08,
    "yield_rate_range": (0.07, 0.09),
    "purchase_costs": 25000,
    "renovation_costs": 50000,
    "financing_rate": 0.05,
    "loan_to_value": 0.65,
    "loan_fee_rate": 0.01,
    "repayment_type": "annuity",
    "loan_term_years": 20,
}


def calculate(**overrides: float | tuple[float, float] | str) -> dict[str, float]:
    inputs = {**BASE_INPUTS, **overrides}
    return calculate_valuation(**inputs)


def central_price(noi: float = 54910, nar: float = 0.08, purchase_costs: float = 25000, tax_rate: float = 0.104) -> float:
    return (noi / nar - purchase_costs) / (1 + tax_rate)


class ValuationTests(unittest.TestCase):
    def test_rent_noi_and_value_range(self) -> None:
        result = calculate()

        self.assertEqual(result["gross_rent"], 68000)
        self.assertEqual(result["effective_rent"], 64600)
        self.assertEqual(result["annual_operating_costs"], 9690)
        self.assertEqual(result["noi"], 54910)
        self.assertAlmostEqual(result["value"], central_price())
        self.assertAlmostEqual(result["value_range_low"], central_price(nar=0.09))
        self.assertAlmostEqual(result["value_range_high"], central_price(nar=0.07))

    def test_nar_equals_noi_over_price_plus_buyer_costs(self) -> None:
        result = calculate(purchase_price=0)

        buyer_costs = 25000 + result["transfer_tax"]
        self.assertAlmostEqual(result["noi"] / (result["value"] + buyer_costs), 0.08)

    def test_buyer_costs_larger_than_capitalised_rent_give_zero_value(self) -> None:
        result = calculate(purchase_costs=10_000_000)

        self.assertEqual(result["value"], 0)
        self.assertEqual(result["value_range_low"], 0)
        self.assertEqual(result["value_range_high"], 0)

    def test_acquisition_price_and_tax_basis(self) -> None:
        no_purchase = calculate(purchase_price=0)
        lower_purchase = calculate(purchase_price=550000)
        higher_purchase = calculate(purchase_price=800000)

        self.assertAlmostEqual(no_purchase["acquisition_price"], central_price())
        self.assertEqual(lower_purchase["acquisition_price"], 550000)
        self.assertEqual(lower_purchase["financing_basis"], 550000)
        self.assertEqual(higher_purchase["transfer_tax_base"], 800000)

    def test_annuity_cash_flow(self) -> None:
        result = calculate()

        loan = central_price() * 0.65
        payment = loan * 0.05 / (1 - 1.05 ** -20)
        self.assertAlmostEqual(result["loan_amount"], loan)
        self.assertAlmostEqual(result["annual_debt_service"], payment)
        self.assertAlmostEqual(result["cash_flow_after_debt_service"], 54910 - payment)
        self.assertNotIn("cash_on_cash_return", result)

    def test_interest_only_and_zero_interest_annuity(self) -> None:
        interest_only = calculate(repayment_type="interest_only")
        zero_rate = calculate(financing_rate=0)

        self.assertEqual(interest_only["annual_debt_service"], interest_only["interest_cost"])
        self.assertEqual(interest_only["principal_repayment"], 0)
        self.assertAlmostEqual(zero_rate["annual_debt_service"], zero_rate["loan_amount"] / 20)

    def test_itemized_costs_replace_percentage_costs(self) -> None:
        result = calculate(annual_operating_costs=10000)

        self.assertEqual(result["annual_operating_costs"], 10000)
        self.assertEqual(result["noi"], 54600)

    def test_zero_ltv_has_no_debt_or_debt_service(self) -> None:
        result = calculate(loan_to_value=0)

        self.assertEqual(result["loan_amount"], 0)
        self.assertEqual(result["annual_debt_service"], 0)
        self.assertEqual(result["cash_flow_after_debt_service"], result["noi"])

    def test_every_property_type_has_a_valid_nar_range(self) -> None:
        for property_type, (low, high) in NAR_RANGES.items():
            with self.subTest(property_type=property_type):
                self.assertEqual(nar_range(property_type), (low, high))
                self.assertTrue(0 < low < high < 0.2)
        with self.assertRaises(ValueError):
            nar_range("Onbekend")

    def test_value_has_no_growth_component(self) -> None:
        result = calculate()

        for key in ("value_growth_basis", "annual_value_growth", "yield_including_value_growth"):
            self.assertNotIn(key, result)

    def test_invalid_inputs_are_rejected(self) -> None:
        invalid_cases = [
            {"rent_per_m2": -1},
            {"purchase_costs": -1},
            {"renovation_costs": -1},
            {"financing_rate": -0.01},
            {"rent_per_m2": math.inf},
            {"yield_rate_range": (0.09, 0.07)},
            {"yield_rate_range": (0.07,)},
            {"yield_rate": 0.1},
        ]
        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    calculate(**overrides)


if __name__ == "__main__":
    unittest.main()