# AI Usage & Failure Disclosure

### 1. Tools & Models Used
- **Claude / Gemini (Interactive)**: Architecture design, edge-case generation, and test scaffolding.
- **Gemini API (`gemini-2.5-flash`, `gemini-3.8-flash`)**: 
  - Project A: Query-time computation baseline (Task 2b) and NLP intent parsing (Task 3).
  - Project B: Semantic review for ticket status contradictions (Task 2k) and hybrid pipeline tier-3 auditing (Task 5).

---

### 2. Concrete Failures Caught & Resolved

#### Failure 1 (Project A): Section 87A Marginal Relief Error
- **The Failure**: Query-time LLM applied full ₹25,000 rebate on ₹7,00,010 income (New Regime), returning ₹0 tax.
- **Ground Truth**: Rebate ceiling is ₹7,00,000. Marginal relief limits tax to income above ₹7L (₹10 tax payable).
- **Resolution**: Deterministic test suite flagged the ₹10 mismatch against `DeterministicTaxEngine`.

#### Failure 2 (Project B): Type Incompatibility in Pandas Mutation
- **The Failure**: Injecting strings into numeric zip codes caused `LossySetitemError` / `TypeError`.
- **Ground Truth**: Mixed-type benchmarking requires explicit `object` dtype casting before injecting string corruptions.
- **Resolution**: Test harness crashed; resolved by casting target columns to `object` before injection.

#### Failure 3 (Project B): Deprecated Endpoints & API 503 Outages
- **The Failure**: `gemini-1.5-flash` returned 404, while `gemini-3.8-flash` hit transient 503 high-demand errors, stalling the pipeline.
- **Ground Truth**: Production pipelines require active model fallbacks and non-blocking failure modes.
- **Resolution**: Updated model cascade and implemented an in-memory heuristic fallback to guarantee 100% pipeline uptime.

---

### 3. Verification
All calculations, tax brackets, and data quality benchmark numbers were independently verified using `python run_project_a.py` and `python run_project_b.py`.