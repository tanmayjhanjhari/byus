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

    def test_run_both_no_real_model_before_eod_is_none(self, mitigator, two_group_df):
        """
        Without a real model or df_with_pred, before EOD/AOD must be None.
        After EOD/AOD may come from simulation GBM (valid, not fabricated).
        """
        result = mitigator.run_both(two_group_df, "Outcome", "Group")
        # Before EOD/AOD: None (no real model predictions provided)
        assert result["reweigh"]["before"]["EOD"] is None, \
            "Before EOD should be None without real model predictions"
        assert result["reweigh"]["before"]["AOD"] is None, \
            "Before AOD should be None without real model predictions"
        assert result["threshold"]["before"]["EOD"] is None, \
            "Threshold before EOD should be None without real model predictions"
        # After EOD/AOD: from simulation — valid if in range
        for key in ["reweigh", "threshold"]:
            eod_after = result[key]["after"].get("EOD")
            if eod_after is not None:
                assert -1.0 <= eod_after <= 1.0, f"{key} after EOD out of range"


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

    def test_threshold_simulation_eod_aod_available_flag_matches_value(
        self, mitigator, two_group_df
    ):
        """
        eod_available flag should match whether EOD is actually non-None.
        (Simulation may compute real EOD from its own predictions.)
        """
        r = mitigator.threshold_adjust(two_group_df, "Outcome", "Group")
        after = r["after"]
        eod_val = after.get("EOD")
        eod_flag = after.get("eod_available")
        assert (eod_val is None) == (not eod_flag), \
            f"eod_available flag ({eod_flag}) does not match EOD value ({eod_val})"
        aod_val = after.get("AOD")
        aod_flag = after.get("aod_available")
        assert (aod_val is None) == (not aod_flag), \
            f"aod_available flag ({aod_flag}) does not match AOD value ({aod_val})"

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

# ─────────────────────────────────────────────────────────────────────────────
# 8. Real model integration (predict_proba path)
# ─────────────────────────────────────────────────────────────────────────────

class TestRealModelIntegration:
    """
    Verify that when a real sklearn model (with predict_proba) is supplied,
    threshold adjustment uses it (is_simulation=False) and EOD/AOD become real.

    Generic: uses a synthetic LogisticRegression -- NOT credit-risk specific.
    """

    @pytest.fixture
    def model_and_df(self):
        """
        Train a generic LogisticRegression on the two_group_df fixture.
        Returns (model, df_with_pred, df_raw).
        """
        from sklearn.linear_model import LogisticRegression
        np.random.seed(42)
        n = 400
        df = pd.DataFrame({
            "Group":    ["A"] * 200 + ["B"] * 200,
            "Feature1": np.random.randn(n),
            "Feature2": np.random.randn(n),
            "Outcome":  np.array([1]*160 + [0]*40 + [1]*80 + [0]*120),
        })
        X = df[["Feature1", "Feature2"]].values
        y = df["Outcome"].values
        model = LogisticRegression(random_state=42)
        model.fit(X, y)
        # Mimic what analyze router does
        df_with_pred = df.copy()
        df_with_pred["__predictions__"] = model.predict(X)
        return model, df_with_pred, df

    def test_threshold_uses_real_model_when_available(self, mitigator, model_and_df):
        """Threshold adjustment should use real model when predict_proba available."""
        model, df_with_pred, df = model_and_df
        result = mitigator.threshold_adjust(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=model,
            df_with_pred=df_with_pred,
        )
        assert result.get("is_simulation") == False, (
            f"Expected is_simulation=False when real model has predict_proba, "
            f"got {result.get('is_simulation')}"
        )
        assert result.get("simulation_note") is None, (
            "Real model path should not have a simulation_note"
        )

    def test_threshold_real_model_eod_aod_available(self, mitigator, model_and_df):
        """After threshold with real model, EOD/AOD should be real (not None)."""
        model, df_with_pred, df = model_and_df
        result = mitigator.threshold_adjust(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=model,
            df_with_pred=df_with_pred,
        )
        after = result["after"]
        assert after.get("eod_available") == True, (
            f"Expected eod_available=True from real model, got {after.get('eod_available')}"
        )
        assert after["EOD"] is not None, "EOD should be a real value, not None"
        assert after["AOD"] is not None, "AOD should be a real value, not None"
        # Values must be in [-1, 1]
        assert -1.0 <= after["EOD"] <= 1.0, f"EOD out of range: {after['EOD']}"
        assert -1.0 <= after["AOD"] <= 1.0, f"AOD out of range: {after['AOD']}"

    def test_before_eod_aod_real_when_df_with_pred_provided(self, mitigator, model_and_df):
        """Before EOD/AOD should be real when df_with_pred is supplied."""
        model, df_with_pred, df = model_and_df
        result = mitigator.reweigh(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=model,
            df_with_pred=df_with_pred,
        )
        before = result["before"]
        assert before["EOD"] is not None, (
            "Before EOD should be real when df_with_pred is provided"
        )
        assert before["AOD"] is not None, (
            "Before AOD should be real when df_with_pred is provided"
        )
        assert before.get("eod_available") == True

    def test_run_both_with_real_model_no_crash(self, mitigator, model_and_df):
        """run_both with real model should complete without error."""
        model, df_with_pred, df = model_and_df
        result = mitigator.run_both(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=model,
            df_with_pred=df_with_pred,
        )
        assert "reweigh" in result
        assert "threshold" in result
        assert result["winner"] in ("reweigh", "threshold")
        assert result["model_info"]["real_model_used"] == True

    def test_threshold_no_model_falls_back_to_simulation(self, mitigator, model_and_df):
        """When no model is supplied, threshold adjustment uses simulation."""
        _, _, df = model_and_df
        result = mitigator.threshold_adjust(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
        )
        assert result.get("is_simulation") == True, (
            "Without real model, threshold should be simulation"
        )

    def test_model_without_predict_proba_falls_back_to_simulation(self, mitigator, model_and_df):
        """Model without predict_proba should fall back to GBM simulation."""
        from unittest.mock import MagicMock
        _, _, df = model_and_df
        # Create a mock model with predict but no predict_proba
        mock_model = MagicMock()
        del mock_model.predict_proba  # Remove predict_proba
        mock_model.predict = MagicMock(return_value=np.zeros(len(df), dtype=int))

        result = mitigator.threshold_adjust(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=mock_model,
        )
        assert result.get("is_simulation") == True, (
            "Model without predict_proba should fall back to simulation"
        )

    def test_real_model_performance_metrics_not_simulation_labelled(
        self, mitigator, model_and_df
    ):
        """Performance metrics from real model path should NOT have simulation_note."""
        model, df_with_pred, df = model_and_df
        result = mitigator.threshold_adjust(
            df=df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=model,
            df_with_pred=df_with_pred,
        )
        after = result["after"]
        assert after.get("simulation_note") is None, (
            f"Real model path should not have simulation_note in after metrics; "
            f"got: {after.get('simulation_note')}"
        )
        # Should have real performance metrics
        for metric in ["accuracy", "precision", "recall", "f1"]:
            assert metric in after, f"Real model path missing {metric}"
            assert 0.0 <= after[metric] <= 1.0, f"{metric} out of range"

    def test_generic_attributes_work_not_just_age_gender(self, mitigator):
        """Engine must work with any sensitive attribute name — not just age/gender."""
        np.random.seed(0)
        n = 300
        df = pd.DataFrame({
            "region":      (["North"] * 150 + ["South"] * 150),
            "score":       np.random.randn(n),
            "loan_amount": np.random.randint(1000, 50000, n),
            "approved":    np.array([1]*110 + [0]*40 + [1]*70 + [0]*80),
        })
        result = mitigator.run_both(
            df=df,
            target_col="approved",
            sensitive_attr="region",
        )
        assert "reweigh" in result
        assert "threshold" in result
        assert result["winner"] in ("reweigh", "threshold")
        # SPD should be in valid range regardless of attribute name
        spd = result["reweigh"]["before"]["SPD"]
        assert -1.0 <= spd <= 1.0, f"SPD out of range for generic attr: {spd}"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Targeted Real Model Audit Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTargetedRealModelAudit:
    """Targeted validation for the real-model mitigation path and no-silent-fallback."""

    @pytest.fixture
    def real_files_exist(self):
        import os
        csv_p = r"E:\Codes\fairenough\credit_risk_v2.csv"
        pkl_p = r"E:\Codes\fairenough\credit_risk_v2_model.pkl"
        return os.path.exists(csv_p) and os.path.exists(pkl_p), csv_p, pkl_p

    def test_1_real_model_loads_successfully(self, real_files_exist):
        exists, _, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        model = joblib.load(pkl_p)
        assert callable(getattr(model, "predict", None)), "Model must have predict method"
        assert callable(getattr(model, "predict_proba", None)), "Model must have predict_proba method"
        raw_f = getattr(model, "feature_names_in_", None)
        assert raw_f is not None, "Model must have feature_names_in_"

    def test_2_feature_preparation_succeeds(self, mitigator, real_files_exist):
        exists, csv_p, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        df = pd.read_csv(csv_p)
        model = joblib.load(pkl_p)
        X = mitigator._prepare_features_for_model(df, model, "credit_risk", "gender")
        assert X is not None, "Feature preparation must succeed"
        assert len(X) == len(df), "Prepared features length must match dataset rows"

    def test_3_real_model_generates_predictions(self, mitigator, real_files_exist):
        exists, csv_p, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        df = pd.read_csv(csv_p)
        model = joblib.load(pkl_p)
        if hasattr(model, "predict_proba") and not hasattr(model, "multi_class") and "LogisticRegression" in type(model).__name__:
            setattr(model, "multi_class", "auto")
        X = mitigator._prepare_features_for_model(df, model, "credit_risk", "gender")
        proba = model.predict_proba(X)
        assert proba.shape == (len(df), 2), f"Expected shape ({len(df)}, 2), got {proba.shape}"
        assert 0.0 <= proba[:, 1].min() <= proba[:, 1].max() <= 1.0, "Probabilities must be in [0, 1]"

    def test_4_threshold_adjustment_uses_real_model_probabilities(self, mitigator, real_files_exist):
        exists, csv_p, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        df = pd.read_csv(csv_p)
        model = joblib.load(pkl_p)
        result = mitigator.threshold_adjust(
            df=df,
            target_col="credit_risk",
            sensitive_attr="gender",
            model=model,
        )
        assert result.get("is_simulation") is False, "Must use real model, not simulation"
        assert result.get("simulation_note") is None, "Real model path must not have simulation_note"
        assert "thresholds" in result, "Result must contain computed thresholds"
        for grp, thresh in result["thresholds"].items():
            assert 0.1 <= thresh <= 0.9, f"Threshold for {grp} out of range: {thresh}"

    def test_5_real_eod_aod_are_calculated(self, mitigator, real_files_exist):
        exists, csv_p, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        df = pd.read_csv(csv_p)
        model = joblib.load(pkl_p)
        result = mitigator.threshold_adjust(
            df=df,
            target_col="credit_risk",
            sensitive_attr="gender",
            model=model,
        )
        after = result["after"]
        assert after.get("eod_available") is True, "EOD must be marked available"
        assert after.get("aod_available") is True, "AOD must be marked available"
        assert after["EOD"] is not None, "EOD value must not be None"
        assert after["AOD"] is not None, "AOD value must not be None"
        assert -1.0 <= after["EOD"] <= 1.0, f"EOD out of range: {after['EOD']}"
        assert -1.0 <= after["AOD"] <= 1.0, f"AOD out of range: {after['AOD']}"

    def test_6_real_performance_metrics_calculated(self, mitigator, real_files_exist):
        exists, csv_p, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        df = pd.read_csv(csv_p)
        model = joblib.load(pkl_p)
        result = mitigator.threshold_adjust(
            df=df,
            target_col="credit_risk",
            sensitive_attr="gender",
            model=model,
        )
        after = result["after"]
        for m in ["accuracy", "precision", "recall", "f1"]:
            assert m in after, f"Missing metric {m}"
            assert after[m] is not None, f"Metric {m} must not be None"
            assert 0.0 <= after[m] <= 1.0, f"Metric {m} out of range: {after[m]}"

    def test_7_real_model_failure_does_not_silently_trigger_simulation(self, mitigator, two_group_df):
        """When a real model errors, it must report failure, NOT silently run GBM simulation."""
        from unittest.mock import MagicMock
        broken_model = MagicMock()
        broken_model.predict_proba.side_effect = RuntimeError("Custom model internal crash")
        broken_model.feature_names_in_ = np.array(["Col1", "Col2"])

        result = mitigator.threshold_adjust(
            df=two_group_df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=broken_model,
        )
        assert result.get("is_simulation") is False, "Must NOT fall back to simulation when real model fails"
        assert "error" in result or "error" in result["after"], "Must return explicit error state"
        assert result["after"]["metrics_mode"] == "unavailable", "Metrics mode must be unavailable"
        assert result["after"]["SPD"] is None, "Failed model must not fabricate SPD"

    def test_8_simulation_works_only_when_explicitly_no_model(self, mitigator, two_group_df):
        """Simulation should run cleanly when no model is provided."""
        result = mitigator.threshold_adjust(
            df=two_group_df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=None,
        )
        assert result.get("is_simulation") is True, "Without a model, is_simulation must be True"
        assert result.get("simulation_note") is not None, "Simulation must carry a disclosure note"

    def test_9_reweighing_does_not_fabricate_performance(self, mitigator, two_group_df):
        """Reweighing post-mitigation must not invent model performance metrics."""
        result = mitigator.reweigh(
            df=two_group_df,
            target_col="Outcome",
            sensitive_attr="Group",
            model=None,
        )
        after = result["after"]
        assert after["accuracy"] is None, "Reweighing after accuracy should be None without retrained model"
        assert after["f1"] is None, "Reweighing after f1 should be None without retrained model"
        assert after["EOD"] is None, "Reweighing after EOD must be None"
        assert after["AOD"] is None, "Reweighing after AOD must be None"
        assert result.get("is_simulation") is False, "Dataset reweighing is real dataset reweighting"

    def test_10_generic_model_data_inputs_remain_supported(self, mitigator):
        """Engine supports arbitrary domain columns and models without hardcoded assumptions."""
        from sklearn.ensemble import RandomForestClassifier
        n = 200
        df = pd.DataFrame({
            "hospital_site": ["SiteA"] * 100 + ["SiteB"] * 100,
            "biomarker_a": np.random.randn(n),
            "biomarker_b": np.random.randn(n),
            "readmitted": np.array([1]*80 + [0]*20 + [1]*40 + [0]*60),
        })
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        X_tr = df[["biomarker_a", "biomarker_b"]].values
        y_tr = df["readmitted"].values
        clf.fit(X_tr, y_tr)

        result = mitigator.run_both(
            df=df,
            target_col="readmitted",
            sensitive_attr="hospital_site",
            model=clf,
        )
        assert result["threshold"]["is_simulation"] is False, "Must use real RandomForestClassifier"
        assert result["threshold"]["after"]["eod_available"] is True
        assert result["winner"] in ("reweigh", "threshold")


class TestPrincipledThresholdAdjustment:
    """
    Unit and integration tests for principled, data-adaptive threshold adjustment:
    1. Prevents all-positive collapse
    2. Prevents all-negative collapse
    3. Narrow probability distributions
    4. Highly imbalanced datasets
    5. Different sensitive group counts (multi-group)
    6. Different score distributions (bimodal, skewed beta)
    7. Real model threshold adjustment avoids collapse
    8. Fairness/performance trade-off selection
    9. Generic datasets and models
    """

    @pytest.fixture
    def real_files_exist(self):
        import os
        csv_p = r"E:\Codes\fairenough\credit_risk_v2.csv"
        pkl_p = r"E:\Codes\fairenough\credit_risk_v2_model.pkl"
        return os.path.exists(csv_p) and os.path.exists(pkl_p), csv_p, pkl_p

    def test_prevents_all_positive_collapse(self, mitigator):
        """When scores are high [0.65, 0.95], candidate selection and non-degeneracy prevent all-positive collapse."""
        np.random.seed(42)
        n = 200
        # Scores shifted high (all > 0.65)
        scores = np.random.uniform(0.65, 0.95, size=n)
        s = np.random.choice([0, 1], size=n)
        groups = np.unique(s)
        y_true = (scores > 0.80).astype(int)

        best_threshs, best_spd = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true
        )

        y_pred = np.zeros(n, dtype=int)
        for g, t in best_threshs.items():
            y_pred[s == g] = (scores[s == g] >= t).astype(int)

        # Must NOT collapse to 100% positive
        assert y_pred.mean() < 1.0, "Predictions must not collapse to 100% positive"
        assert (y_pred == 0).sum() > 0, "Must produce negative predictions"
        for g in groups:
            assert float(best_threshs[g]) > float(scores.min()), (
                f"Threshold {best_threshs[g]} must be above min score {scores.min()} to avoid collapse"
            )

    def test_prevents_all_negative_collapse(self, mitigator):
        """When scores are low [0.05, 0.35], candidate selection and non-degeneracy prevent all-negative collapse."""
        np.random.seed(42)
        n = 200
        # Scores shifted low (all < 0.35)
        scores = np.random.uniform(0.05, 0.35, size=n)
        s = np.random.choice([0, 1], size=n)
        groups = np.unique(s)
        y_true = (scores > 0.20).astype(int)

        best_threshs, best_spd = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true
        )

        y_pred = np.zeros(n, dtype=int)
        for g, t in best_threshs.items():
            y_pred[s == g] = (scores[s == g] >= t).astype(int)

        # Must NOT collapse to 0% positive
        assert y_pred.mean() > 0.0, "Predictions must not collapse to 0% positive"
        assert (y_pred == 1).sum() > 0, "Must produce positive predictions"
        for g in groups:
            assert float(best_threshs[g]) < float(scores.max()), (
                f"Threshold {best_threshs[g]} must be below max score {scores.max()} to avoid collapse"
            )

    def test_narrow_probability_distribution(self, mitigator):
        """When scores occupy a narrow band [0.510, 0.530], candidates are derived from score support."""
        np.random.seed(42)
        n = 300
        # Narrow score range: min=0.510, max=0.530
        scores = np.random.uniform(0.510, 0.530, size=n)
        s = np.random.choice([0, 1], size=n)
        groups = np.unique(s)
        y_true = (scores > 0.520).astype(int)

        best_threshs, best_spd = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true
        )

        for g, t in best_threshs.items():
            assert 0.510 <= t <= 0.530, f"Threshold {t} must fall within narrow score band [0.510, 0.530]"

        y_pred = np.zeros(n, dtype=int)
        for g, t in best_threshs.items():
            y_pred[s == g] = (scores[s == g] >= t).astype(int)

        assert 0.05 <= y_pred.mean() <= 0.95, "Narrow distribution must produce balanced predictions"

    def test_imbalanced_dataset(self, mitigator):
        """Optimizer adapts non-degeneracy constraints and avoids collapse on heavily skewed data."""
        np.random.seed(42)
        n = 500
        # 3% positive base rate
        y_true = np.zeros(n, dtype=int)
        y_true[:15] = 1
        np.random.shuffle(y_true)
        scores = np.random.beta(1, 20, size=n)
        s = np.random.choice([0, 1], size=n)
        groups = np.unique(s)

        best_threshs, best_spd = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true, min_samples_per_class=1
        )

        y_pred = np.zeros(n, dtype=int)
        for g, t in best_threshs.items():
            y_pred[s == g] = (scores[s == g] >= t).astype(int)

        assert (y_pred == 1).sum() >= 1, "Must predict at least 1 positive"
        assert (y_pred == 0).sum() >= 1, "Must predict at least 1 negative"

    def test_different_sensitive_group_counts(self, mitigator):
        """Optimizer handles multi-group attributes (3 and 4 groups) using coordinate descent."""
        np.random.seed(42)
        n = 400
        scores = np.random.uniform(0.2, 0.8, size=n)
        # 4 sensitive groups
        s = np.random.choice([0, 1, 2, 3], size=n)
        groups = np.unique(s)
        y_true = (scores > 0.5).astype(int)

        best_threshs, best_spd = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true
        )

        assert len(best_threshs) == 4, f"Expected 4 thresholds, got {len(best_threshs)}"
        for g in groups:
            assert g in best_threshs, f"Missing threshold for group {g}"
            assert 0.2 <= best_threshs[g] <= 0.8

    def test_different_score_distributions(self, mitigator):
        """Optimizer handles bimodal score distributions seamlessly."""
        np.random.seed(42)
        n = 400
        # Bimodal scores: mix of two normals
        scores_mode1 = np.random.normal(0.3, 0.05, size=n // 2)
        scores_mode2 = np.random.normal(0.7, 0.05, size=n // 2)
        scores = np.clip(np.concatenate([scores_mode1, scores_mode2]), 0.01, 0.99)
        s = np.random.choice([0, 1], size=n)
        groups = np.unique(s)
        y_true = (scores > 0.5).astype(int)

        best_threshs, best_spd = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true
        )
        assert best_spd < 0.10, f"Expected low SPD on symmetric distribution, got {best_spd}"

    def test_real_model_threshold_adjustment_avoids_collapse(self, mitigator, real_files_exist):
        """Real credit_risk_v2 model thresholds avoid 0.2 degenerate collapse and preserve both classes."""
        exists, csv_p, pkl_p = real_files_exist
        if not exists:
            pytest.skip("credit_risk_v2 files not found in repo")
        import joblib
        df = pd.read_csv(csv_p)
        model = joblib.load(pkl_p)

        result = mitigator.threshold_adjust(
            df=df,
            target_col="credit_risk",
            sensitive_attr="gender",
            model=model,
        )
        after = result["after"]
        # Thresholds must NOT be 0.2 (which causes all-positive collapse)
        for grp, t in result["thresholds"].items():
            assert t > 0.50, f"Threshold for {grp} ({t}) must be > 0.50 within actual score support [0.52, 0.71]"

        # Group positive rates must be strictly < 1.0 (not all-positive)
        assert after["positive_prediction_rate"] < 1.0, "Overall positive prediction rate must be < 1.0"
        for grp, stats in after["group_stats"].items():
            assert stats["positive_rate"] < 1.0, f"Group {grp} positive rate must be < 1.0"

        # Model performance metrics must be valid real calculations
        assert 0.50 <= after["accuracy"] <= 0.85, f"Unexpected accuracy: {after['accuracy']}"
        assert 0.50 <= after["precision"] <= 0.85, f"Unexpected precision: {after['precision']}"
        assert 0.50 <= after["recall"] <= 1.0, f"Unexpected recall: {after['recall']}"
        assert 0.50 <= after["f1"] <= 0.90, f"Unexpected f1: {after['f1']}"

    def test_fairness_performance_tradeoff(self, mitigator):
        """Optimizer penalizes utility loss and will not accept zero disparity if utility is destroyed."""
        np.random.seed(42)
        n = 200
        scores = np.random.uniform(0.1, 0.9, size=n)
        s = np.random.choice([0, 1], size=n)
        groups = np.unique(s)
        # Ground truth strongly correlated with scores
        y_true = (scores > 0.5).astype(int)

        # Optimize with utility consideration
        threshs_with_u, spd_with_u = mitigator._optimise_thresholds(
            scores=scores, s=s, groups=groups, y_true=y_true, utility_weight=1.0
        )

        y_pred = np.zeros(n, dtype=int)
        for g, t in threshs_with_u.items():
            y_pred[s == g] = (scores[s == g] >= t).astype(int)

        from sklearn.metrics import accuracy_score
        acc = accuracy_score(y_true, y_pred)
        assert acc >= 0.75, f"Expected high utility preserved, got accuracy {acc}"

    def test_generic_datasets_and_models(self, mitigator):
        """Threshold adjustment operates generically on arbitrary domains, features, and model types."""
        from sklearn.ensemble import GradientBoostingClassifier
        np.random.seed(42)
        n = 250
        df_generic = pd.DataFrame({
            "client_tier": np.random.choice(["Tier1", "Tier2", "Tier3"], size=n),
            "engagement_score": np.random.exponential(scale=10.0, size=n),
            "tenure_months": np.random.randint(1, 60, size=n),
            "renewed": np.random.choice([0, 1], size=n, p=[0.4, 0.6]),
        })

        clf = GradientBoostingClassifier(n_estimators=15, random_state=42)
        X = df_generic[["engagement_score", "tenure_months"]].values
        y = df_generic["renewed"].values
        clf.fit(X, y)

        res = mitigator.threshold_adjust(
            df=df_generic,
            target_col="renewed",
            sensitive_attr="client_tier",
            model=clf,
        )
        assert res["is_simulation"] is False, "Must use real GradientBoostingClassifier"
        assert res["after"]["metrics_mode"] == "model_level"
        assert res["after"]["eod_available"] is True
        assert len(res["thresholds"]) == 3
