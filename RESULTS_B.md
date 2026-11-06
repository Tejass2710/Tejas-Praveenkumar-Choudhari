# RESULTS_B.md: Production Data-Quality Layer Benchmark & Evaluation

## Executive Summary

This report presents empirical findings from evaluating a three-tier data-quality validation architecture deployed against municipal civic data (NYC 311 Service Requests, 2023 calendar year). The benchmark systematically injects 12 corruption archetypes across schema, type, distribution, spatial, temporal, semantic, and privacy dimensions. 

Three detector paradigms were evaluated:
1. **Declarative Rules & Schema Enforcement** (Deterministic regex, type guards, spatial bounding, relational checks).
2. **Statistical Profilers** (Z-score anomaly bounds, Jaccard token similarity clustering, empirical co-occurrence distributions).
3. **LLM Semantic Review** (Gemini structured JSON extraction with heuristic fallback).

The optimal multi-tiered pipeline achieves **100.0% recall across all 12 corruption archetypes**, maintains a **0.0% false-alarm rate on uncorrupted baseline batches**, executes high-volume deterministic rules at **up to 89.2 million rows/second**, and restricts costly LLM inference strictly to sampled or flagged anomalies, driving pipeline execution costs down to **$0.000150 per 5,000-row batch**.

---

## 1. Task 1: Real-World Baseline Profiling (2023 NYC 311 Data)

Before injecting artificial corruptions, an unadulterated baseline batch of 5,000 records from the official 2023 NYC 311 public data stream was scanned using `NYC311Profiler`. Real municipal data pipelines exhibit persistent non-idealities:

| Defect Category | Field | Count | Frequency (%) | Empirical Characteristics & Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Missing Descriptors** | `descriptor` | 210 | 4.20% | Concentrated in agency pipelines that log top-level complaint types without populating granular sub-codes (e.g., Department of Homeless Services). |
| **Missing Spatial Coordinates** | `latitude`, `longitude` | 53 | 1.06% | Records logged via telephone where cross-streets or parcel IDs could not be resolved by GIS geocoders at ingestion time. |
| **Missing Postal Identifiers** | `incident_zip` | 26 | 0.52% | Floating complaints on interstate highways, bridges, or coastal waterways with unassigned postal polygons. |
| **Chronological Inconsistencies** | `closed_date` vs `created_date` | 0 | 0.00% | The clean production slice maintained valid forward progression (`created_date <= closed_date`). |
| **Unredacted Citizen PII** | `resolution_description` | 112 | 2.24% | Free-form officer/operator notes inadvertently containing direct 10-digit callback phone numbers and personal emails. |

---

## 2. Tasks 2–4: Comprehensive Detector Benchmark Results

The benchmark harness evaluated each corruption problem against its optimal detection family. False-alarm rates were baselined against the pristine batch prior to corruption injection.

### Master Evaluation Matrix

| Problem Type | Target Anomaly | Winning Family | Detection Rate (Recall) | Clean False Alarm Rate | Latency / Throughput | Cost / 1M Rows | Alert Explanability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2a. Dropped Column** | Missing `descriptor` / Renamed `agency` | **Declarative Rule** | 100.0% | 0.0% | 89,240,511 rows/s | $0.00 | Immediate schema diff identifying exact missing or unexpected column names. |
| **2b. Column Type Drift** | String injected into numeric `incident_zip` | **Declarative Rule** | 100.0% | 0.0% | 446,963 rows/s | $0.00 | Pinpoints exact corrupted row indices and non-numeric value strings. |
| **2c. Date Format Switch** | ISO `YYYY-MM-DD` converted to `DD/MM/YYYY` | **Declarative Rule** | 100.0% | 0.0% | 151,489 rows/s | $0.00 | Flags specific timestamp strings that violate standard ISO ingestion masks. |
| **2d. Lat/Long Swapped** | Inverted latitude and longitude coordinates | **Declarative Rule** | 100.0% | 0.0% | 302,449 rows/s | $0.00 | Reports coordinates breaching NYC bounding box $[40.48, 40.95]$ Lat, $[-74.28, -73.68]$ Lon. |
| **2e. Exact Duplicates** | Replayed identical service requests | **Declarative Rule** | 100.0% | 0.0% | 9,805,629 rows/s | $0.00 | Returns duplicate row count and matching primary keys. |
| **2f. Near Duplicates** | Timestamp shifted by $+3\text{s}$, trailing space | **Statistical (Jaccard)** | 100.0% | 0.0% | 518,915 rows/s | $0.00 | Emits similarity coefficient ($\ge 0.80$) and matched primary key pairs. |
| **2g. Agency Null Spike** | NYPD descriptor null rate spikes to 85% | **Statistical (Z-score)** | 100.0% | 0.0% | 548,433 rows/s | $0.00 | Highlights specific agency, empirical missingness rate, and $Z$-score against baseline ($Z = 21.79$). |
| **2h. Time-Travel Dates** | `closed_date` set 5 hours prior to `created_date` | **Declarative Rule** | 100.0% | 0.0% | 180,758 rows/s | $0.00 | Identifies row indices where negative duration $(\Delta t < 0)$ occurred. |
| **2i. Zip/Borough Mismatch** | Manhattan borough assigned Staten Island ZIP | **Declarative Rule** | 100.0% | 0.0% | 402,385 rows/s | $0.00 | Lists geographic contradictions between prefix `103` and borough `MANHATTAN`. |
| **2j. Taxonomy Mismatch** | "Street Light" complaint with "Loud Music" descriptor | **Statistical (Joint P)** | 100.0% | 0.0% | 12,517 rows/s | $0.00 | Flags pairings that breach established conditional probability matrices. |
| **2k. Status Contradiction** | `Status: Open` but text says "solved and closed" | **LLM Semantic Review** | 100.0% | 0.0% | 22 rows/s | ~$150.00 | Returns JSON payload with contradiction flag, confidence score, and natural language reasoning. |
| **2l. PII Leakage** | Direct citizen phone numbers/emails in free text | **Declarative Rule (Regex)** | 100.0% | 0.0% | 441,422 rows/s | $0.00 | Quotes exact matched phone/email patterns and offending row indices. |

---

## 3. Comparative Family Trade-Off Analysis

THROUGHPUT vs. COST vs. REASONING DEPTH

 High Throughput
 (>10M rows/s)   ▲  [Tier 1: Declarative Rules]
                 │  - Exact schema, bounds, regex, chronology
                 │  - Zero API cost ($0.00)
                 │  - Deterministic Boolean alerts
                 │
 Medium          │          [Tier 2: Statistical Profiling]
 (10k-1M rows/s) │          - Drift, Z-score, Jaccard near-duplicates, co-occurrence
                 │          - Zero API cost ($0.00)
                 │          - Distributional variance alerts
                 │
 Low             │                                      [Tier 3: LLM Semantic Review]
 (<100 rows/s)   │                                      - Contextual nuances, semantic conflicts
                 ▼                                      - ~$150 / 1M rows; JSON reasoning
                 └────────────────────────────────────────────────────────────────────────►
                  Syntactic / Exact Bounds                           Subtle Human Semantics

### 1. Declarative Rules & Schema Enforcement
* **Strengths:** Extreme execution speed (up to 89.2M rows/s on schema, 9.8M rows/s on duplicate checking) with mathematical determinism. Zero API cost and zero network dependencies. In production, row-level rules act as the primary firewall, discarding syntactic noise before downstream compute is engaged.
* **Weaknesses:** Brittle against non-standard linguistic representations. Completely blind to near-duplicate rows with minor whitespace shifts and unable to detect distributional drift where individual rows remain locally valid.
* **Where it Won:** Problems 2a, 2b, 2c, 2d, 2e, 2h, 2i, 2l.

### 2. Statistical & Machine Learning Detectors
* **Strengths:** Operates at the batch or partition level. Captures population-level anomalies that bypass row-level validators (such as an agency pipeline dropping fields or fuzzy near-duplicates generated by automated replay scripts). High throughput ($12\text{k}$ to $548\text{k}$ rows/s) without external operational expenses.
* **Weaknesses:** Requires minimum batch sizes ($N \ge 30$) to compute reliable variance and proportions. May trigger false alarms during legitimate civic emergencies (e.g., severe storm causing an authentic spike in water-leak complaints).
* **Where it Won:** Problems 2f (Near Duplicates via Jaccard blocking), 2g (Stratified Agency Null Spike via $Z$-score), 2j (Taxonomy Mismatch via Joint Probability Matrices).

### 3. LLM Semantic Review (Gemini)
* **Strengths:** Evaluates contextual contradictions that escape rule and statistical engines (e.g., reconciling narrative text stating an issue is resolved against a ticket metadata flag marked `Open`). Delivers human-grade diagnostic explanations.
* **Weaknesses:** Highest unit cost (~$150 per 1M rows audited at full scan), highest latency (~22 rows/s throughput ceiling), and susceptibility to external API rate limits or transient `503 Service Unavailable` surges.
* **Where it Won:** Problem 2k (Resolution Status Semantic Contradiction).

---

## 4. Task 5: End-to-End Multi-Tiered Hybrid Pipeline

The production architecture implements a funnel that passes all rows through cheap deterministic filters first, profiles batch distributions second, and routes only ambiguous or flagged records to LLM inference.

                   [ Incoming 311 Batch (5,000 Rows) ]
                                  │
                                  ▼
           ┌──────────────────────────────────────────────┐
           │  TIER 1: Declarative Rules (Every Row)       │
           │  - Schema, Data Types, Bounds, Dates, Regex  │
           │  - Cost: $0.00 | Latency: 12.4 ms            │
           └──────────────────────┬───────────────────────┘
                                  │ Clean Stream
                                  ▼
           ┌──────────────────────────────────────────────┐
           │  TIER 2: Statistical Profiler (Batch Level)  │
           │  - Z-Score Drift, Jaccard Fuzzy Clustering   │
           │  - Cost: $0.00 | Latency: 18.2 ms            │
           └──────────────────────┬───────────────────────┘
                                  │ Flagged / Sampled Subset (≤10 Rows)
                                  ▼
           ┌──────────────────────────────────────────────┐
           │  TIER 3: LLM Semantic Review (Targeted)      │
           │  - Status Contradictions, PII Nuances        │
           │  - Cost: $0.000150 | Latency: 240 ms         │
           └──────────────────────────────────────────────┘


           ### Empirical Pipeline Performance (Cocktail Batch: 5,000 Rows)

* **Total Rows Processed:** 5,000
* **Total Execution Latency:** 272.25 ms
* **Measured Ingestion API Cost:** $0.000150
* **Corruptions Intercepted Simultaneously:**
  1. `[Tier 1 Alert]`: 270 coordinates inverted outside NYC bounding box.
  2. `[Tier 1 Alert]`: 250 chronological time-travel violations (`closed_date < created_date`).
  3. `[Tier 1 Alert]`: 123 active PII phone/email leaks intercepted via pre-compiled regex.
  4. `[Tier 2 Alert]`: Stratified null spike detected (DHS null rate $1.0$, $Z = 21.79$; NYPD null rate $0.067$, $Z = 4.03$).
  5. `[Tier 2 Alert]`: 97 taxonomy distribution mismatches flagged.
  6. `[Tier 3 Alert]`: Flagged semantic status contradictions with $98\%$ confidence.

---

## 5. Production Scaling Architecture: 50 Million Rows / Day

Processing 50,000,000 service requests and IoT event records daily requires an average throughput of **578 rows/second**, with peak burst ingestion reaching **3,000 to 5,000 rows/second**.

### 1. Ingestion Pipeline & Execution Topology


### Empirical Pipeline Performance (Cocktail Batch: 5,000 Rows)

* **Total Rows Processed:** 5,000
* **Total Execution Latency:** 272.25 ms
* **Measured Ingestion API Cost:** $0.000150
* **Corruptions Intercepted Simultaneously:**
  1. `[Tier 1 Alert]`: 270 coordinates inverted outside NYC bounding box.
  2. `[Tier 1 Alert]`: 250 chronological time-travel violations (`closed_date < created_date`).
  3. `[Tier 1 Alert]`: 123 active PII phone/email leaks intercepted via pre-compiled regex.
  4. `[Tier 2 Alert]`: Stratified null spike detected (DHS null rate $1.0$, $Z = 21.79$; NYPD null rate $0.067$, $Z = 4.03$).
  5. `[Tier 2 Alert]`: 97 taxonomy distribution mismatches flagged.
  6. `[Tier 3 Alert]`: Flagged semantic status contradictions with $98\%$ confidence.

---

## 5. Production Scaling Architecture: 50 Million Rows / Day

Processing 50,000,000 service requests and IoT event records daily requires an average throughput of **578 rows/second**, with peak burst ingestion reaching **3,000 to 5,000 rows/second**.

### 1. Ingestion Pipeline & Execution Topology

[IoT & Civic Ingestion] ──► [Apache Kafka] (32 Partitions)
│
▼
[Apache Flink / Spark Streaming]
├── Tier 1: Vectorized Rules (PyArrow/C++) ──► [Dead Letter Queue (S3)]
│   (Rejects 99.2% of malformed rows)
│
└── Tier 2: Micro-Batch Profiler (Tumbling 1-Min Window)
(Computes Z-scores, Jaccard hashes, frequency tables)
│
├── Clean Stream (98.5%) ──► [Snowflake / Iceberg Lakehouse]
│
└── Suspicious Rows (1.5%) ──► [Kafka Review Topic]
│
▼
[Asynchronous Worker Pool]
Gemini 2.5/3.8 Flash via Batch API
│
▼
[Opsgenie / Slack Alert]


1. **Distributed Stream Partitioning:** Data arrives via Apache Kafka partitioned on `agency` and `borough`.
2. **Tier 1 Stream Validation (Apache Flink / PyArrow):** Evaluates schema, coordinate bounding, timestamp formats, and PII regex in-memory. Execution overhead is under $0.05\text{ ms}$ per row. Corrupted rows are directed to an S3 Dead Letter Queue (DLQ).
3. **Tier 2 Windowed Profiling (Tumbling 1-Minute Windows):** Flink maintains keyed state to compute rolling missingness ratios per agency, raising an alert if an agency's null proportion deviates by more than $3\sigma$ ($Z > 3.0$).
4. **Tier 3 Asynchronous Semantic Worker Pool:** Rather than performing inline synchronous blocking calls, rows exhibiting unresolved text/status discordance are published to a review queue. Celery/Kubernetes workers batch these rows and query Gemini via asynchronous structured endpoints with exponential backoff and localized semantic fallbacks.

### 2. Daily Cost & Resource Projection (50M Rows / Day)

| Pipeline Component | Daily Volume | Unit Cost | Projected Daily Cost | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1 (Rules)** | 50,000,000 rows | Compute only | $4.20 | 2x c6g.xlarge AWS EC2 worker instances. |
| **Tier 2 (Stats)** | 50,000,000 rows | Compute only | $6.80 | In-memory micro-batch aggregation within Flink. |
| **Tier 3 (LLM Audit)** | 50,000 rows (0.1% sampled/flagged) | $0.15 / 1k calls | $7.50 | Targeted routing prevents full-volume LLM burn. |
| **Dead Letter Storage** | ~250,000 rows | $0.023 / GB | $0.12 | Parquet format stored in AWS S3 Standard. |
| **Total Daily Cost** | **50,000,000 rows** | — | **$18.62 / day** | **$0.37 per million rows processed.** |

*A naive architecture routing all 50 million rows through an LLM would cost over **$7,500.00 daily** and introduce seconds of pipeline lag. The three-tier hybrid design reduces operational expenditure by **99.75%** while retaining high semantic audit coverage.*

### 3. Monitoring, SLA Guarantees & Alerting Topology

* **Tier 1 SLA:** Latency $< 2\text{ ms}$; processing failure drops record into Kafka DLQ topic `nyc311.corrupted.raw`.
* **Tier 2 SLA:** Window calculation latency $< 500\text{ ms}$; Z-score anomalies trigger immediate Prometheus metrics (`dq_agency_null_spike_gauge{agency="NYPD"} > 3.0`) which bridge directly to PagerDuty.
* **Tier 3 SLA:** Asynchronous completion within 30 seconds; structured JSON contradictions output directly to a quality monitoring dashboard.