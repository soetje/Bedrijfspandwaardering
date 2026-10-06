import re
import unittest

from reporting import report_pdf
from valuation import calculate_valuation


class ReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inputs = {
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
            "transfer_tax_rate": 0.104,
            "purchase_price": 0,
            "value_growth_rate": 0.02,
            "annual_operating_costs": None,
            "loan_fee_rate": 0.01,
            "repayment_type": "annuity",
            "loan_term_years": 20,
            "detailed_operating_costs": False,
            "operating_cost_items": {},
            "repayment_type_label": "Annuïtair",
            "loan_term_label": "20 jaar",
        }
        self.result = calculate_valuation(
            **{key: value for key, value in self.inputs.items() if key in {
                "area_m2", "rent_per_m2", "vacancy_rate", "operating_cost_rate",
                "yield_rate", "yield_rate_range", "purchase_costs", "renovation_costs",
                "financing_rate", "loan_to_value", "transfer_tax_rate", "purchase_price",
                "value_growth_rate", "annual_operating_costs", "loan_fee_rate",
                "repayment_type", "loan_term_years",
            }}
        )

    def create_pdf(self) -> bytes:
        return report_pdf("Testpand", "06-10-2026", self.inputs, self.result)

    def test_standard_report_is_valid_single_page_pdf(self) -> None:
        pdf = self.create_pdf()

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 1)

    def test_itemized_cost_report_is_valid_pdf(self) -> None:
        self.inputs["detailed_operating_costs"] = True
        self.inputs["operating_cost_items"] = {
            "Onderhoud": 5000,
            "Verzekering": 1000,
            "OZB en eigenaarslasten": 2500,
            "Beheer": 1500,
            "Overig": 1000,
        }

        pdf = self.create_pdf()

        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertLessEqual(len(re.findall(rb"/Type\s*/Page\b", pdf)), 2)


if __name__ == "__main__":
    unittest.main()