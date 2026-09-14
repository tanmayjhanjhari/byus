"""
FairEnough - Mitigation Correctness Tests

Tests that verify:
1. Reweighing uses the same baseline as BiasEngine (no SPD=1.000 / DI=0.000)
2. Age binning is applied in mitigator (same as BiasEngine)
3. EOD and AOD are None in all mitigation output
4. Reweighing "before" = baseline (not model prediction rates)
5. Reweighing "after" = dataset-level (from weighted positive rates)
6. Threshold "after" is labelled is_simulation=True
7. Performance metrics (Acc/Precision/Recall/F1) come from simulation
8. Recommendation uses only SPD (not fake EOD/AOD)
9. Baseline SPD/DI can be overridden by caller (router passing analysis baseline)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import pytest

from services.mitigator import BiasMitigator
from services.bias_engine import BiasEngine


@pytest.fixture
def mitigator():
    return BiasMitigator()


@pytest.fixture
def engine():
    return BiasEngine()


@pytest.fixture
def pima_like_df():
    """Synthetic Pima-like dataset with known bias (Age-based)."""
    np.random.seed(42)
    n = 500
    ages = np.random.randint(21, 70, n)
    # Younger (<50) has 45% positive rate, older (>=50) has 30%
    outcome = np.where(ages < 50,
                       np.random.binomial(1, 0.45, n),
                       np.random.binomial(1, 0.30, n))
    return pd.DataFrame({
        "Age": ages,
        "Pregnancies": np.random.randint(0, 12, n),
        "Glucose": np.random.randint(70, 200, n),
        "BMI": np.random.uniform(18, 50, n).round(1),
        "Outcome": outcome,
    })


@pytest.fixture
def two_group_df():
    """Simple binary group dataset for controlled tests."""
    return pd.DataFrame({
        "Group": ["A"] * 200 + ["B"] * 200,
        "Feature1": np.random.randn(400),
        "Feature2": np.random.randn(400),
        "Outcome": np.array([1]*160 + [0]*40 + [1]*80 + [0]*120),  # A=0.8, B=0.4
    })


# ─────────────────────────────────────────────────────────────────────────────
# 1. EOD and AOD must ALWAYS be None in mitigation output
# ─────────────────────────────────────────────────────────────────────────────

class TestMitigationEODAOD:

    def test_reweigh_before_eod_is_none(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r["before"]["EOD"] is None,             f"Reweighing before EOD should be None, got {r['before']['EOD']}"

    def test_reweigh_before_aod_is_none(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r["before"]["AOD"] is None,             f"Reweighing before AOD should be None, got {r['before']['AOD']}"

    def test_reweigh_after_eod_is_none(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r["after"]["EOD"] is None,             f"Reweighing after EOD should be None, got {r['after']['EOD']}"

    def test_reweigh_after_aod_is_none(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r["after"]["AOD"] is None,             f"Reweighing after AOD should be None, got {r['after']['AOD']}"

    def test_threshold_before_eod_is_none(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert r["before"]["EOD"] is None,             f"Threshold before EOD should be None, got {r['before']['EOD']}"

    def test_threshold_after_eod_is_none(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert r["after"]["EOD"] is None,             f"Threshold after EOD should be None, got {r['after']['EOD']}"

    def test_run_both_no_eod_aod(self, mitigator, two_group_df):
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        assert result["reweigh"]["before"]["EOD"] is None
        assert result["reweigh"]["after"]["EOD"] is None
        assert result["threshold"]["before"]["EOD"] is None
        assert result["threshold"]["after"]["EOD"] is None
        assert result["reweigh"]["after"]["AOD"] is None
        assert result["threshold"]["after"]["AOD"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Age binning applied in mitigator (should NOT produce SPD=1.0, DI=0.0)
# ─────────────────────────────────────────────────────────────────────────────

class TestMitigatorAgeBinning:

    def test_age_not_producing_extreme_spd(self, mitigator, pima_like_df):
        """Extreme SPD=1.0 and DI=0.0 are signs of unbinned Age groups."""
        result = mitigator.reweigh(pima_like_df, "Outcome", "Age")
        before_spd = result["before"]["SPD"]
        before_di  = result["before"]["DI"]

        assert abs(before_spd) < 0.9,             f"SPD=1.0 indicates Age not binned (got {before_spd}). "             f"Unbinned Age creates 49 tiny groups."
        assert before_di is None or before_di > 0.05,             f"DI=0.0 indicates Age not binned (got {before_di})."

    def test_age_binning_produces_only_two_groups(self, mitigator, pima_like_df):
        """The group_stats before should have exactly 2 groups for Age."""
        result = mitigator.reweigh(pima_like_df, "Outcome", "Age")
        group_stats = result["before"].get("group_stats", {})
        # With baseline not provided, fallback computes from binned data
        # So should be 2 groups
        if group_stats:
            assert len(group_stats) <= 2,                 f"Expected <=2 Age groups, got {len(group_stats)}: {list(group_stats.keys())}"

    def test_binning_threshold_matches_bias_engine(self, mitigator):
        """Mitigator and BiasEngine must use the same binning threshold."""
        from services.bias_engine import BiasEngine
        engine = BiasEngine()
        assert mitigator.CARDINALITY_BIN_THRESHOLD == engine.CARDINALITY_BIN_THRESHOLD,             "Mitigator and BiasEngine CARDINALITY_BIN_THRESHOLD must match"
        assert mitigator.CONTINUOUS_BIN_THRESHOLD == engine.CONTINUOUS_BIN_THRESHOLD,             "Mitigator and BiasEngine CONTINUOUS_BIN_THRESHOLD must match"
        assert mitigator.CONTINUOUS_BIN_LABELS == engine.CONTINUOUS_BIN_LABELS,             "Mitigator and BiasEngine CONTINUOUS_BIN_LABELS must match"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Baseline SPD/DI consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestBaselineConsistency:

    def test_reweigh_before_matches_provided_baseline(self, mitigator, two_group_df):
        """When baseline_spd and baseline_di are provided, 'before' must use them."""
        expected_spd = -0.152
        expected_di  = 0.686
        result = mitigator.reweigh(
            two_group_df, "Outcome", "Group",
            baseline_spd=expected_spd,
            baseline_di=expected_di,
        )
        assert abs(result["before"]["SPD"] - expected_spd) < 1e-6,             f"Reweighing 'before' SPD should be {expected_spd}, got {result['before']['SPD']}"
        assert abs(result["before"]["DI"] - expected_di) < 1e-6,             f"Reweighing 'before' DI should be {expected_di}, got {result['before']['DI']}"

    def test_threshold_before_matches_provided_baseline(self, mitigator, two_group_df):
        """Threshold adjustment 'before' must use the same baseline as reweighing."""
        expected_spd = -0.152
        expected_di  = 0.686
        result = mitigator.threshold_adjust(
            two_group_df, "Outcome", "Group",
            baseline_spd=expected_spd,
            baseline_di=expected_di,
        )
        assert abs(result["before"]["SPD"] - expected_spd) < 1e-6,             f"Threshold 'before' SPD should be {expected_spd}, got {result['before']['SPD']}"

    def test_run_both_reweigh_and_threshold_same_before(self, mitigator, two_group_df):
        """In run_both, reweigh and threshold must have the same 'before' values."""
        baseline_spd = -0.2
        baseline_di  = 0.75
        result = mitigator.run_both(
            two_group_df, "Outcome", "Group",
            baseline_spd=baseline_spd,
            baseline_di=baseline_di,
        )
        rew_spd = result["reweigh"]["before"]["SPD"]
        thr_spd = result["threshold"]["before"]["SPD"]
        assert abs(rew_spd - thr_spd) < 1e-6,             f"Reweighing and threshold 'before' SPD must match: {rew_spd} vs {thr_spd}"

    def test_without_baseline_spd_not_extreme(self, mitigator, two_group_df):
        """Without baseline, computed SPD should match actual data (not 1.0 or 0.0)."""
        result = mitigator.reweigh(two_group_df, "Outcome", "Group")
        spd = result["before"]["SPD"]
        # A=0.8, B=0.4 → SPD = 0.4 - 0.8 = -0.4 (approx)
        assert -0.6 < spd < 0,             f"Expected SPD around -0.4, got {spd}. SPD=1.0 means unbinned groups."

    def test_reweigh_after_spd_consistent_units(self, mitigator, two_group_df):
        """Reweighing after SPD should be in the same direction/scale as before."""
        result = mitigator.reweigh(two_group_df, "Outcome", "Group")
        before_spd = result["before"]["SPD"]
        after_spd  = result["after"]["SPD"]
        # Both should be in range [-1, 1] and after should be closer to 0
        assert -1.0 <= before_spd <= 0.0, f"Before SPD out of expected range: {before_spd}"
        assert abs(after_spd) <= abs(before_spd) + 0.05,             f"Reweighing should reduce or maintain SPD magnitude: before={before_spd}, after={after_spd}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Reweighing: dataset-level before/after
# ─────────────────────────────────────────────────────────────────────────────

class TestReweighDatasetLevel:

    def test_reweigh_before_metrics_mode(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r["before"]["metrics_mode"] == "dataset_level"

    def test_reweigh_after_metrics_mode(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r["after"]["metrics_mode"] == "dataset_level_reweighted"

    def test_reweigh_is_not_simulation(self, mitigator, two_group_df):
        """Reweighing SPD/DI are real dataset metrics — is_simulation must be False."""
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert r.get("is_simulation") == False,             f"Reweighing is_simulation should be False, got {r.get('is_simulation')}"

    def test_reweigh_spd_di_in_valid_range(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        spd = r["after"]["SPD"]
        di  = r["after"]["DI"]
        assert -1.0 <= spd <= 1.0, f"After SPD out of range: {spd}"
        assert di is None or (0.0 <= di <= 2.0), f"After DI out of range: {di}"

    def test_reweigh_weights_summary_present(self, mitigator, two_group_df):
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        assert "weights_summary" in r
        ws = r["weights_summary"]
        assert "min" in ws and "max" in ws and "mean" in ws
        assert ws["min"] >= 0.09, f"Min weight too small: {ws['min']}"
        assert ws["max"] <= 10.1, f"Max weight too large: {ws['max']}"

    def test_reweigh_performance_metrics_from_simulation(self, mitigator, two_group_df):
        """Performance metrics present but labelled as simulation."""
        r = mitigator.reweigh(two_group_df, "Outcome", "Group")
        before = r["before"]
        after  = r["after"]
        # Should have simulation note
        assert "simulation_note" in before or "simulation_note" in after
        # Accuracy should be in valid range if present
        if "accuracy" in before:
            assert 0.0 <= before["accuracy"] <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Threshold adjustment: simulation labelling
# ─────────────────────────────────────────────────────────────────────────────

class TestThresholdSimulationLabelling:

    def test_threshold_is_simulation(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert r.get("is_simulation") == True,             f"Threshold is_simulation should be True, got {r.get('is_simulation')}"

    def test_threshold_after_metrics_mode(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert r["after"]["metrics_mode"] == "simulation"

    def test_threshold_has_simulation_note(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert "simulation_note" in r or "simulation_note" in r["after"],             "Threshold adjustment must have a simulation_note"

    def test_threshold_eod_available_flag_is_false(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert r["after"].get("eod_available") == False
        assert r["after"].get("aod_available") == False

    def test_threshold_thresholds_dict_present(self, mitigator, two_group_df):
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        assert "thresholds" in r
        thresholds = r["thresholds"]
        assert len(thresholds) >= 1
        for t in thresholds.values():
            assert 0.1 <= float(t) <= 0.9, f"Threshold out of range: {t}"


# ─────────────────────────────────────────────────────────────────────────────
# 6. run_both output structure
# ─────────────────────────────────────────────────────────────────────────────

class TestRunBothOutput:

    def test_run_both_winner_is_valid(self, mitigator, two_group_df):
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        assert result["winner"] in ("reweigh", "threshold"),             f"winner must be 'reweigh' or 'threshold', got {result['winner']}"

    def test_run_both_winner_reason_is_string(self, mitigator, two_group_df):
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        assert isinstance(result["winner_reason"], str)
        assert len(result["winner_reason"]) > 10

    def test_run_both_no_fake_eod_in_winner_reason(self, mitigator, two_group_df):
        """Winner reason should not reference EOD/AOD as measured metrics."""
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        reason = result["winner_reason"].lower()
        # Should not claim EOD/AOD improvement
        bad_phrases = ["eod improved", "aod improved", "equal opportunity achieved"]
        for phrase in bad_phrases:
            assert phrase not in reason,                 f"Winner reason should not claim '{phrase}' without real measurements"

    def test_run_both_has_model_info(self, mitigator, two_group_df):
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        assert "model_info" in result
        assert "note" in result["model_info"]

    def test_run_both_bias_reduction_from_spd_only(self, mitigator, two_group_df):
        """bias_reduction_pct must be computed from SPD, not from EOD/AOD."""
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        rew = result["reweigh"]
        spd_b = abs(rew["before"]["SPD"] or 0)
        spd_a = abs(rew["after"]["SPD"] or 0)
        expected_reduction = round(((spd_b - spd_a) / max(spd_b, 1e-9)) * 100, 1) if spd_b > 0 else 0.0
        actual_reduction = rew["effects"]["bias_reduction_pct"]
        assert abs(actual_reduction - expected_reduction) < 0.2,             f"bias_reduction_pct should be {expected_reduction}, got {actual_reduction}"

    def test_run_both_effects_spd_delta_consistent(self, mitigator, two_group_df):
        """effects.spd_delta = after.SPD - before.SPD."""
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        rew = result["reweigh"]
        expected_delta = round((rew["after"]["SPD"] or 0) - (rew["before"]["SPD"] or 0), 4)
        assert abs(rew["effects"]["spd_delta"] - expected_delta) < 0.001,             f"spd_delta mismatch: expected {expected_delta}, got {rew['effects']['spd_delta']}"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Analysis-mitigation baseline consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalysisMitigationConsistency:

    def test_mitigation_before_matches_analysis_when_baseline_provided(
        self, mitigator, engine, two_group_df
    ):
        """When analysis result is passed as baseline, mitigation 'before' must match."""
        # Run analysis
        analysis = engine.analyze(two_group_df, "Outcome", ["Group"])
        attr_m = analysis["metrics_per_attr"]["Group"]
        analysis_spd = attr_m["spd"]
        analysis_di  = attr_m["di"]

        # Run mitigation with analysis baseline
        mit = mitigator.run_both(
            two_group_df, "Outcome", "Group",
            baseline_spd=analysis_spd,
            baseline_di=analysis_di,
        )

        rew_before_spd = mit["reweigh"]["before"]["SPD"]
        thr_before_spd = mit["threshold"]["before"]["SPD"]

        assert abs(rew_before_spd - analysis_spd) < 1e-5,             f"Reweighing before SPD ({rew_before_spd}) != analysis SPD ({analysis_spd})"
        assert abs(thr_before_spd - analysis_spd) < 1e-5,             f"Threshold before SPD ({thr_before_spd}) != analysis SPD ({analysis_spd})"

    def test_mitigation_before_consistent_sign_convention(self, mitigator, engine, two_group_df):
        """SPD sign convention: unpriv - priv = negative when unpriv has fewer positives."""
        analysis = engine.analyze(two_group_df, "Outcome", ["Group"])
        analysis_spd = analysis["metrics_per_attr"]["Group"]["spd"]

        mit = mitigator.run_both(
            two_group_df, "Outcome", "Group",
            baseline_spd=analysis_spd,
        )
        # A=0.8, B=0.4 → priv=A, unpriv=B → SPD = 0.4 - 0.8 = -0.4
        assert analysis_spd < 0, f"Expected negative SPD for A=0.8, B=0.4 scenario, got {analysis_spd}"
        assert mit["reweigh"]["before"]["SPD"] < 0,             f"Mitigation before SPD should be negative, got {mit['reweigh']['before']['SPD']}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
