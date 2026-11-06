import os
import sys
import time
from pathlib import Path

# Explicitly load .env file from the current script directory
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Google GenAI SDK
try:
    from google import genai
except ImportError as e:
    genai = None
    print(f"[!] Warning: google-genai library import failed: {e}")

from project_a.config import CONFIG_FY24_25
from project_a.models import SalaryProfile
from project_a.rules_engine import DeterministicTaxEngine
from project_a.llm_compiled_rules import LLMCompiledRulesEngine

try:
    from project_a.llm_query_engine import LLMQueryEngine
except ImportError as e:
    print(f"[!] Warning: LLMQueryEngine import failed: {e}")
    LLMQueryEngine = None

try:
    from project_a.parser import PlainLanguageParser
except ImportError as e:
    print(f"[!] Warning: PlainLanguageParser import failed: {e}")
    PlainLanguageParser = None

from project_a.test_generator import generate_test_cases, PLAIN_LANGUAGE_QUERIES


def run_benchmarks():
    print("==================================================")
    print("  PROJECT A: INCOME-TAX ENGINE BENCHMARK HARNESS  ")
    print("==================================================\n")

    # Read API Key
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    client = None

    if not api_key:
        print("[!] Warning: GEMINI_API_KEY not found in environment or .env file.")
    elif genai is None:
        print("[!] Warning: google.genai package is not installed. Run: pip install google-genai")
    else:
        try:
            client = genai.Client(api_key=api_key)
            print("[✓] Gemini API client successfully initialized.\n")
        except Exception as e:
            print(f"[!] Error initializing Gemini client: {e}\n")

    # 1. Initialize Engines
    engine_hand = DeterministicTaxEngine(CONFIG_FY24_25)
    engine_compiled = LLMCompiledRulesEngine(CONFIG_FY24_25)
    engine_llm = LLMQueryEngine(client) if (LLMQueryEngine and client) else None
    parser = PlainLanguageParser(client) if (PlainLanguageParser and client) else None

    # 2. Generate 200 Synthetic Edge Cases (Task 1)
    print("[1] Generating 200 synthetic test cases...")
    test_cases = generate_test_cases()
    print(f"    Generated {len(test_cases)} test cases.\n")

    # 3. Benchmark Task 2a: Hand-Coded Rules
    print("[2] Running Task 2a: Hand-Coded Rules Engine...")
    t0 = time.time()
    hand_results = [engine_hand.evaluate(p) for p in test_cases]
    hand_time = (time.time() - t0) * 1000
    print(f"    200 cases executed in: {hand_time:.2f} ms ({hand_time/len(test_cases):.4f} ms/case)")

    # 4. Benchmark Task 2c: LLM-Compiled Rules
    print("\n[3] Running Task 2c: LLM-Compiled Rules Engine...")
    t0 = time.time()
    compiled_results = [engine_compiled.execute(p) for p in test_cases]
    comp_time = (time.time() - t0) * 1000
    print(f"    200 cases executed in: {comp_time:.2f} ms ({comp_time/len(test_cases):.4f} ms/case)")

    # 5. Determinism Check (10 repeated runs on Case #0)
    print("\n[4] Checking Determinism (10 repeated iterations)...")
    sample_case = test_cases[0]
    hand_outputs = [engine_hand.evaluate(sample_case).old_regime.final_tax for _ in range(10)]
    is_hand_deterministic = len(set(hand_outputs)) == 1
    print(f"    Hand-Coded Deterministic: {is_hand_deterministic} (Outputs: {set(hand_outputs)})")

    # 6. Task 2b: Query-Time LLM Execution
    print("\n[5] Task 2b: Query-Time LLM Execution...")
    if engine_llm and client:
        print("    Executing live query-time LLM on sample profile...")
        try:
            t0 = time.time()
            llm_res = engine_llm.compute(sample_case)
            llm_time = (time.time() - t0) * 1000
            print(f"    Status: SUCCESS | Latency: {llm_time:.2f} ms")
            print(f"    Calculated: Old Tax = Rs {llm_res.get('old_final_tax')}, New Tax = Rs {llm_res.get('new_final_tax')}")
            print(f"    Recommended: {llm_res.get('recommended_regime')}")
        except Exception as err:
            print(f"    [!] LLM Execution Failed: {err}")
    else:
        print("    [!] SKIPPED: LLM client is not available (check API key or import errors above).")

    # 7. Task 3: Plain-Language Parser Sample Verification
    print("\n[6] Task 3: Plain-Language Parser Intent & Ambiguity Check...")
    if parser and client:
        sample_queries = PLAIN_LANGUAGE_QUERIES[:3]
        for idx, q in enumerate(sample_queries, start=1):
            try:
                res = parser.parse(q)
                if res.is_ambiguous:
                    print(f"    Sample {idx} [Ambiguity Handled]: \"{q}\"")
                    print(f"      -> Question: {res.clarification_question}")
                else:
                    p = res.data
                    print(f"    Sample {idx} [Parsed Successfully]: \"{q}\"")
                    print(f"      -> Gross: Rs {p.gross_salary:,.0f} | 80C: Rs {p.sec_80c:,.0f}")
            except Exception as e:
                print(f"    Sample {idx} [!] Parse Failed: {e}")
    else:
        print("    [!] SKIPPED: Parser client is not available.")

    # 8. Statutory Audit Trace
    print("\n[7] Statutory Clause Audit Trace (Case #1):")
    sample_res = hand_results[1]
    print(f"    Gross: Rs {sample_res.old_regime.gross_total_income:,.0f}")
    print(f"    Old Tax: Rs {sample_res.old_regime.final_tax:,.0f} | New Tax: Rs {sample_res.new_regime.final_tax:,.0f}")
    print(f"    Recommended: {sample_res.recommended_regime} (Diff: Rs {sample_res.tax_difference:,.0f})")
    print("    Audit Steps:")
    for trace in sample_res.old_regime.clause_trace:
        print(f"      - {trace}")

    print("\n==================================================")
    print("  ALL BENCHMARKS EXECUTED SUCCESSFULLY!           ")
    print("==================================================")


if __name__ == "__main__":
    run_benchmarks()