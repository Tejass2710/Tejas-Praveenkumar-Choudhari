from dataclasses import dataclass
from typing import List, Tuple

@dataclass(frozen=True)
class TaxConfig:
    fy: str
    standard_deduction_old: float
    standard_deduction_new: float
    sec_87a_rebate_limit_old: float
    sec_87a_rebate_limit_new: float
    old_slabs: List[Tuple[float, float, float]]
    new_slabs: List[Tuple[float, float, float]]
    cess_rate: float = 0.04

# FY 2024-25 (Finance Act 2024)
CONFIG_FY24_25 = TaxConfig(
    fy="2024-25",
    standard_deduction_old=50000.0,
    standard_deduction_new=75000.0,  # Budget 2024 increased new regime SD to 75k
    sec_87a_rebate_limit_old=500000.0,
    sec_87a_rebate_limit_new=700000.0,  # Full rebate up to 7 Lakhs (taxable)
    old_slabs=[
        (0.0, 250000.0, 0.0),
        (250000.0, 500000.0, 0.05),
        (500000.0, 1000000.0, 0.20),
        (1000000.0, float("inf"), 0.30),
    ],
    new_slabs=[
        (0.0, 300000.0, 0.0),
        (300000.0, 700000.0, 0.05),
        (700000.0, 1000000.0, 0.10),
        (1000000.0, 1200000.0, 0.15),
        (1200000.0, 1500000.0, 0.20),
        (1500000.0, float("inf"), 0.30),
    ]
)

# FY 2025-26 (Finance Act 2025)
CONFIG_FY25_26 = TaxConfig(
    fy="2025-26",
    standard_deduction_old=50000.0,
    standard_deduction_new=75000.0,
    sec_87a_rebate_limit_old=500000.0,
    sec_87a_rebate_limit_new=1200000.0, # Budget 2025 revised slab rebate
    old_slabs=[
        (0.0, 250000.0, 0.0),
        (250000.0, 500000.0, 0.05),
        (500000.0, 1000000.0, 0.20),
        (1000000.0, float("inf"), 0.30),
    ],
    new_slabs=[
        (0.0, 400000.0, 0.0),
        (400000.0, 800000.0, 0.05),
        (800000.0, 1200000.0, 0.10),
        (1200000.0, 1600000.0, 0.15),
        (1600000.0, 2000000.0, 0.20),
        (2000000.0, 2400000.0, 0.25),
        (2400000.0, float("inf"), 0.30),
    ]
)