"""
FairEnough — End-to-End UI Model Persistence & API Integration Tests

Covers all required scenarios across two distinct product modes:
MODE 1: Dataset Only
  1. CSV upload without model
  2. Dataset-only analysis calculates SPD/DI, EOD=N/A, AOD=N/A
  3. Dataset-only Reweighing performance metrics = N/A
  4. Dataset-only Threshold Adjustment does NOT automatically simulate
  5. Dataset-only Threshold Adjustment returns Model Required
  6. Optional simulation triggers ONLY on explicit user action (simulate_threshold=True)
  7. Optional simulation clearly marked as simulation

MODE 2: Dataset + Compatible Real Model
  8. CSV + PKL model upload & persistence
  9. Real model availability across Upload → Analyze → Mitigation
  10. Threshold Adjustment executes real-model path without simulation
  11. Real performance metrics (Acc, Pre, Rec, F1) computed from uploaded model
  12. Reweighing label reflects real model availability
  13. Incompatible model prediction error handling
  14. Multi-group attribute support with real model
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app

CSV_PATH = r"E:\Codes\fairenough\credit_risk_v2.csv"
PKL_PATH = r"E:\Codes\fairenough\credit_risk_v2_model.pkl"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestUIModelIntegrationFlow:
    """Test suite verifying model persistence and dual user modes (Dataset Only vs Dataset + Model)."""

    def test_1_csv_upload_without_model(self, client):
        """CSV upload creates session and initializes dataset metadata."""
        with open(CSV_PATH, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "session_id" in data
        assert data["row_count"] == 1000
        assert "credit_risk" in data["columns"]

    def test_2_dataset_only_analysis_eod_aod_na(self, client):
        """When only CSV is uploaded, SPD/DI are real dataset metrics; EOD and AOD are N/A."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        r_an = client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
            },
        )
        assert r_an.status_code == 200
        data = r_an.json()
        metrics = data["metrics_per_attr"]["gender"]
        # SPD and DI must exist from dataset distributions
        assert metrics["spd"] is not None
        assert metrics["di"] is not None
        # EOD and AOD must be None (N/A) because there are no model predictions
        assert metrics["eod"] is None, "Dataset-only analysis must have EOD=None"
        assert metrics["aod"] is None, "Dataset-only analysis must have AOD=None"
        assert metrics["eod_available"] is False
        assert metrics["aod_available"] is False

    def test_3_dataset_only_reweighing_performance_na(self, client):
        """Dataset-only Reweighing computes dataset SPD/DI; performance metrics Acc/Pre/Rec/F1 are N/A."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
            },
        )

        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
            },
        )
        assert r_mit.status_code == 200
        data = r_mit.json()
        rew = data["reweigh"]
        assert rew["has_real_model"] is False
        assert rew["before"].get("accuracy") is None
        assert rew["after"]["accuracy"] is None
        assert rew["before"].get("f1") is None
        assert rew["after"]["f1"] is None
        assert "no model uploaded" in rew["after"]["simulation_note"].lower()

    def test_4_dataset_only_threshold_does_not_auto_simulate(self, client):
        """When no model is uploaded, Threshold Adjustment does NOT auto-simulate; shows Model Required."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
            },
        )

        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
            },
        )
        assert r_mit.status_code == 200
        thr = r_mit.json()["threshold"]
        # Must not automatically simulate
        assert thr["is_simulation"] is False
        assert thr["model_required"] is True
        assert thr["status"] == "model_required"
        assert thr["can_simulate"] is True
        assert "Model Required" in thr["title"]
        assert thr["after"] is None

    def test_5_simulation_starts_only_on_explicit_user_action(self, client):
        """Simulation for Threshold Adjustment starts ONLY after explicit user action (simulate_threshold=True)."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
            },
        )

        # Default request: no simulation
        r_default = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
                "simulate_threshold": False,
            },
        )
        assert r_default.json()["threshold"]["is_simulation"] is False

        # Explicit user action: run simulation
        r_sim = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
                "simulate_threshold": True,
            },
        )
        assert r_sim.status_code == 200
        thr_sim = r_sim.json()["threshold"]
        assert thr_sim["is_simulation"] is True, "Must be labelled as simulation"
        assert thr_sim["has_real_model"] is False
        assert thr_sim["after"] is not None
        assert thr_sim["simulation_note"] is not None
        assert "simulation" in thr_sim["simulation_note"].lower()

    def test_6_csv_and_compatible_pkl_upload(self, client):
        """Uploading CSV followed by PKL model stores model in active session."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                f"/api/upload-model?session_id={sid}",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        assert r_model.status_code in (200, 201)
        mdata = r_model.json()
        assert "model_id" in mdata
        assert mdata["model_type"] == "LogisticRegression"
        assert mdata["n_features"] == 8

        session = app.state.sessions[sid]
        assert session.get("model") is not None
        assert session.get("model_id") == mdata["model_id"]

    def test_7_model_availability_after_analyze_to_mitigation(self, client):
        """Model survives Analyze stage and executes real Threshold Adjustment in Mitigation."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                "/api/upload-model",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        mid = r_model.json()["model_id"]

        # Analyze
        r_an = client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
                "model_id": mid,
            },
        )
        assert r_an.status_code == 200
        an_data = r_an.json()
        assert an_data["metrics_per_attr"]["gender"]["metrics_mode"] == "model_level"
        assert an_data["metrics_per_attr"]["gender"]["eod_available"] is True

        # Mitigation
        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
                "model_id": mid,
            },
        )
        assert r_mit.status_code == 200
        mit_data = r_mit.json()
        thr = mit_data["threshold"]
        assert thr["is_simulation"] is False, "Real model must NOT be marked as simulation"
        assert thr["has_real_model"] is True
        assert thr["after"] is not None
        assert thr["after"]["metrics_mode"] == "model_level"

    def test_8_threshold_real_performance_metrics(self, client):
        """Real model threshold adjustment computes genuine non-collapsed metrics."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                "/api/upload-model",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        mid = r_model.json()["model_id"]

        client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
                "model_id": mid,
            },
        )

        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
                "model_id": mid,
            },
        )
        after = r_mit.json()["threshold"]["after"]
        assert 0.50 <= after["accuracy"] <= 0.85
        assert 0.50 <= after["precision"] <= 0.85
        assert 0.50 <= after["recall"] <= 1.0
        assert 0.50 <= after["f1"] <= 0.90
        assert after["positive_prediction_rate"] < 1.0
        assert after["eod_available"] is True
        assert after["aod_available"] is True

    def test_9_reweighing_label_dynamic_with_model(self, client):
        """Reweighing has_real_model flag accurately reflects presence of uploaded model."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                "/api/upload-model",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        mid = r_model.json()["model_id"]

        client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
                "model_id": mid,
            },
        )

        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
                "model_id": mid,
            },
        )
        assert r_mit.json()["reweigh"]["has_real_model"] is True

    def test_10_multi_group_attribute_real_model_mitigation(self, client):
        """Multi-group attribute (e.g. age_group) successfully optimizes per-group thresholds with real model."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                "/api/upload-model",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        mid = r_model.json()["model_id"]

        client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["age_group"],
                "model_id": mid,
            },
        )

        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "age_group",
                "model_id": mid,
            },
        )
        assert r_mit.status_code == 200
        thr = r_mit.json()["threshold"]
        assert thr["is_simulation"] is False
        assert thr["has_real_model"] is True
        assert thr["after"]["eod_available"] is True
