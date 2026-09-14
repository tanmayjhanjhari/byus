"""
FairEnough - Bias Mitigator Service

ARCHITECTURE
============
Two mitigation strategies:
  1. Reweighing           - dataset-level (weights only, no model required)
  2. Threshold Adjustment - model-level simulation (GBM, labelled as simulation)

METRIC HONESTY POLICY
=====================
  - "Before" SPD/DI come from the BiasEngine analysis baseline (same values as
    the analysis page). They are NOT recomputed from model predictions here.

  - "After" Reweighing SPD/DI are computed from the REWEIGHTED dataset positive
    rates (dataset-level) -- not from model predictions.

  - "After" Threshold Adjustment SPD/DI are computed from simulation model
    predictions (clearly labelled is_simulation=True).

  - EOD and AOD are ALWAYS None. They require real external model predictions
    which do not exist in the dataset-only workflow.

  - Acc/Precision/Recall/F1 come from an internal GBM simulation model.
    Clearly labelled with simulation_note field.

  - Sensitive attribute binning mirrors BiasEngine exactly
    (CARDINALITY_BIN_THRESHOLD=10, CONTINUOUS_BIN_THRESHOLD=50.0).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


class BiasMitigator:
    """Honest bias mitigation - dataset-level metrics, simulation clearly labelled."""

    RANDOM_STATE: int = 42
    TEST_SIZE: float = 0.30

    # Must match BiasEngine constants exactly
    CARDINALITY_BIN_THRESHOLD: int = 10
    CONTINUOUS_BIN_THRESHOLD: float = 50.0
    CONTINUOUS_BIN_LABELS: tuple = ("Younger (<50)", "Older (>=50)")

    # ── Binning (mirrors BiasEngine._bin_continuous_attr) ─────────────────────

    def _apply_binning(self, series: pd.Series, attr: str) -> pd.Series:
        """
        Apply the same binning logic as BiasEngine._bin_continuous_attr.
        Numeric attrs with > CARDINALITY_BIN_THRESHOLD unique values are
        binned into two groups at CONTINUOUS_BIN_THRESHOLD.
        """
        if (pd.api.types.is_numeric_dtype(series)
                and series.nunique() > self.CARDINALITY_BIN_THRESHOLD):
            threshold = self.CONTINUOUS_BIN_THRESHOLD
            low_label, high_label = self.CONTINUOUS_BIN_LABELS
            return series.apply(
                lambda v: high_label if pd.notna(v) and float(v) >= threshold
                else low_label
            )
        return series.astype(str)

    # ── Dataset-level SPD/DI (identical formula to BiasEngine) ────────────────

    def _dataset_spd_di(
        self,
        df: pd.DataFrame,
        target_col: str,
        sens_col: str,
        weight_col: str | None = None,
    ) -> tuple:
        """
        Compute dataset-level SPD and DI from positive outcome rates.
        Optionally uses sample weights for computing weighted positive rates.

        SPD = positive_rate(unprivileged) - positive_rate(privileged)
              (negative = unprivileged group has FEWER positives, consistent with BiasEngine)
        DI  = positive_rate(unprivileged) / positive_rate(privileged)

        Returns (spd, di, group_stats).
        """
        sub = df.dropna(subset=[target_col, sens_col]).copy()

        # Binarize target
        y = sub[target_col]
        if set(y.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
            y_bin = y.astype(int)
        elif y.nunique() == 2:
            vals = sorted(y.unique())
            y_bin = y.map({vals[0]: 0, vals[1]: 1})
        elif pd.api.types.is_numeric_dtype(y):
            y_bin = (y > y.median()).astype(int)
        else:
            y_bin = (y == y.mode()[0]).astype(int)
        sub = sub.copy()
        sub["__y_tmp__"] = y_bin

        # Compute weighted positive rate per group
        group_stats: dict[str, dict] = {}
        for group_name, grp in sub.groupby(sens_col):
            if weight_col and weight_col in grp.columns:
                w = grp[weight_col].clip(0)
                total_w = w.sum()
                if total_w == 0:
                    continue
                pos_rate = float((grp["__y_tmp__"] * w).sum() / total_w)
            else:
                pos_rate = float(grp["__y_tmp__"].mean())
            group_stats[str(group_name)] = {
                "count": int(len(grp)),
                "positive_count": int(grp["__y_tmp__"].sum()),
                "positive_rate": round(pos_rate, 4),
            }

        if len(group_stats) < 2:
            return 0.0, None, group_stats

        priv_name   = max(group_stats, key=lambda g: group_stats[g]["positive_rate"])
        unpriv_name = min(group_stats, key=lambda g: group_stats[g]["positive_rate"])
        priv_rate   = group_stats[priv_name]["positive_rate"]
        unpriv_rate = group_stats[unpriv_name]["positive_rate"]

        # SPD: negative = unprivileged receives fewer positives (same sign as BiasEngine)
        spd = round(unpriv_rate - priv_rate, 4)
        di  = round(unpriv_rate / priv_rate, 4) if priv_rate > 0 else None

        return spd, di, group_stats

    # ── Public API ─────────────────────────────────────────────────────────────

    def run_both(
        self,
        df: pd.DataFrame,
        target_col: str,
        sensitive_attr: str,
        predicted_cause: str | None = None,
        # Analysis baseline — use as authoritative "before" so both pages
        # show the same dataset-level values.
        baseline_spd: float | None = None,
        baseline_di: float | None = None,
        baseline_group_stats: dict | None = None,
    ) -> dict[str, Any]:
        """Run both mitigation strategies and return a unified comparison."""
        rew = self.reweigh(
            df, target_col, sensitive_attr,
            baseline_spd=baseline_spd,
            baseline_di=baseline_di,
            baseline_group_stats=baseline_group_stats,
        )
        thr = self.threshold_adjust(
            df, target_col, sensitive_attr,
            baseline_spd=baseline_spd,
            baseline_di=baseline_di,
            baseline_group_stats=baseline_group_stats,
        )

        # ── Winner selection (dataset-level SPD only — no EOD/AOD) ────────────
        spd_b = abs(rew["before"]["SPD"] or 0)
        spd_r = abs(rew["after"]["SPD"] or 0)
        spd_t = abs(thr["after"]["SPD"] or 0)

        red_r = round(((spd_b - spd_r) / max(spd_b, 1e-9)) * 100, 1) if spd_b > 0 else 0.0
        red_t = round(((spd_b - spd_t) / max(spd_b, 1e-9)) * 100, 1) if spd_b > 0 else 0.0

        # Update effects with consistent bias reduction pct
        rew["effects"]["bias_reduction_pct"] = red_r
        thr["effects"]["bias_reduction_pct"] = red_t

        # Cause-based winner preference
        cause_winner = None
        cause_reason = None
        if predicted_cause == "proxy":
            cause_winner = "reweigh"
            cause_reason = (
                "Reweighing is preferred for proxy discrimination. "
                "It rebalances group-outcome frequencies so proxy features "
                "can no longer unfairly drive group disparities."
            )
        elif predicted_cause == "underrepresentation":
            cause_winner = "threshold"
            cause_reason = (
                "Threshold Adjustment is preferred for underrepresentation. "
                "It corrects the decision boundary per group, compensating for "
                "the lack of minority training examples."
            )
        elif predicted_cause == "historical_skew":
            cause_winner = "reweigh"
            cause_reason = (
                "Reweighing is preferred for historical bias. "
                "It down-weights historically over-represented group-outcome patterns."
            )

        # Validate cause preference against actual dataset-level SPD reduction
        if cause_winner == "reweigh" and red_r < 5:
            cause_winner = "threshold"
            cause_reason = (
                f"Threshold adjustment is recommended because reweighing achieved "
                f"only {red_r:.1f}% dataset-level bias reduction on this dataset. "
                f"Note: bias reduction is measured from actual dataset outcome distributions."
            )
        elif cause_winner == "threshold" and red_t < 5:
            cause_winner = "reweigh"
            cause_reason = (
                f"Reweighing is recommended because threshold adjustment achieved "
                f"only {red_t:.1f}% dataset-level bias reduction for this dataset."
            )

        # Pure metric fallback
        if cause_winner is None:
            rew_spd_b = rew["before"]["SPD"]
            rew_spd_a = rew["after"]["SPD"]
            thr_spd_a = thr["after"]["SPD"]
            if red_r >= red_t:
                cause_winner = "reweigh"
                cause_reason = (
                    f"Reweighing is recommended: it achieved {red_r:.1f}% dataset-level "
                    f"bias reduction (SPD {rew_spd_b:.3f} → {rew_spd_a:.3f}). "
                    f"These values are computed from actual dataset outcome distributions."
                )
            else:
                cause_winner = "threshold"
                cause_reason = (
                    f"Threshold adjustment is recommended: it achieved {red_t:.1f}% "
                    f"bias reduction in the simulation model "
                    f"(SPD {rew_spd_b:.3f} → {thr_spd_a:.3f}). "
                    f"Note: threshold SPD/DI values are from a simulation model, not actual data."
                )

        winner = cause_winner
        winner_reason = cause_reason

        # Generate explanations
        rew["explanation"] = self.generate_mitigation_explanation(
            rew["before"], rew["after"], "reweigh", sensitive_attr, rew["effects"]
        )
        thr["explanation"] = self.generate_mitigation_explanation(
            thr["before"], thr["after"], "threshold", sensitive_attr, thr["effects"]
        )

        return {
            "reweigh": rew,
            "threshold": thr,
            "winner": winner,
            "winner_reason": winner_reason,
            "predicted_cause_used": predicted_cause,
            "model_info": {
                "type": "GradientBoostingClassifier",
                "note": (
                    "Performance metrics (Acc/Precision/Recall/F1) come from an internal "
                    "simulation model. Reweighing SPD and DI are computed from actual "
                    "dataset outcome distributions. Threshold SPD/DI are from the simulation. "
                    "EOD and AOD are not available (require real model predictions)."
                ),
            },
        }

    # ── Explanation text ───────────────────────────────────────────────────────

    def generate_mitigation_explanation(
        self, before: dict, after: dict,
        technique: str, sensitive_attr: str,
        effects: dict,
    ) -> dict:
        """Generate plain-English explanation of what the mitigation technique did."""

        spd_before     = abs(before.get("SPD") or 0)
        spd_after      = abs(after.get("SPD") or 0)
        acc_before     = before.get("accuracy")
        acc_after      = after.get("accuracy")
        bias_reduction = effects.get("bias_reduction_pct") or 0
        is_simulation  = technique == "threshold"

        if technique == "reweigh":
            how_it_works = (
                f"Reweighing assigns higher statistical weight to under-represented "
                f"(group, outcome) combinations in the training data. For "
                f"'{sensitive_attr}', group-outcome pairs that were historically "
                f"under-represented receive greater importance, rebalancing the "
                f"learned outcome distribution."
            )
        else:
            how_it_works = (
                f"Threshold adjustment uses group-specific decision thresholds "
                f"rather than a single global threshold for '{sensitive_attr}'. "
                f"Each group gets its own cut-off probability, calibrated to "
                f"equalise outcome rates across groups. "
                f"Note: these values are from an internal simulation model because "
                f"no real model predictions are available."
            )

        # Bias result — be explicit about what was measured
        source_note = "" if not is_simulation else " (simulation model)"
        if spd_before == 0:
            bias_result = "No measurable dataset-level bias before mitigation (SPD = 0)."
        elif bias_reduction >= 50:
            bias_result = (
                f"Bias{source_note} was substantially reduced. SPD moved from "
                f"{spd_before:.3f} to {spd_after:.3f} — a {bias_reduction:.0f}% "
                f"reduction in the outcome rate gap between groups."
            )
        elif bias_reduction >= 10:
            bias_result = (
                f"Bias{source_note} was partially reduced. SPD moved from "
                f"{spd_before:.3f} to {spd_after:.3f} — a {bias_reduction:.0f}% improvement."
            )
        elif bias_reduction > 0:
            bias_result = (
                f"Modest bias reduction{source_note} ({bias_reduction:.0f}%). "
                f"SPD moved from {spd_before:.3f} to {spd_after:.3f}. "
                f"The bias may be embedded in feature correlations rather than "
                f"group-outcome frequency imbalance."
            )
        else:
            bias_result = (
                f"This technique did not reduce bias for '{sensitive_attr}'{source_note}. "
                f"SPD remained at approximately {spd_after:.3f}."
            )

        # Performance note (from simulation)
        if acc_before is None or acc_after is None:
            acc_result = "Performance metrics are not available."
        else:
            acc_delta = acc_after - acc_before
            sim_note = " (internal simulation — not real deployed model performance)"
            if abs(acc_delta) < 0.005:
                acc_result = (
                    f"Simulation accuracy was virtually unchanged "
                    f"({acc_before:.1%} → {acc_after:.1%}){sim_note}."
                )
            elif acc_delta < 0:
                acc_result = (
                    f"Simulation accuracy dropped from {acc_before:.1%} to "
                    f"{acc_after:.1%} ({abs(acc_delta)*100:.1f}% reduction). "
                    f"This illustrates the typical fairness-accuracy trade-off{sim_note}."
                )
            else:
                acc_result = (
                    f"Simulation accuracy improved slightly from {acc_before:.1%} to "
                    f"{acc_after:.1%}{sim_note}."
                )

        graph_explanation = (
            "The Fairness Improvement chart shows SPD and DI before and after mitigation. "
            "Reweighing before/after SPD and DI are computed from actual dataset outcome "
            "distributions (same formula as the analysis page). "
            "Threshold adjustment values are from an internal GBM simulation model. "
            "EOD and AOD are not shown -- they require real model predictions."
        )

        return {
            "how_it_works": how_it_works,
            "bias_result": bias_result,
            "acc_result": acc_result,
            "graph_explanation": graph_explanation,
            "summary": f"{bias_result} {acc_result}",
        }

    # ── Reweighing ─────────────────────────────────────────────────────────────

    def reweigh(
        self,
        df: pd.DataFrame,
        target_col: str,
        sensitive_attr: str,
        baseline_spd: float | None = None,
        baseline_di: float | None = None,
        baseline_group_stats: dict | None = None,
    ) -> dict[str, Any]:
        """
        Genuine dataset-level reweighing.

        - Uses IBM reweighing formula: w = P(G)*P(Y) / P(G,Y).
        - Measures AFTER SPD/DI from weighted dataset positive rates (dataset-level).
        - EOD and AOD = None (always — require external predictions).
        - Also runs GBM simulation for performance metrics (labelled as simulation).
        """
        df_work = df.copy().dropna(subset=[target_col, sensitive_attr])

        # Apply same binning as BiasEngine
        df_work["__sens_binned__"] = self._apply_binning(
            df_work[sensitive_attr], sensitive_attr
        )

        # Binarize target
        y_raw = df_work[target_col]
        if set(y_raw.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
            y_bin = y_raw.astype(int)
        elif y_raw.nunique() == 2:
            vals = sorted(y_raw.unique())
            y_bin = y_raw.map({vals[0]: 0, vals[1]: 1})
        elif pd.api.types.is_numeric_dtype(y_raw):
            y_bin = (y_raw > y_raw.median()).astype(int)
        else:
            y_bin = (y_raw == y_raw.mode()[0]).astype(int)
        df_work["__y__"] = y_bin

        # ── BEFORE: authoritative analysis baseline ──────────────────────────
        if baseline_spd is not None and baseline_di is not None:
            before_spd = float(baseline_spd)
            before_di  = float(baseline_di)
            before_gs  = baseline_group_stats or {}
        else:
            # Compute from dataset (same formula as BiasEngine) as fallback
            before_spd, before_di, before_gs = self._dataset_spd_di(
                df_work, "__y__", "__sens_binned__"
            )

        before: dict[str, Any] = {
            "SPD": round(before_spd, 4),
            "DI":  round(before_di, 4) if before_di is not None else None,
            "EOD": None,   # Not available — requires external model predictions
            "AOD": None,   # Not available — requires external model predictions
            "eod_available": False,
            "aod_available": False,
            "metrics_mode": "dataset_level",
            "group_stats": before_gs,
        }

        # ── Compute IBM reweighing weights ───────────────────────────────────
        n = len(df_work)
        le_s = LabelEncoder()
        s_all = le_s.fit_transform(df_work["__sens_binned__"])
        y_all = df_work["__y__"].values

        weights = np.ones(n)
        for g in np.unique(s_all):
            for label in np.unique(y_all):
                mask = (s_all == g) & (y_all == label)
                n_gl = int(mask.sum())
                if n_gl == 0:
                    continue
                p_g  = float((s_all == g).sum()) / n
                p_l  = float((y_all == label).sum()) / n
                p_gl = n_gl / n
                weights[mask] = (p_g * p_l) / p_gl

        weights = np.clip(weights, 0.1, 10.0)
        df_work["__weight__"] = weights

        # ── AFTER: dataset-level SPD/DI from reweighted positive rates ───────
        after_spd, after_di, after_gs = self._dataset_spd_di(
            df_work, "__y__", "__sens_binned__", weight_col="__weight__"
        )

        after: dict[str, Any] = {
            "SPD": round(after_spd, 4),
            "DI":  round(after_di, 4) if after_di is not None else None,
            "EOD": None,
            "AOD": None,
            "eod_available": False,
            "aod_available": False,
            "metrics_mode": "dataset_level_reweighted",
            "group_stats": after_gs,
        }

        # ── GBM simulation for performance metrics only ───────────────────────
        sim_before, sim_after = self._run_simulation(
            df_work, target_col, sensitive_attr, weights
        )

        SIM_NOTE = (
            "Performance metrics come from an internal GBM simulation model, "
            "not from a real deployed model."
        )
        if sim_before is not None:
            before.update(sim_before)
            before["simulation_note"] = SIM_NOTE
        if sim_after is not None:
            after.update(sim_after)
            after["simulation_note"] = SIM_NOTE

        # ── Effects ──────────────────────────────────────────────────────────
        spd_b = abs(before["SPD"] or 0)
        spd_a = abs(after["SPD"] or 0)
        bias_reduction_pct = (
            round(((spd_b - spd_a) / max(spd_b, 1e-9)) * 100, 1)
            if spd_b > 0 else 0.0
        )
        spd_delta = round((after["SPD"] or 0) - (before["SPD"] or 0), 4)
        di_b = before.get("DI")
        di_a = after.get("DI")
        di_delta = (
            round(di_a - di_b, 4) if di_b is not None and di_a is not None else None
        )
        acc_b = before.get("accuracy")
        acc_a = after.get("accuracy")
        acc_delta = (
            round(acc_a - acc_b, 4)
            if acc_b is not None and acc_a is not None else None
        )
        acc_retained = (
            round(acc_a / max(acc_b, 1e-9) * 100, 1) if acc_b else None
        )

        diagnostic = None
        if spd_b > 0.01 and bias_reduction_pct < 3:
            diagnostic = (
                f"Low dataset-level bias reduction ({bias_reduction_pct:.1f}%) "
                f"may occur when: (1) bias is driven by proxy features that survive "
                f"weight rebalancing, (2) outcome distribution is weakly related to "
                f"group membership, or (3) groups are already near-equal in size. "
                f"SPD/DI values are accurate — computed from actual data."
            )

        effects: dict[str, Any] = {
            "bias_reduction_pct":    bias_reduction_pct,
            "spd_delta":             spd_delta,
            "di_delta":              di_delta,
            "accuracy_delta":        acc_delta,
            "accuracy_retained_pct": acc_retained,
            "diagnostic":            diagnostic,
        }

        return {
            "before": before,
            "after":  after,
            "effects": effects,
            "improvement_pct": bias_reduction_pct,
            "weights_summary": {
                "min":  round(float(weights.min()), 3),
                "max":  round(float(weights.max()), 3),
                "mean": round(float(weights.mean()), 3),
            },
            "is_simulation": False,   # Reweighing SPD/DI = real dataset metrics
            "simulation_note": (
                "Dataset-level fairness metrics (SPD, DI) were evaluated before and "
                "after applying reweighing weights to the dataset outcome distributions. "
                "EOD and AOD were not evaluated because model predictions are not available. "
                "Performance metrics (Acc/Precision/Recall/F1) come from an internal GBM "
                "simulation model and are for illustration only."
            ),
        }

    # ── Threshold Adjustment ───────────────────────────────────────────────────

    def threshold_adjust(
        self,
        df: pd.DataFrame,
        target_col: str,
        sensitive_attr: str,
        baseline_spd: float | None = None,
        baseline_di: float | None = None,
        baseline_group_stats: dict | None = None,
    ) -> dict[str, Any]:
        """
        Threshold adjustment — operates on simulation model predictions.

        - "Before" uses the analysis baseline (same as reweighing for consistency).
        - Trains a GBM simulation model internally.
        - Finds per-group thresholds that minimise SPD in the simulation.
        - "After" SPD/DI are from simulation model predictions (is_simulation=True).
        - EOD and AOD: None always.
        - All results are labelled as simulation.
        """
        df_work = df.copy().dropna(subset=[target_col, sensitive_attr])

        # Apply same binning as BiasEngine
        df_work["__sens_binned__"] = self._apply_binning(
            df_work[sensitive_attr], sensitive_attr
        )

        # Binarize target
        y_raw = df_work[target_col]
        if set(y_raw.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
            y_bin = y_raw.astype(int)
        elif y_raw.nunique() == 2:
            vals = sorted(y_raw.unique())
            y_bin = y_raw.map({vals[0]: 0, vals[1]: 1})
        elif pd.api.types.is_numeric_dtype(y_raw):
            y_bin = (y_raw > y_raw.median()).astype(int)
        else:
            y_bin = (y_raw == y_raw.mode()[0]).astype(int)
        df_work["__y__"] = y_bin

        # ── BEFORE: same analysis baseline as reweighing ──────────────────────
        if baseline_spd is not None and baseline_di is not None:
            before_spd = float(baseline_spd)
            before_di  = float(baseline_di)
            before_gs  = baseline_group_stats or {}
        else:
            before_spd, before_di, before_gs = self._dataset_spd_di(
                df_work, "__y__", "__sens_binned__"
            )

        before: dict[str, Any] = {
            "SPD": round(before_spd, 4),
            "DI":  round(before_di, 4) if before_di is not None else None,
            "EOD": None,
            "AOD": None,
            "eod_available": False,
            "aod_available": False,
            "metrics_mode": "dataset_level",
            "group_stats": before_gs,
        }

        # ── Simulation model ──────────────────────────────────────────────────
        le_s = LabelEncoder()
        s_all = le_s.fit_transform(df_work["__sens_binned__"])
        y_all = df_work["__y__"].values

        X_all, _ = self._prepare_features(df_work, target_col, sensitive_attr)

        idx = np.arange(len(df_work))
        try:
            idx_train, idx_test = train_test_split(
                idx, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE,
                stratify=y_all,
            )
        except ValueError:
            idx_train, idx_test = train_test_split(
                idx, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE,
            )

        X_train = X_all[idx_train]
        X_test  = X_all[idx_test]
        y_train = y_all[idx_train]
        y_test  = y_all[idx_test]
        s_test  = s_all[idx_test]

        model = GradientBoostingClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05,
            subsample=0.8, random_state=self.RANDOM_STATE,
        )
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_test)[:, 1]

        # Before threshold (0.5 global)
        y_pred_before = (proba >= 0.5).astype(int)

        # Before simulation performance
        before["accuracy"]  = round(float(accuracy_score(y_test, y_pred_before)), 4)
        before["precision"] = round(float(precision_score(y_test, y_pred_before, zero_division=0)), 4)
        before["recall"]    = round(float(recall_score(y_test, y_pred_before, zero_division=0)), 4)
        before["f1"]        = round(float(f1_score(y_test, y_pred_before, zero_division=0)), 4)
        before["simulation_note"] = (
            "Performance metrics come from an internal GBM simulation model, "
            "not from a real deployed model."
        )

        # ── Per-group threshold search to minimise SPD in simulation ──────────
        groups = np.unique(s_test)
        threshold_range = np.arange(0.2, 0.81, 0.05)
        best_thresholds: dict = {g: 0.5 for g in groups}
        best_spd_sim = float("inf")

        if len(groups) == 2:
            g0, g1 = groups[0], groups[1]
            for t0 in threshold_range:
                for t1 in threshold_range:
                    y_adj = np.zeros(len(proba), dtype=int)
                    y_adj[s_test == g0] = (proba[s_test == g0] >= t0).astype(int)
                    y_adj[s_test == g1] = (proba[s_test == g1] >= t1).astype(int)
                    rates = {g: float(y_adj[s_test == g].mean()) for g in groups}
                    spd_sim = abs(min(rates.values()) - max(rates.values()))
                    if spd_sim < best_spd_sim:
                        best_spd_sim = spd_sim
                        best_thresholds = {g0: t0, g1: t1}
        else:
            for t in threshold_range:
                y_adj = (proba >= t).astype(int)
                rates = {g: float(y_adj[s_test == g].mean()) for g in groups}
                spd_sim = abs(min(rates.values()) - max(rates.values()))
                if spd_sim < best_spd_sim:
                    best_spd_sim = spd_sim
                    best_thresholds = {g: t for g in groups}

        # Apply best thresholds
        y_pred_after = np.zeros(len(proba), dtype=int)
        for g, thresh in best_thresholds.items():
            y_pred_after[s_test == g] = (proba[s_test == g] >= thresh).astype(int)

        # After simulation SPD/DI from prediction rates
        sim_rates = {g: float(y_pred_after[s_test == g].mean()) for g in groups}
        priv_sim   = max(sim_rates.values())
        unpriv_sim = min(sim_rates.values())
        after_spd_sim = round(unpriv_sim - priv_sim, 4)
        after_di_sim  = round(unpriv_sim / priv_sim, 4) if priv_sim > 0 else None

        SIM_NOTE = (
            "SPD/DI and performance metrics here come from an internal GBM simulation model. "
            "Threshold adjustment requires real model prediction scores -- "
            "these values illustrate the technique but are not real measurements."
        )

        after: dict[str, Any] = {
            "SPD": after_spd_sim,
            "DI":  after_di_sim,
            "EOD": None,
            "AOD": None,
            "eod_available": False,
            "aod_available": False,
            "metrics_mode": "simulation",
            "accuracy":  round(float(accuracy_score(y_test, y_pred_after)), 4),
            "precision": round(float(precision_score(y_test, y_pred_after, zero_division=0)), 4),
            "recall":    round(float(recall_score(y_test, y_pred_after, zero_division=0)), 4),
            "f1":        round(float(f1_score(y_test, y_pred_after, zero_division=0)), 4),
            "simulation_note": SIM_NOTE,
            "group_stats": {},
        }

        # ── Effects ───────────────────────────────────────────────────────────
        spd_b = abs(before["SPD"] or 0)
        spd_a = abs(after["SPD"] or 0)
        bias_reduction_pct = (
            round(((spd_b - spd_a) / max(spd_b, 1e-9)) * 100, 1)
            if spd_b > 0 else 0.0
        )
        spd_delta = round((after["SPD"] or 0) - (before["SPD"] or 0), 4)
        di_b = before.get("DI")
        di_a = after.get("DI")
        di_delta = (
            round(di_a - di_b, 4) if di_b is not None and di_a is not None else None
        )
        acc_b = before.get("accuracy")
        acc_a = after.get("accuracy")
        acc_delta = (
            round(acc_a - acc_b, 4)
            if acc_b is not None and acc_a is not None else None
        )
        acc_retained = (
            round(acc_a / max(acc_b, 1e-9) * 100, 1) if acc_b else None
        )

        diagnostic = None
        if spd_b > 0.01 and bias_reduction_pct < 3:
            diagnostic = (
                f"Low simulation bias reduction ({bias_reduction_pct:.1f}%) from "
                f"threshold adjustment. Note: the dataset-level SPD = "
                f"{before['SPD']:.3f} (from actual data -- see analysis page). "
                f"These simulation values are for illustration only."
            )

        effects: dict[str, Any] = {
            "bias_reduction_pct":    bias_reduction_pct,
            "spd_delta":             spd_delta,
            "di_delta":              di_delta,
            "accuracy_delta":        acc_delta,
            "accuracy_retained_pct": acc_retained,
            "diagnostic":            diagnostic,
        }

        return {
            "before": before,
            "after":  after,
            "effects": effects,
            "improvement_pct": bias_reduction_pct,
            "thresholds": {str(k): round(float(v), 2) for k, v in best_thresholds.items()},
            "is_simulation": True,   # Threshold SPD/DI = simulation model
            "simulation_note": (
                "Threshold adjustment requires model decision scores. Without real "
                "model predictions, an internal GBM simulation was used to demonstrate "
                "the technique. Before/after SPD and DI for threshold adjustment are "
                "from simulation predictions, not from actual dataset outcome distributions. "
                "EOD and AOD are not available."
            ),
        }

    # ── GBM simulation helper ─────────────────────────────────────────────────

    def _run_simulation(
        self,
        df_work: pd.DataFrame,
        target_col: str,
        sensitive_attr: str,
        weights: np.ndarray | None = None,
    ) -> tuple:
        """
        Run a GBM simulation before (no weights) and after (with weights).
        Returns (before_perf, after_perf) dicts with accuracy/precision/recall/f1.
        Returns (None, None) if not enough data or error.
        """
        try:
            y_all = df_work["__y__"].values
            X_all, _ = self._prepare_features(df_work, target_col, sensitive_attr)

            idx = np.arange(len(df_work))
            try:
                idx_train, idx_test = train_test_split(
                    idx, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE,
                    stratify=y_all,
                )
            except ValueError:
                idx_train, idx_test = train_test_split(
                    idx, test_size=self.TEST_SIZE, random_state=self.RANDOM_STATE,
                )

            X_train, X_test = X_all[idx_train], X_all[idx_test]
            y_train, y_test = y_all[idx_train], y_all[idx_test]

            # Before (no weights)
            m1 = GradientBoostingClassifier(
                n_estimators=150, max_depth=3, learning_rate=0.05,
                subsample=0.8, random_state=self.RANDOM_STATE,
            )
            m1.fit(X_train, y_train)
            p1 = m1.predict(X_test)
            sim_before = {
                "accuracy":  round(float(accuracy_score(y_test, p1)), 4),
                "precision": round(float(precision_score(y_test, p1, zero_division=0)), 4),
                "recall":    round(float(recall_score(y_test, p1, zero_division=0)), 4),
                "f1":        round(float(f1_score(y_test, p1, zero_division=0)), 4),
            }

            if weights is None:
                return sim_before, None

            w_train = weights[idx_train]
            m2 = GradientBoostingClassifier(
                n_estimators=150, max_depth=3, learning_rate=0.05,
                subsample=0.8, random_state=self.RANDOM_STATE,
            )
            m2.fit(X_train, y_train, sample_weight=w_train)
            p2 = m2.predict(X_test)
            sim_after = {
                "accuracy":  round(float(accuracy_score(y_test, p2)), 4),
                "precision": round(float(precision_score(y_test, p2, zero_division=0)), 4),
                "recall":    round(float(recall_score(y_test, p2, zero_division=0)), 4),
                "f1":        round(float(f1_score(y_test, p2, zero_division=0)), 4),
            }
            return sim_before, sim_after

        except Exception as exc:
            print(f"[Mitigator] Simulation failed: {exc}")
            return None, None

    # ── Feature preparation ────────────────────────────────────────────────────

    def _prepare_features(self, df_work, target_col, sensitive_attr):
        """Encode all features except target/sensitive/internal columns."""
        exclude = {
            target_col, sensitive_attr,
            "__target__", "__sens__", "__y__", "__s__",
            "__sens_binned__", "__weight__", "__sens_raw__", "__y_tmp__",
        }

        y_vals = None
        for y_candidate in ["__y__", "__target__", target_col]:
            if y_candidate in df_work.columns:
                try:
                    y_vals = df_work[y_candidate].astype(float)
                    break
                except Exception:
                    pass

        leaking = set()
        if y_vals is not None:
            for col in df_work.columns:
                if col in exclude:
                    continue
                try:
                    if df_work[col].dtype in ["int64", "float64", "int32", "float32"]:
                        corr = abs(float(df_work[col].corr(y_vals)))
                    else:
                        enc = LabelEncoder().fit_transform(
                            df_work[col].fillna("missing").astype(str))
                        corr = abs(float(np.corrcoef(enc, y_vals)[0, 1]))
                    if corr > 0.90:
                        leaking.add(col)
                        print(f"[Mitigator] LEAKAGE '{col}' corr={corr:.3f} EXCLUDED")
                except Exception:
                    pass

        target_base = (target_col
                       .replace("_binary", "").replace("_encoded", "")
                       .replace("_label", "").replace("_num", "").lower())
        for col in df_work.columns:
            if col in exclude or col in leaking:
                continue
            if target_base in col.lower() and col.lower() != target_col.lower():
                leaking.add(col)

        feature_cols = [
            c for c in df_work.columns
            if c not in exclude and c not in leaking
        ]
        if not feature_cols:
            feature_cols = [sensitive_attr] if sensitive_attr in df_work.columns else []

        X_parts = []
        for col in feature_cols:
            try:
                if df_work[col].dtype in ["int64", "float64", "int32", "float32"]:
                    X_parts.append(df_work[[col]].values.astype(float))
                else:
                    enc = LabelEncoder().fit_transform(
                        df_work[col].fillna("missing").astype(str))
                    X_parts.append(enc.reshape(-1, 1).astype(float))
            except Exception:
                pass

        if not X_parts:
            return np.zeros((len(df_work), 1)), []

        return np.hstack(X_parts), feature_cols

    # ── Legacy static helper (kept for router compatibility) ──────────────────

    @staticmethod
    def effects(before: dict, after: dict) -> dict:
        """Legacy method. Compute delta metrics between before and after."""
        def delta(key: str):
            b = before.get(key)
            a = after.get(key)
            if b is None or a is None:
                return None
            return round(float(a) - float(b), 4)

        spd_before = abs(before.get("SPD") or before.get("spd") or 0)
        spd_after  = abs(after.get("SPD")  or after.get("spd")  or 0)
        bias_reduction_pct = (
            round((spd_before - spd_after) / spd_before * 100, 2)
            if spd_before > 0 else 0.0
        )
        acc_before = before.get("accuracy", 1) or 1
        acc_after  = after.get("accuracy", 1)  or 1
        accuracy_retained_pct = (
            round(acc_after / acc_before * 100, 2) if acc_before > 0 else 100.0
        )

        return {
            "accuracy_delta":        delta("accuracy"),
            "precision_delta":       delta("precision"),
            "recall_delta":          delta("recall"),
            "f1_delta":              delta("f1"),
            "spd_delta":             delta("SPD") or delta("spd"),
            "bias_reduction_pct":    bias_reduction_pct,
            "accuracy_retained_pct": accuracy_retained_pct,
        }
