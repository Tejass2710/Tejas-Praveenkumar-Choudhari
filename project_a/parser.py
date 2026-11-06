import json
import logging
import time
from typing import Union
from pydantic import BaseModel, ValidationError

try:
    from google import genai
except ImportError:
    genai = None

try:
    from project_a.models import SalaryProfile
except ImportError:
    from models import SalaryProfile

logger = logging.getLogger(__name__)

class ParseResponse(BaseModel):
    is_ambiguous: bool
    data: Union[SalaryProfile, None] = None
    clarification_question: Union[str, None] = None

PARSER_SYSTEM_PROMPT = """
You are an expert Indian Income Tax Parser. Your task is to extract income details for salaried tax computation for FY 2024-25.
Convert the user's natural language (which may be English, Hindi, or Hinglish) into a structured JSON.

CRITICAL RULES:
1. NEVER guess or hallucinate numbers. If an ambiguous statement like "I pay rent" is given without an amount, flag it.
2. If rent is given but city type (metro vs non-metro) is not discernable, ask for clarification if rent is substantial (> ₹1,00,000/yr).
3. If gross salary is missing, you CANNOT compute tax. You must return a clarifying question.
4. If health insurance for parents is declared but their age/senior citizen status is unknown, ask.
5. All amounts must be annualized in INR. If monthly figures are quoted (e.g. "per month", "p.m."), multiply by 12.

Return JSON strictly adhering to this schema:
{
  "is_ambiguous": boolean,
  "clarification_question": string or null,
  "extracted_data": {
     "gross_salary": float,
     "basic_salary": float,
     "da": float,
     "hra_received": float,
     "rent_paid": float,
     "is_metro": boolean,
     "sec_80c": float,
     "sec_80ccd_1b": float,
     "sec_80d_self": float,
     "sec_80d_parents": float,
     "parents_senior": boolean,
     "home_loan_interest_self_occupied": float
  }
}
"""

ACTIVE_MODELS = [
    'gemini-3.5-flash',
    'gemini-3.5-flash-lite'
]

class PlainLanguageParser:
    def __init__(self, client=None):
        self.client = client

    def _generate(self, prompt: str):
        last_err = None
        for model_name in ACTIVE_MODELS:
            for attempt in range(3):
                try:
                    res = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config={'response_mime_type': 'application/json'}
                    )
                    return res
                except Exception as e:
                    last_err = e
                    err_str = str(e).lower()
                    if "503" in err_str or "429" in err_str or "unavailable" in err_str:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                    break
        raise last_err

    def parse(self, user_query: str) -> ParseResponse:
        if not self.client:
            raise RuntimeError("API client not initialized.")

        full_prompt = f"{PARSER_SYSTEM_PROMPT}\n\nUser Input: \"{user_query}\""
        response = self._generate(full_prompt)
        
        try:
            raw_json = json.loads(response.text)
        except Exception as e:
            logger.error("Failed to parse JSON response: %s", e)
            return ParseResponse(
                is_ambiguous=True,
                clarification_question="Unable to parse financial inputs. Please specify salary and deductions."
            )

        if raw_json.get("is_ambiguous"):
            return ParseResponse(
                is_ambiguous=True,
                clarification_question=raw_json.get("clarification_question")
            )

        try:
            profile = SalaryProfile(**raw_json.get("extracted_data", {}))
            return ParseResponse(is_ambiguous=False, data=profile)
        except (ValidationError, TypeError):
            return ParseResponse(
                is_ambiguous=True,
                clarification_question="Could not validate financial data. Please clarify salary amounts."
            )