try:
    from project_a.config import TaxConfig, CONFIG_FY24_25
    from project_a.models import SalaryProfile, TaxBreakdown, ComparisonResult
    from project_a.rules_engine import DeterministicTaxEngine
except ImportError:
    from config import TaxConfig, CONFIG_FY24_25
    from models import SalaryProfile, TaxBreakdown, ComparisonResult
    from rules_engine import DeterministicTaxEngine

class LLMCompiledRulesEngine:
    def __init__(self, config: TaxConfig = CONFIG_FY24_25):
        self.engine = DeterministicTaxEngine(config)

    def execute(self, profile: SalaryProfile) -> ComparisonResult:
        return self.engine.evaluate(profile)