"""
FairEnough — Bias Analysis Engine

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

            # Drop rows where the attribute or label is null, but keep ALL columns
            # so _compute_attr_metrics has feature columns available for internal EOD/AOD model
            sub = df.dropna(subset=list(dict.fromkeys([attr, label_col])))
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

        # Grade and overall severity MUST come from audit_score only
        grade, overall_severity, grade_label, _ = self._derive_grade_and_severity(audit_score_rounded)

        return {
            "metrics_per_attr": metrics_per_attr,
            "audit_score": audit_score_rounded,
            "grade": grade,
            "overall_severity": overall_severity,
            "grade_label": grade_label,
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
        cols_to_select = list(dict.fromkeys([target_col, attr, label_col] + feature_cols))
        df_work = sub[cols_to_select].copy()
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
            # External model predictions available — compare predictions vs ground truth
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
            # No external model — train an internal classifier and compute EOD/AOD from
            # its predictions vs ground truth, same method used by BiasMitigator.
            EOD = None
            AOD = None
            try:
                import numpy as _np
                from sklearn.ensemble import GradientBoostingClassifier
                from sklearn.model_selection import train_test_split
                from sklearn.preprocessing import LabelEncoder as _LE

                # Build clean feature matrix — exclude target and sensitive attr
                exclude_cols = {target_col, attr, label_col, '__target__', '__sens__',
                                '__truth__', '__predictions__'}
                feat_candidates = [c for c in df_work.columns if c not in exclude_cols]

                if feat_candidates and len(df_work) >= 60:
                    y_all = df_work['__target__'].values
                    s_all = df_work['__sens__'].values

                    # Leakage guard: DROP individual leaking columns (corr > 0.95 with target)
                    # Do NOT abort the entire model — just remove the bad columns.
                    clean_cols = []
                    X_parts = []
                    for fc in feat_candidates:
                        col_data = df_work[fc].copy()
                        if col_data.dtype.kind in ('i', 'f'):
                            arr = col_data.fillna(col_data.median()).values.astype(float)
                        else:
                            arr = _LE().fit_transform(
                                col_data.fillna('missing').astype(str)
                            ).astype(float)

                        try:
                            corr = abs(float(_np.corrcoef(arr, y_all)[0, 1]))
                        except Exception:
                            corr = 0.0

                        if corr > 0.95:
                            # Skip this column — it leaks the target
                            continue

                        clean_cols.append(fc)
                        X_parts.append(arr.reshape(-1, 1))

                    if X_parts:  # At least one clean feature remains
                        X_all = _np.hstack(X_parts)
                        idx = _np.arange(len(df_work))
                        idx_tr, idx_te = train_test_split(
                            idx, test_size=0.30, random_state=42, stratify=y_all
                        )
                        clf = GradientBoostingClassifier(
                            n_estimators=100, max_depth=3,
                            learning_rate=0.1, subsample=0.8,
                            random_state=42
                        )
                        clf.fit(X_all[idx_tr], y_all[idx_tr])
                        y_pred = clf.predict(X_all[idx_te])
                        y_true_te = y_all[idx_te]
                        s_te = s_all[idx_te]

                        # Compute EOD and AOD from model predictions vs ground truth
                        groups_te = _np.unique(s_te)
                        if len(groups_te) >= 2:
                            rates = {g: _np.mean(y_pred[s_te == g]) for g in groups_te}
                            priv_g   = max(rates, key=rates.get)
                            unpriv_g = min(rates, key=rates.get)

                            def _tpr_fpr(mask):
                                yg, pg = y_true_te[mask], y_pred[mask]
                                tp = int(((pg == 1) & (yg == 1)).sum())
                                fn = int(((pg == 0) & (yg == 1)).sum())
                                fp = int(((pg == 1) & (yg == 0)).sum())
                                tn = int(((pg == 0) & (yg == 0)).sum())
                                tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
                                fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
                                return tpr, fpr

                            tpr_p, fpr_p = _tpr_fpr(s_te == priv_g)
                            tpr_u, fpr_u = _tpr_fpr(s_te == unpriv_g)

                            EOD = round(float(tpr_p - tpr_u), 4)
                            AOD = round(float(((tpr_p - tpr_u) + (fpr_p - fpr_u)) / 2), 4)
            except Exception as _e:
                # Never break analysis if internal model fails
                pass


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
            "SPD": SPD,
            "DI": DI,
            "EOD": EOD,
            "AOD": AOD,
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
    def _derive_grade_and_severity(audit_score: float):
        if audit_score >= 85:
            return "A", "low",   "Fair",           "#22C55E"
        elif audit_score >= 70:
            return "B", "low",   "Minor Issues",   "#84CC16"
        elif audit_score >= 50:
            return "C", "medium","Moderate Bias",  "#F59E0B"
        else:
            return "F", "high",  "High Bias",      "#EF4444"

    @staticmethod
    def _get_overall_severity(audit_score: float) -> str:
        """Severity must always match the grade, derived from audit_score."""
        return BiasEngine._derive_grade_and_severity(audit_score)[1]

    @staticmethod
    def _get_grade(audit_score: float) -> str:
        """Grade derived from audit_score."""
        return BiasEngine._derive_grade_and_severity(audit_score)[0]

    @staticmethod
    def _severity(spd: float) -> str:
        """Per-attribute severity based on SPD thresholds (independent of overall grade)."""
        abs_spd = abs(spd)
        if abs_spd < 0.1:
            return "low"
        if abs_spd < 0.2:
            return "medium"
        return "high"

    @staticmethod
    def _grade(score: float) -> str:
        """Legacy method kept for backwards compat — delegates to _get_grade."""
        return BiasEngine._get_grade(score)

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
