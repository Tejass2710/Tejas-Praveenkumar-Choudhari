import os
import sys
from pathlib import Path

# Force load .env from the current working file's directory
try:
    from dotenv import load_dotenv
    env_file = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_file)
except ImportError:
    pass

from google import genai
from project_a.parser import PlainLanguageParser
from project_a.test_generator import PLAIN_LANGUAGE_QUERIES

def test_nlp_parsing():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not configured. Aborting execution.")
        return

    client = genai.Client(api_key=api_key)
    parser = PlainLanguageParser(client)

    print("==================================================")
    print("      EVALUATING TASK 3: NATURAL LANGUAGE PARSER  ")
    print("==================================================\n")

    for idx, query in enumerate(PLAIN_LANGUAGE_QUERIES, start=1):
        print(f"[{idx}] Input: \"{query}\"")
        try:
            result = parser.parse(query)
            if result.is_ambiguous:
                print(f"    Status: Ambiguity Detected -> Clarification: {result.clarification_question}\n")
            else:
                p = result.data
                print(f"    Status: Successfully Structured -> Gross: ₹{p.gross_salary:,.0f} | 80C: ₹{p.sec_80c:,.0f}\n")
        except Exception as err:
            print(f"    Execution Error: {err}\n")

if __name__ == "__main__":
    test_nlp_parsing()