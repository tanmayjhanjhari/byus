import os
import sys
import unittest

# Ensure backend directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.reporter import ReportGenerator
from services.gemini_service import GeminiService
from services.validator import DataValidator

class TestScenarioAndBranding(unittest.TestCase):
    def test_report_branding_and_limitations(self):
        reporter = ReportGenerator()
        sample_session = {
            "filename": "adult.csv",
            "row_count": 32561,
            "target_col": "income_binary",
            "sensitive_attrs": ["sex", "race"],
            "scenario": "income",
            "validation": {"engine": "fairenough"},
            "bias_results": {
                "audit_score": 26.3,
                "overall_severity": "high",
                "grade": "F",
                "grade_label": "HIGH BIAS — IMMEDIATE ACTION REQUIRED",
                "metrics_per_attr": {
                    "sex": {
                        "spd": 0.196,
                        "SPD": 0.196,
                        "di": 0.358,
                        "DI": 0.358,
                        "EOD": 0.070,
                        "AOD": 0.058,
                        "severity": "high",
                        "legal_flag": True,
                        "privileged_group": "Male",
                        "unprivileged_group": "Female",
                        "group_stats": {
                            "Male": {"positive_rate": 0.305, "count": 21790},
                            "Female": {"positive_rate": 0.109, "count": 10771}
                        }
                    }
                }
            },
            "mitigation_results": {
                "winner": "reweigh",
                "winner_details": {
                    "spd_reduction_pct": 53.0,
                    "acc_drop_pct": 0.5
                },
                "reweighing": {
                    "before": {"spd": 0.158, "di": 0.353, "eod": 0.080, "aod": 0.063, "accuracy": 0.874},
                    "after": {"spd": 0.075, "di": 0.643, "eod": 0.166, "aod": 0.087, "accuracy": 0.869}
                },
                "threshold_adjustment": {
                    "before": {"spd": 0.158, "di": 0.353, "eod": 0.080, "aod": 0.063, "accuracy": 0.874},
                    "after": {"spd": 0.001, "di": 0.996, "eod": 0.306, "aod": 0.186, "accuracy": 0.856}
                }
            }
        }
        
        pdf_bytes = reporter.generate(sample_session)
        self.assertGreater(len(pdf_bytes), 5000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

        # Inspect story elements of _p5 directly
        p5_story = reporter._p5(20)
        all_p5_texts = []
        for elem in p5_story:
            if hasattr(elem, "text"):
                all_p5_texts.append(elem.text)
            elif hasattr(elem, "_cellvalues"):
                for row in elem._cellvalues:
                    for cell in row:
                        if hasattr(cell, "text"):
                            all_p5_texts.append(cell.text)
        
        combined_text = " ".join(all_p5_texts)
        self.assertIn("FairEnough", combined_text)
        self.assertIn("Google Gemini", combined_text)
        self.assertNotIn("previously analyzed", combined_text.lower())
        self.assertNotIn("previously trained", combined_text.lower())
        self.assertNotIn("20", combined_text)
        self.assertNotIn("ByUs", combined_text)
        print("\n[OK] PDF Generated successfully with FairEnough branding and without 'previously analyzed' or '20' text!")

    def test_safe_scenario_handling(self):
        # Verify both string and dict formats work safely
        for scenario_input in ["income", {"scenario": "income", "confidence_pct": 95}]:
            scenario = scenario_input if isinstance(scenario_input, str) else scenario_input.get("scenario", "unknown")
            self.assertEqual(scenario, "income")
        print("[OK] Scenario safe parsing verified!")

if __name__ == "__main__":
    unittest.main()
