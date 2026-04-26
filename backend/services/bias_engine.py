"""
ByUs — Bias Analysis Engine

Computes SPD, DI, EOD, AOD per sensitive attribute with bootstrapped
confidence intervals, severity labels, and a composite Audit Score.
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np
import pandas as pd

# Suppress noisy sklearn warnings during bootstrap resamples
_warnings.filterwarnings("ignore", category=RuntimeWarning)


class BiasEngine:
    """
    Compute fairness metrics for a DataFrame.

    All metrics follow the convention that *privileged* is the largest
    demographic group by count.  This is pragmatic and avoids requiring the
    caller to know which group is historically advantaged.
    """

    BOOTSTRAP_N: int = 200
    BOOTSTRAP_SEED: int = 42

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(
        self,
        df: pd.DataFrame,
        target_col: str,
        sensitive_attrs: list[str],
        use_predictions: bool = False,
    ) -> dict[str, Any]:
        """
        Run full bias analysis.

        Parameters
        ----------
        df : pd.DataFrame
            Dataset.  If ``use_predictions`` is True the frame must contain a
            column named ``__predictions__`` with model-generated labels.
        target_col : str
            Ground-truth label column.
        sensitive_attrs : list[str]
            Protected-attribute columns to analyse.
        use_predictions : bool
            When True, metrics are computed against ``__predictions__`` instead
            of ``target_col``.

        Returns
        -------
        dict
            ``metrics_per_attr``, ``audit_score``, ``overall_severity``
        """
        label_col = "__predictions__" if use_predictions else target_col

        metrics_per_attr: dict[str, Any] = {}

        for attr in sensitive_attrs:
            if attr not in df.columns:
                metrics_per_attr[attr] = {
                    "error": f"Column '{attr}' not found in dataset."
                }
                continue

            # Drop rows where the attribute or label is null
            cols_to_keep = list(dict.fromkeys([attr, target_col, label_col]))
            sub = df[cols_to_keep].dropna(
                subset=list(dict.fromkeys([attr, label_col]))
            )
            if sub.empty:
                metrics_per_attr[attr] = {
                    "error": "No valid rows after dropping nulls."
                }
                continue

            metrics_per_attr[attr] = self._compute_attr_metrics(
                sub, attr, target_col, label_col
            )

        # ── Audit Score ───────────────────────────────────────────────────────
        audit_score_rounded = self._compute_audit_score(metrics_per_attr)

        # Grade
        grade = self._grade(audit_score_rounded)

        # Overall severity
        severities = [
            m["severity"]
            for m in metrics_per_attr.values()
            if isinstance(m, dict) and "severity" in m
        ]
        if "high" in severities:
            overall_severity = "high"
        elif "medium" in severities:
            overall_severity = "medium"
        else:
            overall_severity = "low"

        return {
            "metrics_per_attr": metrics_per_attr,
            "audit_score": audit_score_rounded,
            "grade": grade,
            "overall_severity": overall_severity,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _compute_attr_metrics(
        self,
        sub: pd.DataFrame,
        attr: str,
        target_col: str,
        label_col: str,
    ) -> dict[str, Any]:
        """Compute all metrics for a single sensitive attribute."""
        feature_cols = [c for c in sub.columns if c not in [target_col, attr, label_col]]
        # Step 1 — always work on a clean copy
        df_work = sub[[target_col, attr, label_col] + feature_cols].copy()
        df_work = df_work.dropna(subset=[target_col, attr])

        # Step 2 — binarize target robustly
        y = df_work[label_col]
        if set(y.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
            y_bin = y.astype(int)
        elif y.nunique() == 2:
            vals = sorted(y.unique())
            y_bin = y.map({vals[0]: 0, vals[1]: 1})
        elif pd.api.types.is_numeric_dtype(y):
            median = y.median()
            y_bin = (y > median).astype(int)
        else:
            y_bin = (y == y.mode()[0]).astype(int)
        df_work['__target__'] = y_bin

        # Step 3 — encode sensitive attribute as integers
        from sklearn.preprocessing import LabelEncoder
        le = LabelEncoder()
        df_work['__sens__'] = le.fit_transform(df_work[attr].astype(str))
        group_names = {i: name for i, name in enumerate(le.classes_)}

        warnings_list = []

        # Step 4 — compute group positive rates
        groups = df_work['__sens__'].unique()
        group_stats = {}
        for g in groups:
            mask = df_work['__sens__'] == g
            group_name = group_names[g]
            count = int(mask.sum())
            if count <= 1:
                warnings_list.append(f"Group '{group_name}' has only {count} member(s) — excluded from metrics.")
                continue
            pos_rate = float(df_work.loc[mask, '__target__'].mean())
            group_stats[str(group_name)] = {
                "count": count,
                "positive_rate": round(pos_rate, 4),
                "pct_of_total": round(count / len(df_work) * 100, 1)
            }

        if len(group_stats) < 2:
            return {
                "error": f"'{attr}' has fewer than 2 valid groups after filtering.",
                "group_stats": group_stats,
            }

        # Step 5 — find privileged and unprivileged
        priv_name = max(group_stats, key=lambda g: group_stats[g]["positive_rate"])
        unpriv_name = min(group_stats, key=lambda g: group_stats[g]["positive_rate"])
        priv_rate = group_stats[priv_name]["positive_rate"]
        unpriv_rate = group_stats[unpriv_name]["positive_rate"]

        # Step 6 — compute metrics
        SPD = round(priv_rate - unpriv_rate, 4)
        DI = round(unpriv_rate / priv_rate, 4) if priv_rate > 0 else 0.0

        if label_col != target_col:
            y_true = df_work[target_col]
            if set(y_true.dropna().unique()).issubset({0, 1, 0.0, 1.0}):
                y_true_bin = y_true.astype(int)
            elif y_true.nunique() == 2:
                vals = sorted(y_true.unique())
                y_true_bin = y_true.map({vals[0]: 0, vals[1]: 1})
            elif pd.api.types.is_numeric_dtype(y_true):
                median = y_true.median()
                y_true_bin = (y_true > median).astype(int)
            else:
                y_true_bin = (y_true == y_true.mode()[0]).astype(int)
            df_work['__truth__'] = y_true_bin
            
            priv_encoded = next(k for k, v in group_names.items() if str(v) == priv_name)
            unpriv_encoded = next(k for k, v in group_names.items() if str(v) == unpriv_name)
            eod, aod = self._equal_opportunity_encoded(df_work, '__truth__', '__target__', '__sens__', priv_encoded, unpriv_encoded)
            EOD = round(eod, 4) if eod is not None else None
            AOD = round(aod, 4) if aod is not None else None
        else:
            EOD = None
            AOD = None

        if SPD > 0.99 and DI < 0.01:
            warnings_list.append("Metrics look extreme. Check that target column is correctly binary and sensitive attribute has meaningful variation.")

        # Step 7 — bootstrapped CI for SPD
        spd_samples = []
        for _ in range(self.BOOTSTRAP_N):
            sample = df_work.sample(frac=1.0, replace=True, random_state=None)
            rates = sample.groupby('__sens__')['__target__'].mean()
            if len(rates) >= 2:
                spd_samples.append(float(rates.max() - rates.min()))
        if spd_samples:
            ci_low = round(float(np.percentile(spd_samples, 2.5)), 4)
            ci_high = round(float(np.percentile(spd_samples, 97.5)), 4)
            statistically_significant = not (ci_low <= 0 <= ci_high)
        else:
            ci_low, ci_high, statistically_significant = None, None, True

        return {
            "privileged_group": str(priv_name),
            "unprivileged_group": str(unpriv_name),
            "group_stats": group_stats,
            "spd": SPD,
            "di": DI,
            "eod": EOD,
            "aod": AOD,
            "severity": self._severity(SPD),
            "legal_flag": DI < 0.8,
            "bootstrapped_ci": {"low_95": ci_low, "high_95": ci_high},
            "statistically_significant": statistically_significant,
            "warnings": warnings_list
        }

    def _equal_opportunity_encoded(
        self,
        sub: pd.DataFrame,
        truth_col: str,
        target_col: str,
        sens_col: str,
        privileged: Any,
        unprivileged: Any,
    ) -> tuple[float | None, float | None]:
        def tpr_fpr(mask: pd.Series) -> tuple[float, float]:
            grp = sub[mask]
            actual = grp[truth_col]
            pred = grp[target_col]
            tp = int(((pred == 1) & (actual == 1)).sum())
            fn = int(((pred == 0) & (actual == 1)).sum())
            fp = int(((pred == 1) & (actual == 0)).sum())
            tn = int(((pred == 0) & (actual == 0)).sum())
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            return tpr, fpr

        priv_mask = sub[sens_col] == privileged
        unpriv_mask = sub[sens_col] == unprivileged

        tpr_priv, fpr_priv = tpr_fpr(priv_mask)
        tpr_unpriv, fpr_unpriv = tpr_fpr(unpriv_mask)

        eod = tpr_priv - tpr_unpriv
        aod = ((tpr_priv - tpr_unpriv) + (fpr_priv - fpr_unpriv)) / 2.0

        return float(eod), float(aod)

    # ── Bootstrapped CI ───────────────────────────────────────────────────────

    def _bootstrap_spd_ci(
        self,
        sub: pd.DataFrame,
        attr: str,
        label_col: str,
        privileged: Any,
        unprivileged: Any,
    ) -> tuple[dict[str, float], bool]:
        """
        Compute 95% bootstrapped confidence interval for SPD.

        Returns (ci_dict, statistically_significant).
        """
        rng = np.random.default_rng(self.BOOTSTRAP_SEED)
        n = len(sub)
        spd_samples: list[float] = []

        for _ in range(self.BOOTSTRAP_N):
            sample = sub.iloc[rng.integers(0, n, size=n)]
            priv_rate = float(sample.loc[sample[attr] == privileged, label_col].mean())
            unpriv_rate = float(sample.loc[sample[attr] == unprivileged, label_col].mean())
            if np.isnan(priv_rate) or np.isnan(unpriv_rate):
                continue
            spd_samples.append(priv_rate - unpriv_rate)

        if len(spd_samples) < 10:
            return {"low_95": None, "high_95": None}, False

        low_95 = float(np.percentile(spd_samples, 2.5))
        high_95 = float(np.percentile(spd_samples, 97.5))
        # Statistically significant if CI does NOT cross zero
        significant = not (low_95 <= 0 <= high_95)

        return (
            {"low_95": round(low_95, 4), "high_95": round(high_95, 4)},
            significant,
        )

    # ── Severity & Grade ──────────────────────────────────────────────────────

    @staticmethod
    def _severity(spd: float) -> str:
        abs_spd = abs(spd)
        if abs_spd < 0.1:
            return "low"
        if abs_spd < 0.2:
            return "medium"
        return "high"

    @staticmethod
    def _grade(score: float) -> str:
        if score >= 85:
            return "A (Fair)"
        elif score >= 70:
            return "B (Minor issues)"
        elif score >= 50:
            return "C (Moderate bias)"
        else:
            return "F (High bias — action required)"

    def _compute_audit_score(self, metrics_per_attr: dict) -> float:
        if not metrics_per_attr:
            return 100.0
        penalties = []
        for attr, m in metrics_per_attr.items():
            if "error" in m:
                continue
            spd = abs(m.get("spd", m.get("SPD", 0)) or 0)
            di = m.get("di", m.get("DI", 1.0)) or 1.0
            eod = m.get("eod", m.get("EOD"))

            # SPD penalty: 0.1→15pts, 0.2→35pts, 0.3→55pts, 0.5→80pts
            spd_penalty = min(80, spd * 160)

            # DI penalty: only when below 0.8 legal threshold
            di_penalty = min(45, max(0, (0.8 - di) * 75)) if di < 0.8 else 0

            # EOD penalty if available
            eod_penalty = min(20, abs(eod) * 60) if eod is not None and not np.isnan(eod) else 0

            penalties.append(spd_penalty + di_penalty + eod_penalty)

        if not penalties:
            return 100.0

        total_penalty = sum(penalties) / max(len(penalties), 1)
        score = max(0.0, min(100.0, 100.0 - total_penalty))
        return float(round(score, 1))
