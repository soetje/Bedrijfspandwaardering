import math
import unittest

from valuation import calculate_valuation


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


class ValuationTests(unittest.TestCase):
    def test_rent_noi_and_value_range(self) -> None:
        result = calculate()

        self.assertEqual(result["gross_rent"], 68000)
        self.assertEqual(result["effective_rent"], 64600)
        self.assertEqual(result["annual_operating_costs"], 9690)
        self.assertEqual(result["noi"], 54910)
        self.assertEqual(result["value"], 686375)
        self.assertAlmostEqual(result["value_range_low"], 54910 / 0.09)
        self.assertAlmostEqual(result["value_range_high"], 54910 / 0.07)

    def test_acquisition_price_and_tax_basis(self) -> None:
        no_purchase = calculate(purchase_price=0)
        lower_purchase = calculate(purchase_price=600000)
        higher_purchase = calculate(purchase_price=800000)

        self.assertEqual(no_purchase["acquisition_price"], 686375)
        self.assertEqual(lower_purchase["acquisition_price"], 600000)
        self.assertEqual(lower_purchase["financing_basis"], 600000)
        self.assertEqual(higher_purchase["transfer_tax_base"], 800000)
        self.assertEqual(higher_purchase["value_growth_basis"], 800000)

    def test_annuity_cash_flow_and_cash_on_cash_return(self) -> None:
        result = calculate()

        self.assertAlmostEqual(result["annual_debt_service"], 35799.728758957)
        self.assertAlmostEqual(result["cash_flow_after_debt_service"], 19110.271241043)
        self.assertAlmostEqual(
            result["cash_on_cash_return"],
            result["cash_flow_after_debt_service"] / result["equity_required"],
        )
        self.assertNotEqual(result["cash_on_cash_return"], result["yield_on_total_cost"])

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