import math
from typing import Tuple, List

try:
    from project_a.config import TaxConfig, CONFIG_FY24_25
    from project_a.models import SalaryProfile, TaxBreakdown, ComparisonResult
except ImportError:
    from config import TaxConfig, CONFIG_FY24_25
    from models import SalaryProfile, TaxBreakdown, ComparisonResult
    
class DeterministicTaxEngine:
    def __init__(self, config: TaxConfig = CONFIG_FY24_25):
        self.cfg = config

    def calculate_hra_exemption(self, p: SalaryProfile) -> float:
        if p.hra_received <= 0 or p.rent_paid <= 0:
            return 0.0
        salary_for_hra = p.basic_salary + p.da
        if salary_for_hra <= 0:
            salary_for_hra = p.gross_salary * 0.50 # Fallback proxy if unsegregated

        c1 = p.hra_received
        c2 = max(0.0, p.rent_paid - (0.10 * salary_for_hra))
        c3 = (0.50 if p.is_metro else 0.40) * salary_for_hra
        return min(c1, c2, c3)

    def calculate_deductions_old(self, p: SalaryProfile) -> Tuple[float, List[str]]:
        traces = []
        deductions = 0.0
        
        # Standard deduction
        sd = min(p.gross_salary, self.cfg.standard_deduction_old)
        deductions += sd
        traces.append(f"Sec 16(ia): Standard deduction of ₹{sd:,.0f}")

        # HRA Exemption
        hra = self.calculate_hra_exemption(p)
        if hra > 0:
            deductions += hra
            traces.append(f"Sec 10(13A): HRA exemption of ₹{hra:,.0f}")

        # 80C (Max 1.5L)
        c_val = min(150000.0, p.sec_80c)
        if c_val > 0:
            deductions += c_val
            traces.append(f"Sec 80C: Deductions capped at ₹{c_val:,.0f}")

        # 80CCD(1B) (Max 50k)
        nps = min(50000.0, p.sec_80ccd_1b)
        if nps > 0:
            deductions += nps
            traces.append(f"Sec 80CCD(1B): NPS contribution ₹{nps:,.0f}")

        # 80D
        limit_self = 50000.0 if False else 25000.0 # Assuming user is non-senior
        limit_parents = 50000.0 if p.parents_senior else 25000.0
        d_self = min(limit_self, p.sec_80d_self)
        d_parents = min(limit_parents, p.sec_80d_parents)
        d_total = d_self + d_parents
        if d_total > 0:
            deductions += d_total
            traces.append(f"Sec 80D: Medical insurance ₹{d_total:,.0f} (Parents cap: {limit_parents})")

        # Sec 24(b)
        hl = min(200000.0, p.home_loan_interest_self_occupied)
        if hl > 0:
            deductions += hl
            traces.append(f"Sec 24(b): Self-occupied home loan interest ₹{hl:,.0f}")

        return deductions, traces

    def _compute_slab_tax(self, taxable: float, slabs: List[Tuple[float, float, float]]) -> float:
        tax = 0.0
        for lower, upper, rate in slabs:
            if taxable > lower:
                taxable_in_slab = min(taxable, upper) - lower
                tax += taxable_in_slab * rate
            else:
                break
        return tax

    def _compute_surcharge_with_marginal_relief(self, taxable: float, slab_tax: float, is_new_regime: bool) -> Tuple[float, float]:
        # Surcharge slabs for individuals
        surcharge_rate = 0.0
        threshold = 0.0
        if taxable > 50000000:
            surcharge_rate = 0.25 if is_new_regime else 0.37
            threshold = 50000000
        elif taxable > 20000000:
            surcharge_rate = 0.25
            threshold = 20000000
        elif taxable > 10000000:
            surcharge_rate = 0.15
            threshold = 10000000
        elif taxable > 5000000:
            surcharge_rate = 0.10
            threshold = 5000000
        else:
            return 0.0, 0.0

        raw_surcharge = slab_tax * surcharge_rate
        total_tax_with_surcharge = slab_tax + raw_surcharge

        # Marginal relief calculation
        tax_at_threshold = self._compute_slab_tax(
            threshold, self.cfg.new_slabs if is_new_regime else self.cfg.old_slabs
        )
        # Add previous tier surcharge on threshold if applicable
        prev_surch_rate = 0.0
        if threshold == 10000000: prev_surch_rate = 0.10
        elif threshold == 20000000: prev_surch_rate = 0.15
        elif threshold == 50000000: prev_surch_rate = 0.25
        tax_at_threshold += (tax_at_threshold * prev_surch_rate)

        excess_income = taxable - threshold
        max_allowable_tax = tax_at_threshold + excess_income

        marginal_relief = 0.0
        if total_tax_with_surcharge > max_allowable_tax:
            marginal_relief = total_tax_with_surcharge - max_allowable_tax
            raw_surcharge -= marginal_relief

        return raw_surcharge, marginal_relief

    def calculate_old_regime(self, p: SalaryProfile) -> TaxBreakdown:
        traces = []
        deductions, d_traces = self.calculate_deductions_old(p)
        traces.extend(d_traces)

        taxable = max(0.0, p.gross_salary - deductions)
        # Section 288A rounding to nearest 10
        taxable = round(taxable / 10.0) * 10.0

        slab_tax = self._compute_slab_tax(taxable, self.cfg.old_slabs)
        traces.append(f"Old Slab computation: ₹{slab_tax:,.2f}")

        # Sec 87A Rebate
        rebate = 0.0
        if taxable <= self.cfg.sec_87a_rebate_limit_old:
            rebate = min(slab_tax, 12500.0)
            traces.append(f"Sec 87A: Full rebate of ₹{rebate:,.2f}")

        tax_after_rebate = slab_tax - rebate
        surcharge, marginal_relief = 0.0, 0.0
        if taxable > 5000000:
            surcharge, marginal_relief = self._compute_surcharge_with_marginal_relief(taxable, slab_tax, False)
            traces.append(f"Surcharge: ₹{surcharge:,.2f} (Relief: ₹{marginal_relief:,.2f})")

        cess = (tax_after_rebate + surcharge) * self.cfg.cess_rate
        traces.append(f"Sec 2(14) Finance Act: 4% Health & Education Cess: ₹{cess:,.2f}")

        final_tax = round(tax_after_rebate + surcharge + cess)
        return TaxBreakdown(
            gross_total_income=p.gross_salary,
            total_deductions=deductions,
            taxable_income=taxable,
            slab_tax=slab_tax,
            sec_87a_rebate=rebate,
            tax_after_rebate=tax_after_rebate,
            surcharge=surcharge,
            marginal_relief=marginal_relief,
            cess=cess,
            final_tax=final_tax,
            clause_trace=traces
        )

    def calculate_new_regime(self, p: SalaryProfile) -> TaxBreakdown:
        traces = []
        sd = min(p.gross_salary, self.cfg.standard_deduction_new)
        traces.append(f"Sec 16(ia): Standard deduction under 115BAC: ₹{sd:,.0f}")
        
        taxable = max(0.0, p.gross_salary - sd)
        taxable = round(taxable / 10.0) * 10.0

        slab_tax = self._compute_slab_tax(taxable, self.cfg.new_slabs)
        traces.append(f"Sec 115BAC Slabs: ₹{slab_tax:,.2f}")

        # Section 87A Rebate (Marginal rebate logic for new regime)
        rebate = 0.0
        if taxable <= self.cfg.sec_87a_rebate_limit_new:
            rebate = slab_tax
            traces.append(f"Sec 87A: Full rebate of ₹{rebate:,.2f}")
        else:
            # Marginal relief under 87A for slightly exceeding threshold
            excess_income = taxable - self.cfg.sec_87a_rebate_limit_new
            if slab_tax > excess_income and excess_income < slab_tax:
                rebate = slab_tax - excess_income
                traces.append(f"Sec 87A Marginal Rebate: ₹{rebate:,.2f}")

        tax_after_rebate = max(0.0, slab_tax - rebate)
        surcharge, marginal_relief = 0.0, 0.0
        if taxable > 5000000:
            surcharge, marginal_relief = self._compute_surcharge_with_marginal_relief(taxable, slab_tax, True)
            traces.append(f"Surcharge: ₹{surcharge:,.2f} (Relief: ₹{marginal_relief:,.2f})")

        cess = (tax_after_rebate + surcharge) * self.cfg.cess_rate
        traces.append(f"4% Health & Education Cess: ₹{cess:,.2f}")

        final_tax = round(tax_after_rebate + surcharge + cess)
        return TaxBreakdown(
            gross_total_income=p.gross_salary,
            total_deductions=sd,
            taxable_income=taxable,
            slab_tax=slab_tax,
            sec_87a_rebate=rebate,
            tax_after_rebate=tax_after_rebate,
            surcharge=surcharge,
            marginal_relief=marginal_relief,
            cess=cess,
            final_tax=final_tax,
            clause_trace=traces
        )

    def evaluate(self, p: SalaryProfile) -> ComparisonResult:
        old_res = self.calculate_old_regime(p)
        new_res = self.calculate_new_regime(p)

        if old_res.final_tax < new_res.final_tax:
            rec = "Old Regime"
            diff = new_res.final_tax - old_res.final_tax
            expl = f"Old regime saves ₹{diff:,.0f} due to high deductions (₹{old_res.total_deductions:,.0f})."
        elif new_res.final_tax < old_res.final_tax:
            rec = "New Regime"
            diff = old_res.final_tax - new_res.final_tax
            expl = f"New regime saves ₹{diff:,.0f} due to lower slab rates & higher standard deduction/rebate."
        else:
            rec = "Either"
            diff = 0.0
            expl = "Both regimes yield identical tax liability."

        return ComparisonResult(
            old_regime=old_res,
            new_regime=new_res,
            recommended_regime=rec,
            tax_difference=diff,
            explanation=expl
        )