"""
Comprehensive test suite for Fleiss' Multi-Rater Kappa core algorithm.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import math
import pytest
from fleiss_kappa import fleiss_kappa, calculate_metrics, process_batch, main


class TestFleissKappaCore:
    """Tests for the core Fleiss' kappa computation."""

    def test_perfect_agreement(self):
        """All raters assign all subjects to the same category."""
        # 10 subjects, 3 raters, all agree on category 0
        matrix = [[3, 0, 0]] * 10
        result = fleiss_kappa(matrix)
        assert result["kappa"] == 1.0
        assert result["observed_agreement"] == 1.0
        assert result["interpretation"] == "Almost perfect agreement"

    def test_chance_level_agreement(self):
        """Equal distribution across categories should yield kappa near 0 or negative."""
        # With [1,1,1] distribution, each rater chose a different category
        # This represents complete disagreement, so kappa should be negative
        matrix = [[1, 1, 1] for _ in range(100)]
        result = fleiss_kappa(matrix)
        assert -1.0 <= result["kappa"] <= 0.0  # Negative (complete disagreement)

    def test_fair_agreement(self):
        """Fair agreement scenario with known kappa."""
        # 50 subjects, 4 raters, 2 categories
        # Each subject split 50/50: P_bar=0.333, P_e=0.5, kappa=-0.333
        matrix = [[2, 2] for _ in range(50)]
        result = fleiss_kappa(matrix)
        assert abs(result["kappa"] - (-0.333)) < 0.05

    def test_moderate_agreement(self):
        """Moderate agreement scenario."""
        # 5 subjects, 4 raters, 3 categories
        matrix = [
            [4, 0, 0],  # Perfect agreement
            [4, 0, 0],
            [2, 2, 0],  # Some disagreement
            [2, 1, 1],  # More disagreement
            [1, 2, 1],  # Even more disagreement
        ]
        result = fleiss_kappa(matrix)
        assert -1.0 <= result["kappa"] <= 1.0
        assert result["n_subjects"] == 5
        assert result["n_raters"] == 4
        assert result["n_categories"] == 3

    def test_two_categories(self):
        """Binary classification scenario."""
        matrix = [
            [3, 0],
            [2, 1],
            [1, 2],
            [0, 3],
        ]
        result = fleiss_kappa(matrix)
        assert result["n_categories"] == 2
        assert -1.0 <= result["kappa"] <= 1.0

    def test_kappa_range(self):
        """Kappa should always be in [-1, 1]."""
        test_cases = [
            [[5, 0, 0]] * 3,
            [[2, 2, 1]] * 4,
            [[1, 1, 1], [2, 1, 0], [0, 3, 0], [1, 0, 2]] * 2,
        ]
        for matrix in test_cases:
            result = fleiss_kappa(matrix)
            assert -1.0 <= result["kappa"] <= 1.0

    def test_standard_error_non_negative(self):
        """Standard error should be non-negative."""
        matrix = [[3, 0, 0]] * 5
        result = fleiss_kappa(matrix)
        assert result["standard_error"] >= 0

    def test_p_value_range(self):
        """P-value should be in [0, 1]."""
        matrix = [[2, 1, 0]] * 4
        result = fleiss_kappa(matrix)
        assert 0.0 <= result["p_value"] <= 1.0

    def test_literature_example(self):
        """
        Test against the classic Fleiss' kappa example from literature.
        10 subjects, 5 raters, 4 categories.
        Known result: kappa ≈ 0.35 (verified by manual calculation)
        """
        matrix = [
            [0, 0, 0, 5],
            [0, 1, 3, 1],
            [0, 0, 3, 2],
            [0, 0, 0, 5],
            [0, 2, 3, 0],
            [0, 0, 0, 5],
            [0, 0, 0, 5],
            [0, 0, 0, 5],
            [0, 1, 2, 2],
            [2, 0, 0, 3],
        ]
        result = fleiss_kappa(matrix)
        # Allow reasonable tolerance for floating-point arithmetic
        # Manual calculation gives: kappa ≈ 0.3504
        assert abs(result["kappa"] - 0.35) < 0.05

    def test_empty_matrix_raises(self):
        """Empty matrix should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            fleiss_kappa([])

    def test_single_category_raises(self):
        """Single category should raise ValueError."""
        with pytest.raises(ValueError, match="At least 2 categories"):
            fleiss_kappa([[5], [3]])

    def test_single_rater_raises(self):
        """Single rater should raise ValueError."""
        with pytest.raises(ValueError, match="At least 2 raters"):
            fleiss_kappa([[1, 0], [0, 1]])

    def test_inconsistent_raters_raises(self):
        """Inconsistent rater count should raise ValueError."""
        with pytest.raises(ValueError, match="Inconsistent rater counts"):
            fleiss_kappa([[3, 0], [2, 2]])

    def test_inconsistent_categories_raises(self):
        """Inconsistent category count should raise ValueError."""
        with pytest.raises(ValueError, match="Inconsistent category count"):
            fleiss_kappa([[3, 0, 0], [2, 1]])

    def test_negative_counts_raise(self):
        """Negative counts should raise ValueError."""
        with pytest.raises(ValueError, match="Negative count"):
            fleiss_kappa([[-1, 3], [2, 1]])

    def test_interpretation_scale(self):
        """Test the interpretation categories."""
        assert _get_interpretation(-0.1) == "Poor agreement"
        assert _get_interpretation(0.1) == "Slight agreement"
        assert _get_interpretation(0.3) == "Fair agreement"
        assert _get_interpretation(0.5) == "Moderate agreement"
        assert _get_interpretation(0.7) == "Substantial agreement"
        assert _get_interpretation(0.9) == "Almost perfect agreement"


def _get_interpretation(kappa):
    """Helper to get interpretation without calling full kappa."""
    from fleiss_kappa import _interpret_kappa
    return _interpret_kappa(kappa)


class TestCalculateMetrics:
    """Tests for the legacy calculate_metrics function."""

    def test_with_matrix(self):
        """Should delegate to fleiss_kappa when matrix is provided."""
        matrix = [[3, 0, 0]] * 4
        result = calculate_metrics(matrix=matrix)
        assert "kappa" in result
        assert result["kappa"] == 1.0

    def test_with_matrix_json_string(self):
        """Should parse JSON string matrix."""
        matrix = [[3, 0, 0]] * 4
        result = calculate_metrics(matrix=json.dumps(matrix))
        assert "kappa" in result

    def test_legacy_fallback(self):
        """Legacy numeric input should still work."""
        result = calculate_metrics(v1=12.0, v2=4.0)
        assert "score" in result
        assert "classification" in result


class TestProcessBatch:
    """Tests for batch CSV processing."""

    def test_batch_creates_output(self, tmp_path):
        """Batch processing should create output file."""
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text(
            "Patient,v1,v2\nPat_001,3,0\nPat_002,2,1\n",
            encoding="utf-8"
        )
        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()

    def test_batch_output_has_kappa(self, tmp_path):
        """Output CSV should contain kappa column."""
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text(
            "ID,c1,c2\nT1,3,0\nT2,1,2\n",
            encoding="utf-8"
        )
        process_batch(str(csv_in), str(csv_out))
        content = csv_out.read_text(encoding="utf-8")
        assert "kappa" in content

    def test_batch_missing_file_raises(self, tmp_path):
        """Should raise FileNotFoundError for missing input."""
        with pytest.raises(FileNotFoundError):
            process_batch(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))


class TestCLI:
    """Tests for CLI entry points."""

    def test_single_command(self):
        """CLI single command should work."""
        result = main(["single"])
        # main() doesn't return anything for single, just prints
        assert result is None

    def test_calc_command(self):
        """CLI calc command should compute kappa."""
        result = main(["calc", "[[3,0,0],[2,1,0]]"])
        assert result is None

    def test_batch_command_missing_input(self):
        """Batch with missing input should fail gracefully."""
        with pytest.raises((SystemExit, FileNotFoundError)):
            main(["batch", "-i", "nonexistent.csv"])
