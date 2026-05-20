import numpy as np
import json
import os
import threading
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

SCENARIOS = [
    'criminal_justice', 'education', 'healthcare',
    'hiring', 'income', 'lending', 'other'
]

CAUSE_LABELS = {
    "proxy": (
        "Proxy Discrimination — another feature in this dataset acts as a "
        "hidden stand-in for the sensitive attribute, allowing indirect "
        "discrimination even without using the protected attribute directly."
    ),
    "underrepresentation": (
        "Data Underrepresentation — the disadvantaged group has too few "
        "training examples compared to the majority group, so the model "
        "never learned to make fair decisions for this group."
    ),
    "historical_skew": (
        "Historical Bias — the training data reflects real-world systemic "
        "discrimination from the past. The model learned these unfair "
        "patterns and is now reproducing them in its predictions."
    ),
    "none": "No significant bias pattern detected. The dataset appears fair."
}

TRAINING_FILE = os.path.join(
    os.path.dirname(__file__), '../../data/bias_training_data.json'
)

SEED_DATA = [
    {"spd":0.196,"di":0.358,"top_proxy_r":0.58,"group_ratio":0.49,"proxy_count":1,"rate_variance":0.045,"scenario":4,"cause":"proxy","severity":"high","source":"UCI Adult - gender","auto":False},
    {"spd":0.164,"di":0.360,"top_proxy_r":0.22,"group_ratio":0.12,"proxy_count":0,"rate_variance":0.065,"scenario":4,"cause":"underrepresentation","severity":"high","source":"UCI Adult - race","auto":False},
    {"spd":0.130,"di":0.780,"top_proxy_r":0.24,"group_ratio":0.61,"proxy_count":1,"rate_variance":0.031,"scenario":0,"cause":"proxy","severity":"medium","source":"COMPAS - race","auto":False},
    {"spd":0.100,"di":0.800,"top_proxy_r":0.12,"group_ratio":0.72,"proxy_count":0,"rate_variance":0.018,"scenario":0,"cause":"underrepresentation","severity":"low","source":"COMPAS - sex","auto":False},
    {"spd":0.150,"di":0.680,"top_proxy_r":0.31,"group_ratio":0.43,"proxy_count":1,"rate_variance":0.028,"scenario":5,"cause":"proxy","severity":"medium","source":"German Credit - gender","auto":False},
    {"spd":0.120,"di":0.740,"top_proxy_r":0.18,"group_ratio":0.38,"proxy_count":0,"rate_variance":0.022,"scenario":5,"cause":"historical_skew","severity":"medium","source":"German Credit - age","auto":False},
    {"spd":0.220,"di":0.410,"top_proxy_r":0.45,"group_ratio":0.08,"proxy_count":2,"rate_variance":0.089,"scenario":1,"cause":"proxy","severity":"high","source":"Law School - race","auto":False},
    {"spd":0.180,"di":0.510,"top_proxy_r":0.38,"group_ratio":0.15,"proxy_count":1,"rate_variance":0.071,"scenario":1,"cause":"historical_skew","severity":"high","source":"Law School - gender","auto":False},
    {"spd":0.170,"di":0.560,"top_proxy_r":0.41,"group_ratio":0.31,"proxy_count":2,"rate_variance":0.055,"scenario":2,"cause":"proxy","severity":"high","source":"Healthcare - race","auto":False},
    {"spd":0.090,"di":0.820,"top_proxy_r":0.15,"group_ratio":0.25,"proxy_count":0,"rate_variance":0.019,"scenario":2,"cause":"underrepresentation","severity":"low","source":"Healthcare - gender","auto":False},
    {"spd":0.200,"di":0.480,"top_proxy_r":0.52,"group_ratio":0.41,"proxy_count":2,"rate_variance":0.062,"scenario":3,"cause":"proxy","severity":"high","source":"Hiring - gender","auto":False},
    {"spd":0.140,"di":0.650,"top_proxy_r":0.28,"group_ratio":0.22,"proxy_count":1,"rate_variance":0.041,"scenario":3,"cause":"historical_skew","severity":"medium","source":"Hiring - race","auto":False},
    {"spd":0.080,"di":0.840,"top_proxy_r":0.11,"group_ratio":0.18,"proxy_count":0,"rate_variance":0.014,"scenario":3,"cause":"underrepresentation","severity":"low","source":"Hiring - age","auto":False},
    {"spd":0.234,"di":0.707,"top_proxy_r":0.35,"group_ratio":0.85,"proxy_count":1,"rate_variance":0.037,"scenario":5,"cause":"proxy","severity":"high","source":"Credit Risk - gender","auto":False},
    {"spd":0.045,"di":0.920,"top_proxy_r":0.09,"group_ratio":0.91,"proxy_count":0,"rate_variance":0.008,"scenario":5,"cause":"none","severity":"low","source":"Fair lending dataset","auto":False},
    {"spd":0.012,"di":0.980,"top_proxy_r":0.06,"group_ratio":0.95,"proxy_count":0,"rate_variance":0.003,"scenario":4,"cause":"none","severity":"low","source":"Fair income dataset","auto":False},
    {"spd":0.008,"di":0.990,"top_proxy_r":0.04,"group_ratio":0.88,"proxy_count":0,"rate_variance":0.002,"scenario":3,"cause":"none","severity":"low","source":"Fair hiring dataset","auto":False},
    {"spd":0.300,"di":0.250,"top_proxy_r":0.62,"group_ratio":0.06,"proxy_count":3,"rate_variance":0.110,"scenario":0,"cause":"proxy","severity":"high","source":"Criminal justice complex","auto":False},
    {"spd":0.250,"di":0.320,"top_proxy_r":0.48,"group_ratio":0.09,"proxy_count":2,"rate_variance":0.095,"scenario":5,"cause":"historical_skew","severity":"high","source":"Lending historical","auto":False},
    {"spd":0.180,"di":0.580,"top_proxy_r":0.33,"group_ratio":0.55,"proxy_count":1,"rate_variance":0.044,"scenario":1,"cause":"proxy","severity":"high","source":"Education proxy","auto":False},
]


def _auto_label(spd, di, top_proxy_r, group_ratio, proxy_count, rate_variance):
    spd = abs(spd)
    if spd >= 0.2 or di < 0.5:
        severity = "high"
    elif spd >= 0.1 or di < 0.8:
        severity = "medium"
    elif spd >= 0.05:
        severity = "low"
    else:
        return "none", "low"

    if top_proxy_r >= 0.30 or proxy_count >= 2:
        cause = "proxy"
    elif top_proxy_r < 0.15 and group_ratio < 0.25:
        cause = "underrepresentation"
    elif rate_variance > 0.04 and top_proxy_r < 0.30:
        cause = "historical_skew"
    elif group_ratio < 0.35:
        cause = "underrepresentation"
    else:
        cause = "historical_skew"

    return cause, severity


class BiasPatternClassifier:

    def __init__(self):
        self.cause_model = None
        self.severity_model = None
        self.training_data = []
        self._lock = threading.Lock()
        self._load_or_init()
        self._retrain()

    def _load_or_init(self):
        os.makedirs(os.path.dirname(TRAINING_FILE), exist_ok=True)
        if os.path.exists(TRAINING_FILE):
            with open(TRAINING_FILE, 'r') as f:
                self.training_data = json.load(f)
            print(f"[BiasPatternClassifier] Loaded {len(self.training_data)} examples from disk")
        else:
            self.training_data = list(SEED_DATA)
            self._save()
            print(f"[BiasPatternClassifier] Initialized with {len(self.training_data)} seed examples")

    def _save(self):
        with open(TRAINING_FILE, 'w') as f:
            json.dump(self.training_data, f, indent=2)

    def _retrain(self):
        if len(self.training_data) < 5:
            return
        X = np.array([
            [d['spd'], d['di'], d['top_proxy_r'], d['group_ratio'],
             d['proxy_count'], d['rate_variance'], d['scenario']]
            for d in self.training_data
        ], dtype=float)
        y_cause    = [d['cause']    for d in self.training_data]
        y_severity = [d['severity'] for d in self.training_data]

        self.cause_model = RandomForestClassifier(
            n_estimators=200, max_depth=6,
            min_samples_leaf=1, random_state=42
        )
        self.cause_model.fit(X, y_cause)

        self.severity_model = GradientBoostingClassifier(
            n_estimators=200, max_depth=3,
            learning_rate=0.05, random_state=42
        )
        self.severity_model.fit(X, y_severity)
        print(f"[BiasPatternClassifier] Retrained on {len(self.training_data)} examples")

    def add_training_example(self, spd, di, top_proxy_r, group_ratio,
                              proxy_count, rate_variance, scenario,
                              dataset_name, sensitive_attr):
        scenario_enc = self._encode_scenario(scenario)
        cause, severity = _auto_label(
            spd, di, top_proxy_r, group_ratio, proxy_count, rate_variance
        )
        new_row = {
            "spd":           round(abs(float(spd)), 4),
            "di":            round(float(di), 4),
            "top_proxy_r":   round(float(top_proxy_r), 4),
            "group_ratio":   round(float(group_ratio), 4),
            "proxy_count":   int(proxy_count),
            "rate_variance": round(float(rate_variance), 4),
            "scenario":      scenario_enc,
            "cause":         cause,
            "severity":      severity,
            "source":        f"Auto:{dataset_name}-{sensitive_attr}",
            "auto":          True,
            "timestamp":     datetime.utcnow().isoformat()
        }
        with self._lock:
            is_duplicate = any(
                abs(r['spd'] - new_row['spd']) < 0.01
                and r['scenario'] == new_row['scenario']
                and r['cause'] == new_row['cause']
                for r in self.training_data
            )
            if not is_duplicate:
                self.training_data.append(new_row)
                self._save()
                self._retrain()
                print(f"[AutoLearn] Added {dataset_name}/{sensitive_attr} "
                      f"-> {cause}/{severity}. Total: {len(self.training_data)}")
            else:
                print(f"[AutoLearn] Skipped duplicate: {dataset_name}/{sensitive_attr}")

    def predict(self, spd, di, top_proxy_r, group_ratio,
                proxy_count, rate_variance, scenario) -> dict:
        scenario_enc = self._encode_scenario(scenario)
        X = np.array([[abs(spd), di, top_proxy_r, group_ratio,
                        proxy_count, rate_variance, scenario_enc]])

        if self.cause_model is None:
            cause, severity = _auto_label(
                spd, di, top_proxy_r, group_ratio, proxy_count, rate_variance
            )
            return {
                "predicted_cause":    cause,
                "cause_label":        CAUSE_LABELS.get(cause, cause),
                "confidence_pct":     70.0,
                "top_causes":         [{"cause": cause, "probability": 70.0}],
                "predicted_severity": severity,
                "severity_confidence":70.0,
                "learned":            False,
                "training_examples":  len(self.training_data),
                "note":               "Rule-based fallback"
            }

        cause         = self.cause_model.predict(X)[0]
        cause_proba   = self.cause_model.predict_proba(X)[0]
        cause_classes = self.cause_model.classes_
        severity      = self.severity_model.predict(X)[0]
        sev_proba     = self.severity_model.predict_proba(X)[0]

        sorted_causes = sorted(
            zip(cause_classes, cause_proba), key=lambda x: -x[1]
        )
        return {
            "predicted_cause":    cause,
            "cause_label":        CAUSE_LABELS.get(cause, cause),
            "confidence_pct":     round(float(sorted_causes[0][1]) * 100, 1),
            "top_causes":         [
                {"cause": c, "probability": round(float(p) * 100, 1)}
                for c, p in sorted_causes[:2] if p > 0.05
            ],
            "predicted_severity":  severity,
            "severity_confidence": round(float(max(sev_proba)) * 100, 1),
            "learned":             True,
            "training_examples":   len(self.training_data),
        }

    def get_stats(self) -> dict:
        auto_count = sum(1 for d in self.training_data if d.get('auto'))
        causes = {}
        for d in self.training_data:
            causes[d['cause']] = causes.get(d['cause'], 0) + 1
        return {
            "total_examples":        len(self.training_data),
            "seed_examples":         len(self.training_data) - auto_count,
            "learned_from_uploads":  auto_count,
            "cause_distribution":    causes
        }

    def _encode_scenario(self, scenario: str) -> int:
        s = str(scenario).lower()
        for i, name in enumerate(SCENARIOS):
            if name in s:
                return i
        return 6


_classifier = None

def get_bias_pattern_classifier() -> BiasPatternClassifier:
    global _classifier
    if _classifier is None:
        _classifier = BiasPatternClassifier()
    return _classifier
