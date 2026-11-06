from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class SalaryProfile(BaseModel):
    gross_salary: float = Field(..., ge=0, description="Gross salary before any exemptions")
    basic_salary: float = Field(0.0, ge=0, description="Basic salary component")
    da: float = Field(0.0, ge=0, description="Dearness Allowance")
    hra_received: float = Field(0.0, ge=0, description="HRA component in CTC")
    rent_paid: float = Field(0.0, ge=0, description="Actual rent paid per year")
    is_metro: bool = Field(False, description="Metro city flag (Mumbai, Delhi, Kolkata, Chennai)")
    
    # Chapter VI-A Deductions
    sec_80c: float = Field(0.0, ge=0, description="PPF, EPF, ELSS, Life Insurance (Max 1.5L)")
    sec_80ccd_1b: float = Field(0.0, ge=0, description="NPS Tier-1 employee contribution (Max 50k)")
    sec_80d_self: float = Field(0.0, ge=0, description="Self/family health insurance (Max 25k/50k)")
    sec_80d_parents: float = Field(0.0, ge=0, description="Parents health insurance")
    parents_senior: bool = Field(False, description="Whether parents are aged 60+")
    
    # Section 24(b)
    home_loan_interest_self_occupied: float = Field(0.0, ge=0, description="Home loan interest (Max 2L)")

class TaxBreakdown(BaseModel):
    gross_total_income: float
    total_deductions: float
    taxable_income: float
    slab_tax: float
    sec_87a_rebate: float
    tax_after_rebate: float
    surcharge: float
    marginal_relief: float
    cess: float
    final_tax: float
    clause_trace: List[str]

class ComparisonResult(BaseModel):
    old_regime: TaxBreakdown
    new_regime: TaxBreakdown
    recommended_regime: str
    tax_difference: float
    explanation: str