# Fleiss Multi Rater Kappa

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)

> **Domain:** Clinical Decision Support & Inter-Observer Agreement Analysis

## What It Does

Computes **Fleiss' generalized kappa coefficient** for measuring inter-rater agreement among multiple raters across categorical items. The implementation provides:

- **Fleiss' kappa coefficient** (-1 to 1 scale)
- **Standard error** of the estimate
- **Z-score** for hypothesis testing
- **Two-tailed p-value** for statistical significance
- **Observed vs. chance-corrected agreement** metrics
- **Landis & Koch interpretation** (Poor to Almost Perfect)

Zero-dependency Python implementation with single evaluation, batch CSV processing, and CLI/API interfaces.

Author: Dr. Abu Suraih Sakhri
License: MIT

---

## Installation

```bash
pip install -r requirements.txt
```

Or with Docker:
```bash
docker-compose up --build
```

---

## Usage

### Python API

```python
from fleiss_kappa import fleiss_kappa

# 10 subjects, 3 raters, 3 categories
# matrix[i][j] = number of raters who assigned subject i to category j
matrix = [
    [3, 0, 0],  # All 3 raters agree on category 0
    [2, 1, 0],  # 2 raters category 0, 1 rater category 1
    [0, 3, 0],  # All 3 raters agree on category 1
]

result = fleiss_kappa(matrix)
print(f"Kappa: {result['kappa']}")
print(f"Interpretation: {result['interpretation']}")
print(f"95% CI: {result['kappa']:.3f} +/- {1.96 * result['standard_error']:.3f}")
```

### CLI Usage

```bash
# Direct matrix calculation
python fleiss_kappa.py calc '[[3,0,0],[2,1,0],[0,3,0]]'

# Single evaluation (legacy interface)
python fleiss_kappa.py single

# Batch CSV processing
python fleiss_kappa.py batch -i sample.csv -o results.csv

# Full supervisor system CLI
python cli.py audit --task-id "TASK-01" --primary 14.5 --secondary 4.2
python cli.py batch -i sample.csv -o results.csv
python cli.py verify-audit
python cli.py serve --host 127.0.0.1 --port 8000
```

### Input Data Format (Batch CSV)

CSV file where each row represents a subject and each numeric column represents a category count:

```csv
Patient_ID,cat1,cat2,cat3
PT-101,3,0,0
PT-102,1,2,0
PT-103,0,0,3
```

---

## Mathematical Formulation

Fleiss' kappa measures agreement among **m** raters across **k** categories for **n** subjects:

```
κ = (P̄ - P̄e) / (1 - P̄e)
```

Where:
- **P̄** = observed agreement = (1/n) Σᵢ Pᵢ
- **Pᵢ** = (1/(m(m-1))) Σⱼ nᵢⱼ(nᵢⱼ - 1) for subject i
- **P̄e** = chance agreement = Σⱼ pⱼ²
- **pⱼ** = (1/(nm)) Σᵢ nᵢⱼ

Interpretation scale (Landis & Koch, 1977):
| Kappa Range | Interpretation |
|-------------|----------------|
| < 0.00 | Poor |
| 0.00 - 0.20 | Slight |
| 0.21 - 0.40 | Fair |
| 0.41 - 0.60 | Moderate |
| 0.61 - 0.80 | Substantial |
| 0.81 - 1.00 | Almost Perfect |

---

## Security Features

- **PHI Outbound Guard:** AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers
- **HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation
- **Path Traversal Protection:** Input file paths are validated and resolved
- **Secure Key Generation:** Audit keys are randomly generated per deployment (configurable via `AUDIT_SECRET_KEY` env var)

---

## Testing

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## Container Deployment

```bash
docker build -t fleiss-multi-rater-kappa .
docker run -p 8000:8000 fleiss-multi-rater-kappa
```

Or with docker-compose:
```bash
docker-compose up
```

---

## Project Structure

```
fleiss-multi-rater-kappa/
├── fleiss_kappa.py      # Core kappa algorithm + CLI
├── cli.py               # Supervisor system CLI with audit/PHI guard
├── agents/
│   ├── base.py          # Security, PHI guard, HMAC audit trail
│   ├── models.py        # Pydantic data models
│   ├── supervisor.py    # Multi-worker orchestration
│   ├── workers.py       # Specialized evaluation workers
│   ├── api.py           # FastAPI REST endpoints
│   ├── metrics.py       # Prometheus metrics collector
│   ├── learning.py      # Bayesian calibration engine
│   └── streamer.py      # WebSocket telemetry
├── enrichment.py        # Extended feature engines
├── simulator.py         # Stress testing simulator
├── tests/               # Test suite
├── sample.csv           # Example input data
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
