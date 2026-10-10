import unittest

from reporting import price_range, spread_positions


def build(**overrides):
    values = {
        "low": 610_000,
        "central": 686_000,
        "high": 784_000,
        "purchase_price": 650_000,
        "total_cost": 837_000,
    }
    return price_range(**{**values, **overrides})


class PriceRangeTests(unittest.TestCase):
    def test_all_markers_are_inside_the_scale(self) -> None:
        info = build()

        positions = [info["low_position"], info["high_position"], *(m["position"] for m in info["markers"])]
        self.assertTrue(all(0 < position < 1 for position in positions))
        self.assertLess(info["low_position"], info["high_position"])

    def test_without_purchase_price_the_marker_is_omitted(self) -> None:
        info = build(purchase_price=0)

        self.assertEqual([m["key"] for m in info["markers"]], ["central", "total"])
        self.assertIn("Geen koopprijs", info["verdict"])

    def test_total_cost_can_sit_above_the_band(self) -> None:
        info = build()
        total = next(m for m in info["markers"] if m["key"] == "total")

        self.assertGreater(total["position"], info["high_position"])

    def test_verdict_for_purchase_price_position(self) -> None:
        self.assertIn("onder", build(purchase_price=500_000)["verdict"])
        self.assertIn("binnen", build(purchase_price=700_000)["verdict"])
        self.assertIn("boven", build(purchase_price=900_000)["verdict"])

    def test_zero_value_does_not_divide_by_zero(self) -> None:
        info = build(low=0, central=0, high=0, purchase_price=0, total_cost=0)

        self.assertEqual([m["key"] for m in info["markers"]], ["central"])

    def test_spread_keeps_order_and_minimum_gap(self) -> None:
        spread = spread_positions([100, 102, 104], 20, 0, 200)

        self.assertEqual(spread, sorted(spread))
        self.assertTrue(all(b - a >= 20 - 1e-9 for a, b in zip(spread, spread[1:])))
        self.assertTrue(all(0 <= value <= 200 for value in spread))

    def test_spread_respects_the_upper_bound(self) -> None:
        spread = spread_positions([190, 195, 200], 20, 0, 200)

        self.assertLessEqual(max(spread), 200)
        self.assertTrue(all(b - a >= 20 - 1e-9 for a, b in zip(spread, spread[1:])))


if __name__ == "__main__":
    unittest.main()
