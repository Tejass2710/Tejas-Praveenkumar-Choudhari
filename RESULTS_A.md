# RESULTS_A: Rules vs. LLM Income-Tax Engine

## 1. Task 4: Performance & Accuracy Benchmark

| Metric | Hand-Coded Rules (Task 2a) | LLM at Query Time (Task 2b) | LLM-Compiled Rules (Task 2c) |
| :--- | :--- | :--- | :--- |
| **Rupee-Exact Accuracy** | **100.0%** (200/200) | 88.5% (177/200) | **100.0%** (200/200) |
| **Determinism (10 runs)** | **100% Identical** | 94.0% Consistency | **100% Identical** |
| **p95 Latency** | **0.23 ms** | ~1,450 ms | **0.20 ms** |
| **Cost per 1,000 requests**| **$0.00** | ~$0.30 - $0.50 | **$0.00** |
| **Auditability** | Complete statutory clause trace per rupee | Post-hoc verbal explanation | Complete statutory clause trace per rupee |

> **Official Calculator Verification**: 30 critical edge-case profiles (including rebate boundaries at ₹5,00,000, ₹5,00,010, ₹7,00,000, ₹7,00,010, and surcharge steps at ₹50,00,000) were validated against the Income Tax Department's official online portal calculator (incometax.gov.in) with 100% rupee-exact match.
---

## 2. Task 5: The Law Changes (Finance Act 2025 Transition)

### Transition Log & Failure Analysis
- **Hand-Coded Engine (2a)**:
  - *Time to adapt*: 15 minutes to modify `new_slabs` and rebate limit in `config.py`.
  - *What broke*: 0 test regressions.
  - *Silent failures*: **0**.
- **LLM-Compiled Rules (2c)**:
  - *Time to adapt*: 5 minutes (LLM synthesized the revised slab AST structure, verified via deterministic test harness).
  - *What broke*: 0 test regressions post-review.
  - *Silent failures*: **0**.
- **LLM at Query Time (2b)**:
  - *Time to adapt*: 25 minutes of prompt engineering.
  - *What broke*: Prompt interference. The model hallucinated FY 2024-25 rebate rules (₹7L) on FY 2025-26 queries between ₹7L and ₹12L.
  - *Silent failures*: **14 silent failures** (returned mathematically incorrect tax without raising an error).

---

## 3. Final Production Design (Architecture for 100,000 Users)

### Hybrid Perception-Execution Architecture
1. **Perception Layer (LLM - Gemini Flash)**:
   - Responsible strictly for unstructured text extraction (Hinglish/plain language) into a validated Pydantic schema.
   - Detects ambiguities (e.g., unspecified rent amounts, unstated parental senior-citizen status) and generates targeted clarifying questions instead of guessing.
2. **Execution Layer (Deterministic Compiled Rules)**:
   - Handles all mathematical computations (Section 115BAC slabs, standard deductions, Section 87A rebate, surcharge, and marginal relief).
   - Zero LLM involvement during computation guarantees rupee-exact precision, 0 ms-class latency, and zero per-calculation token cost.
3. **Auditability & Explanation**:
   - Uses parameterized string templates citing statutory sections (`Sec 16(ia)`, `Sec 10(13A)`, `Sec 80C`) rather than open-ended text generation, eliminating financial hallucinations.

   ### Future Budget Maintenance & CI/CD Strategy
- **Configuration Decoupling**: Slabs, rebate limits, and standard deductions live strictly in immutable dataclasses (`config.py`). New budgets are updated via config patches without altering algorithmic logic.
- **Automated Regression Gates**: A pre-merge CI suite runs 500+ synthetic edge cases across rebate thresholds, marginal relief borders, and surcharge steps before deployment.
- **Prompt Isolation**: Because the LLM only extracts entities into a validated Pydantic schema, the engine remains immune to foundational model training cutoff drift and memory bias.