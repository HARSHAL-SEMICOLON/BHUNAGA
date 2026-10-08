"""
Work out the cost and profit for a crop.

This is all simple maths and needs no internet. The numbers shown by default are
just examples for Maharashtra; the farmer can change every one of them to match
their own field.
"""

from __future__ import annotations

from dataclasses import dataclass

# Illustrative per-acre defaults: cost components (INR), expected yield, price.
# yield_unit is the unit for both expected_yield and price_per_unit.
CROP_DEFAULTS = {
    "Cotton":    {"seed": 2500, "fertilizer": 6000, "pesticide": 5000,
                  "labour": 12000, "irrigation": 3000, "other": 3000,
                  "yield": 8.0,  "yield_unit": "quintal", "price": 7000},
    "Sugarcane": {"seed": 8000, "fertilizer": 12000, "pesticide": 3000,
                  "labour": 18000, "irrigation": 9000, "other": 5000,
                  "yield": 400.0, "yield_unit": "quintal", "price": 300},
    "Soybean":   {"seed": 3000, "fertilizer": 4000, "pesticide": 2500,
                  "labour": 6000, "irrigation": 1500, "other": 2000,
                  "yield": 10.0, "yield_unit": "quintal", "price": 4500},
    "Onion":     {"seed": 4000, "fertilizer": 7000, "pesticide": 4000,
                  "labour": 15000, "irrigation": 5000, "other": 4000,
                  "yield": 100.0, "yield_unit": "quintal", "price": 1500},
    "Grapes":    {"seed": 20000, "fertilizer": 25000, "pesticide": 30000,
                  "labour": 45000, "irrigation": 15000, "other": 15000,
                  "yield": 100.0, "yield_unit": "quintal", "price": 5000},
    "Wheat":     {"seed": 2000, "fertilizer": 4000, "pesticide": 1500,
                  "labour": 5000, "irrigation": 3000, "other": 2000,
                  "yield": 16.0, "yield_unit": "quintal", "price": 2300},
}

COST_KEYS = ["seed", "fertilizer", "pesticide", "labour", "irrigation", "other"]


@dataclass
class CostResult:
    total_cost: float
    revenue: float
    profit: float
    yield_total: float
    yield_unit: str
    cost_per_unit: float
    breakdown: dict


def compute(costs: dict, expected_yield: float, price_per_unit: float,
            acres: float = 1.0, yield_unit: str = "quintal") -> CostResult:
    """costs = per-acre amounts; expected_yield/price are per-acre + per-unit."""
    acres = max(acres, 0.0)
    per_acre_cost = sum(float(costs.get(k, 0)) for k in COST_KEYS)
    total_cost = per_acre_cost * acres
    yield_total = float(expected_yield) * acres
    revenue = yield_total * float(price_per_unit)
    profit = revenue - total_cost
    cost_per_unit = (total_cost / yield_total) if yield_total else 0.0
    return CostResult(
        total_cost=total_cost, revenue=revenue, profit=profit,
        yield_total=yield_total, yield_unit=yield_unit,
        cost_per_unit=cost_per_unit,
        breakdown={k: float(costs.get(k, 0)) * acres for k in COST_KEYS},
    )
