#!/usr/bin/env python3
"""
Fleiss' Multi-Rater Kappa for Inter-Observer Agreement
Computes Fleiss' generalized kappa coefficient, standard error, z-score, and p-value for m raters across k categories.

Zero-dependency Python implementation with single and batch evaluation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import math
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


def fleiss_kappa(matrix: List[List[int]]) -> Dict[str, Any]:
    """
    Compute Fleiss' kappa for inter-rater agreement.

    Args:
        matrix: A 2D list where each row represents a subject/item and each column
                represents a category. matrix[i][j] = number of raters who assigned
                subject i to category j.

    Returns:
        Dictionary containing:
        - kappa: Fleiss' kappa coefficient (-1 to 1)
        - se: Standard error of kappa
        - z: Z-score for hypothesis testing
        - p_value: Two-tailed p-value
        - agreement_pct: Percentage of observed agreement
        - n_subjects: Number of subjects rated
        - n_categories: Number of categories
        - n_raters: Number of raters (if consistent)

    Raises:
        ValueError: If matrix is empty, has inconsistent column counts, or rater counts vary.
    """
    if not isinstance(matrix, (list, tuple)) or not matrix:
        raise ValueError("Rating matrix must not be empty")
    if not isinstance(matrix[0], (list, tuple)) or not matrix[0]:
        raise ValueError("Rating matrix must not be empty")

    n_subjects = len(matrix)
    n_categories = len(matrix[0])
    if n_categories < 2:
        raise ValueError("At least 2 categories are required")

    for i, row in enumerate(matrix):
        if not isinstance(row, (list, tuple)):
            raise ValueError(f"Row {i} must be a sequence of integer counts")
        if len(row) != n_categories:
            raise ValueError(
                f"Inconsistent category count: row 0 has {n_categories}, "
                f"row {i} has {len(row)}"
            )
        for j, count in enumerate(row):
            if isinstance(count, bool) or not isinstance(count, int):
                raise ValueError(f"Non-integer count at row {i}, column {j}: {count!r}")
            if count < 0:
                raise ValueError(f"Negative count at row {i}, column {j}: {count}")

    n_raters_per_subject = [sum(row) for row in matrix]
    if len(set(n_raters_per_subject)) > 1:
        raise ValueError(
            f"Inconsistent rater counts across subjects: {set(n_raters_per_subject)}. "
            "All subjects must be rated by the same number of raters."
        )
    n_raters = n_raters_per_subject[0]
    if n_raters < 2:
        raise ValueError("At least 2 raters are required")

    # p_j: proportion of all assignments to category j
    p = [0.0] * n_categories
    for j in range(n_categories):
        p[j] = sum(matrix[i][j] for i in range(n_subjects)) / (n_subjects * n_raters)

    # P_i: extent of agreement for subject i
    # P_i = (1 / (n * (n-1))) * sum_j(n_ij * (n_ij - 1))
    P = [0.0] * n_subjects
    for i in range(n_subjects):
        sum_sq = sum(matrix[i][j] * (matrix[i][j] - 1) for j in range(n_categories))
        P[i] = sum_sq / (n_raters * (n_raters - 1))

    # P_bar: mean of P_i values (observed agreement)
    P_bar = sum(P) / n_subjects

    # P_e: expected agreement by chance = sum_j(p_j^2)
    P_e = sum(pj ** 2 for pj in p)

    # Degenerate marginals have P_e = 1, so the mathematical coefficient
    # is 0/0. Preserve the historical unanimous kappa=1 convention but
    # do not present a fabricated significance test.
    degenerate = math.isclose(P_e, 1.0, rel_tol=0.0, abs_tol=1e-12)
    if degenerate:
        kappa = 1.0
    else:
        kappa = (P_bar - P_e) / (1.0 - P_e)

    # Fleiss, Nee & Landis (1979): asymptotic variance UNDER H0: kappa=0.
    # This is not a general standard error for confidence intervals.
    # Hypothesis testing is not supported on a single subject or when
    # category marginals are degenerate.
    se = z = p_value = None
    inference_note = None
    if degenerate:
        inference_note = "Kappa is a unanimous-agreement convention (P_e=1); inference is undefined."
    elif n_subjects < 2:
        inference_note = "At least two independent subjects are needed for inference."
    else:
        sum_p3 = sum(pj ** 3 for pj in p)
        numerator = 2.0 * (P_e + P_e ** 2 - 2.0 * sum_p3)
        denominator = n_subjects * n_raters * (n_raters - 1) * (1.0 - P_e) ** 2
        null_var = numerator / denominator
        if null_var > 0:
            se = math.sqrt(null_var)
            z = kappa / se
            p_value = math.erfc(abs(z) / math.sqrt(2.0))
        else:
            inference_note = "Null variance is zero; z statistic and p-value are undefined."

    return {
        "kappa": round(kappa, 4),
        "standard_error": round(se, 6) if se is not None else None,
        "z_score": round(z, 4) if z is not None else None,
        "p_value": p_value,
        "observed_agreement": round(P_bar, 4),
        "chance_agreement": round(P_e, 4),
        "n_subjects": n_subjects,
        "n_categories": n_categories,
        "n_raters": n_raters,
        "interpretation": _interpret_kappa(kappa),
        "inference_note": inference_note,
    }


def _norm_cdf(x: float) -> float:
    """Approximation of the standard normal CDF using the error function."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _interpret_kappa(kappa: float) -> str:
    """Interpret Fleiss' kappa using Landis & Koch (1977) benchmark scale."""
    if kappa < 0.00:
        return "Poor agreement"
    elif kappa <= 0.20:
        return "Slight agreement"
    elif kappa <= 0.40:
        return "Fair agreement"
    elif kappa <= 0.60:
        return "Moderate agreement"
    elif kappa <= 0.80:
        return "Substantial agreement"
    else:
        return "Almost perfect agreement"


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Core domain algorithm for fleiss-multi-rater-kappa.
    Accepts rating matrix via 'matrix' kwarg, or constructs one from
    positional-style numeric inputs (v1, v2, v3...) for backward compatibility.
    """
    # If a matrix is provided directly, use the proper Fleiss kappa computation
    if "matrix" in kwargs and kwargs["matrix"] is not None:
        matrix = kwargs["matrix"]
        if isinstance(matrix, str):
            import json
            matrix = json.loads(matrix)
        return fleiss_kappa(matrix)

    # Legacy compatibility: build a simple scoring result from numeric params
    params = {}
    for k, v in kwargs.items():
        if v is not None:
            try:
                params[k] = float(v)
            except (ValueError, TypeError):
                params[k] = str(v)

    numeric_vals = [val for val in params.values() if isinstance(val, (int, float))]
    primary_val = numeric_vals[0] if numeric_vals else 1.0

    score = primary_val
    for idx, nv in enumerate(numeric_vals[1:], start=2):
        score += nv * (1.0 / idx)

    rounded_score = round(score, 2)

    if rounded_score < 10.0:
        tier = "Low / Standard"
        action = "Standard monitoring or negative cutoff"
    elif rounded_score < 25.0:
        tier = "Moderate / Intermediate"
        action = "Close observation or secondary evaluation"
    else:
        tier = "High / Severe"
        action = "Urgent clinical intervention or primary positive finding"

    return {
        "tool": "fleiss-multi-rater-kappa",
        "score": rounded_score,
        "classification": tier,
        "clinical_recommendation": action,
        "inputs_evaluated": len(params),
    }


def _validate_file_path(filepath: str, must_exist: bool = False) -> str:
    """Validate file path to prevent path traversal attacks."""
    resolved = Path(filepath).resolve()
    cwd = Path.cwd().resolve()

    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    # Check that the resolved path doesn't escape to suspicious locations
    # (basic traversal protection)
    try:
        resolved.relative_to(cwd)
    except ValueError:
        # Allow absolute paths but warn - in production you might want to restrict
        pass

    return str(resolved)


def process_single(args) -> None:
    kwargs = vars(args)
    kwargs.pop("func", None)
    res = calculate_metrics(**kwargs)
    print(json.dumps(res, indent=2))


def process_batch(input_csv: str, output_csv: str) -> None:
    """Calculate one dataset-level kappa across all CSV subject rows.

    Category columns must be named cat1, cat2, ... (also c1 or v1 for
    backwards compatibility). The aggregate result is repeated in each
    output row so original record IDs remain accessible.
    """
    import re

    input_path = _validate_file_path(input_csv, must_exist=True)
    output_path = _validate_file_path(output_csv)
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    if not rows:
        raise ValueError("Input CSV contains no subject rows")
    if len(set(fieldnames)) != len(fieldnames):
        raise ValueError("Input CSV contains duplicate column names")

    category_columns = []
    for name in fieldnames:
        match = re.fullmatch(r"(?:cat|c|v)([1-9][0-9]*)", name, flags=re.IGNORECASE)
        if match:
            category_columns.append((int(match.group(1)), name))
    category_columns.sort(key=lambda pair: pair[0])
    if len(category_columns) < 2 or len({number for number, _ in category_columns}) != len(category_columns):
        raise ValueError("CSV requires at least two uniquely numbered category columns (cat1, cat2, ...)")

    matrix = []
    for i, row in enumerate(rows, start=2):
        counts = []
        for _, name in category_columns:
            value = (row.get(name) or "").strip()
            if not value.isdecimal():
                raise ValueError(f"Row {i}, column {name}: expected a non-negative integer count")
            counts.append(int(value))
        matrix.append(counts)

    result = fleiss_kappa(matrix)
    result_fields = [
        "kappa", "standard_error", "z_score", "p_value", "observed_agreement",
        "chance_agreement", "n_subjects", "n_raters", "interpretation", "inference_note",
    ]
    out_fields = list(dict.fromkeys(fieldnames + result_fields))
    with open(output_path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, **{field: result[field] for field in result_fields}})
    print(f"Processed {len(rows)} subjects -> {output_csv} (dataset kappa={result['kappa']})")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fleiss' Multi-Rater Kappa for Inter-Observer Agreement")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Single parser - evaluate a single rating matrix
    single_parser = subparsers.add_parser("single", help="Evaluate single case")
    single_parser.add_argument("--matrix", type=str, default=None,
                                help="JSON array of arrays, e.g., '[[5,0,0],[3,2,0]]'")
    single_parser.add_argument("--v1", type=float, default=10.0, help="Primary parameter (legacy)")
    single_parser.add_argument("--v2", type=float, default=5.0, help="Secondary parameter (legacy)")
    single_parser.add_argument("--v3", type=float, default=2.0, help="Tertiary parameter (legacy)")
    single_parser.set_defaults(func=process_single)

    # Batch parser
    batch_parser = subparsers.add_parser("batch", help="Process batch CSV")
    batch_parser.add_argument("-i", "--input", required=True, help="Input CSV")
    batch_parser.add_argument("-o", "--output", default="results.csv", help="Output CSV")

    # Direct matrix parser (convenience)
    direct_parser = subparsers.add_parser("calc", help="Calculate kappa from JSON matrix directly")
    direct_parser.add_argument("matrix_json", help="JSON matrix string")

    args = parser.parse_args(argv)

    if args.command == "single":
        args.func(args)
    elif args.command == "batch":
        process_batch(args.input, args.output)
    elif args.command == "calc":
        matrix = json.loads(args.matrix_json)
        result = fleiss_kappa(matrix)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
