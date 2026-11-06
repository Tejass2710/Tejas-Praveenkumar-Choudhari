import json
import time

try:
    from google import genai
except ImportError:
    genai = None

try:
    from project_a.models import SalaryProfile, ComparisonResult
except ImportError:
    from models import SalaryProfile, ComparisonResult

QUERY_TIME_TAX_PROMPT = """
You are an Income Tax Act calculation engine for India for FY 2024-25.
Given this profile:
{profile_json}

Compute the Old Regime and New Regime tax down to the exact rupee using:
- Standard Deduction: ₹50,000 (Old), ₹75,000 (New)
- Old Slabs: 0-2.5L: Nil; 2.5L-5L: 5%; 5L-10L: 20%; >10L: 30%
- New Slabs: 0-3L: Nil; 3L-7L: 5%; 7L-10L: 10%; 10L-12L: 15%; 12L-15L: 20%; >15L: 30%
- Section 87A Rebate:
  - Old: Full rebate if taxable <= 5L (max 12,500)
  - New: Full rebate if taxable <= 7L (max 25,000)
- Section 80C limit: 1.5L; 80CCD(1B): 50k; 24(b): 2L.
- Health & Education Cess: 4% on (tax + surcharge).
- Section 288B: Round final tax to nearest rupee.

Output strictly valid JSON conforming to:
{{
  "old_final_tax": float,
  "new_final_tax": float,
  "recommended_regime": "Old Regime" | "New Regime" | "Either",
  "explanation": "string"
}}
"""

ACTIVE_MODELS = [
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite'
]

class LLMQueryEngine:
    def __init__(self, client=None):
        self.client = client

    def compute(self, profile: SalaryProfile) -> dict:
        if not self.client:
            return {"error": "Gemini client not initialized"}
        
        prompt = QUERY_TIME_TAX_PROMPT.format(profile_json=profile.model_dump_json(indent=2))
        
        last_err = None
        for model_name in ACTIVE_MODELS:
            for attempt in range(3):
                try:
                    res = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={'response_mime_type': 'application/json', 'temperature': 0.0}
                    )
                    return json.loads(res.text)
                except Exception as e:
                    last_err = e
                    err_str = str(e).lower()
                    if "503" in err_str or "429" in err_str or "unavailable" in err_str:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    break
        raise last_err