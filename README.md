# Fleiss' Multi-Rater Kappa

Calculate Fleiss' generalized kappa for nominal-category agreement among multiple raters. Each subject has one row of **non-negative integer category counts**; every subject must have the same number of raters (at least two).

## Features

- Browser calculator and CSV upload/export, without any server or third-party JavaScript dependencies
- Python function and command-line interface for count matrices
- Dataset-level CSV aggregation, with each subject's identifier retained in exported records
- Observed agreement, chance agreement, Fleiss' kappa, and descriptive Landis–Koch interpretation
- Null-hypothesis standard error, z-statistic and two-sided p-value for H₀: κ = 0 where defined
- Optional FastAPI service and an independent, generic task-audit subsystem

**Statistical caveat:** The reported standard error is the Fleiss–Nee–Landis *null* variance (1979). It is appropriate for the large-sample test of κ = 0, **not** for confidence intervals about an estimated nonzero κ. Results from small numbers of subjects require particular caution. If all ratings fall in one category, the code retains a legacy κ = 1 convention but reports inferential quantities as unavailable because the coefficient has a zero denominator mathematically. Interpretation bands are descriptive, not diagnostic thresholds.

## Live browser calculator

The repository includes a static application under `web/` suitable for GitHub Pages. On a local machine:

```bash
python -m http.server 8080 --directory web
```

Open http://localhost:8080/ and paste a JSON count matrix or upload a CSV file. Data stays in the browser; no network API is required. The production Pages deployment depends on the repository's GitHub Pages settings and workflow status.

## Python and CLI

The **kappa calculation itself uses only the Python standard library** (Python 3.10+).

```bash
python fleiss_kappa.py calc '[[3,0,0],[2,1,0],[0,3,0],[1,2,0]]'
python fleiss_kappa.py batch -i sample.csv -o results.csv
```

```python
from fleiss_kappa import fleiss_kappa

matrix = [[3, 0, 0], [2, 1, 0], [0, 3, 0], [1, 2, 0]]
result = fleiss_kappa(matrix)
print(result["kappa"], result["p_value"])
```

For batch input, include `cat1,cat2,...` columns (also `c1,c2,...` or `v1,v2,...`). Each CSV row is one subject. The output repeats the **one dataset-level statistic** alongside each source row to preserve identifiers. Fractional counts, unequal rater totals, and unnumbered category columns are rejected. `sample.csv` contains valid count data.

The legacy `fleiss_kappa.py single` numeric scoring interface remains for compatibility, but **its score and clinical tier are unrelated to Fleiss' kappa**. Use `calc` or `batch` for statistical analysis.

## Optional service and supervisor

```bash
python -m pip install -r requirements.txt
python cli.py serve --host 127.0.0.1 --port 8000
```

Send `POST /api/kappa` with `{"matrix":[[3,0],[0,3]]}` to calculate the coefficient; `GET /health` is available. The separate `python cli.py audit`, `python cli.py batch -i sample_tasks.csv`, and `/api/audit` endpoints use a generic rules-based task supervisor. **They do not compute Fleiss' kappa or implement validated CAP/CLSI clinical decision logic.** The chat interface is deterministic mock text, not a connection to a language model. `sample_tasks.csv` demonstrates its distinct input schema.

## Privacy and security

The static application computes locally and does not transmit uploaded content. The FastAPI service processes submitted data and has **no authentication or access control**; bind it to localhost unless deployment security is supplied separately. The optional supervisor uses pattern-based identifier checks, which **cannot reliably de-identify or detect all protected health information**. Do not submit patient-identifiable data. The supervisor audit trail is an **in-memory**, HMAC-SHA256-signed chain (key from `AUDIT_SECRET_KEY` or a random process-local key); verification checks both signatures and links. It is not persistent, independently anchored, or compliance certification.

## Development and testing

```bash
python -m pip install -r requirements.txt
python -m pytest -q
node --test tests/test_browser.mjs
```

No bundler is needed for the static app. The browser uses modern JavaScript modules and file APIs (recent Chrome, Firefox, Safari and Edge). CI runs Python 3.10–3.12 and Node browser-module tests.

## Mathematical reference

For `N` subjects, `m` ratings per subject, and `K` categories:

- `P_i = Σ_j n_ij(n_ij − 1) / [m(m − 1)]`
- `P̄ = Σ_i P_i / N`; `p_j = Σ_i n_ij / (Nm)`
- `P_e = Σ_j p_j²`; `κ = (P̄ − P_e) / (1 − P_e)`
- `Var₀(κ) = 2[P_e + P_e² − 2Σ_j p_j³] / [Nm(m−1)(1−P_e)²]`

References: Fleiss JL. *Psychological Bulletin* (1971), DOI: [10.1037/h0031619](https://doi.org/10.1037/h0031619); Fleiss JL, Nee JC, Landis JR. *Psychological Bulletin* (1979), DOI: [10.1037/0033-2909.86.5.974](https://doi.org/10.1037/0033-2909.86.5.974).

## License

MIT — see [LICENSE](LICENSE).
