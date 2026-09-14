"""
FairEnough — End-to-End UI Model Persistence & API Integration Tests

Covers all 12 required scenarios:
1. CSV upload without model
2. CSV + compatible PKL model upload
3. Model persistence after upload
4. Model availability on Analyze
5. Model availability after Analyze → Mitigation
6. Mitigation request contains correct model/session/reference
7. Backend receives and resolves the model
8. Threshold Adjustment enters real-model path
9. Real model does not enter simulation path
10. No-model case still correctly enters simulation behavior
11. Incompatible model prediction error handling
12. Multi-group attributes (e.g. age_group) in real UI flow
"""

import os
import pytest
from fastapi.testclient import TestClient
import sys, os
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
    """Test suite verifying end-to-end model persistence between UI stages."""

    def test_1_csv_upload_without_model(self, client):
        """CSV upload creates session and initializes dataset metadata."""
        with open(CSV_PATH, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        assert resp.status_code == 201, f"CSV upload failed: {resp.text}"
        data = resp.json()
        assert "session_id" in data
        assert data["row_count"] == 1000
        assert "credit_risk" in data["columns"]

    def test_2_csv_and_compatible_pkl_upload(self, client):
        """Uploading compatible model links model to session and persists standalone entry."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                f"/api/upload-model?session_id={sid}",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        assert r_model.status_code == 201, f"Model upload failed: {r_model.text}"
        m_data = r_model.json()
        assert "model_id" in m_data
        assert m_data["model_type"] == "LogisticRegression"

        # Verify backend session store persistence
        sessions = app.state.sessions
        assert sid in sessions, "Session must exist in app.state.sessions"
        assert "model" in sessions[sid], "Model must be directly linked to session"
        assert sessions[sid]["model_id"] == m_data["model_id"]

    def test_3_model_persistence_form_only_without_query_param(self, client):
        """Model upload via form data alone (standard FormData dropzone) links model to session."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                "/api/upload-model",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
                data={"session_id": sid},
            )
        assert r_model.status_code == 201
        m_data = r_model.json()
        mid = m_data["model_id"]

        sessions = app.state.sessions
        assert sessions[sid].get("model") is not None, "Model must be linked to session via form data"
        assert sessions[sid].get("model_id") == mid

    def test_4_model_availability_on_analyze(self, client):
        """Analyze generates real predictions from uploaded model and preserves model in session."""
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

        r_an = client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
                "model_id": mid,
            },
        )
        assert r_an.status_code == 200, f"Analyze failed: {r_an.text}"
        an_data = r_an.json()
        assert an_data.get("model_used") is True

        sessions = app.state.sessions
        assert "df_with_predictions" in sessions[sid], "df_with_predictions must be saved in session"
        assert "model" in sessions[sid], "Real model must remain persisted in session after analyze"
        assert sessions[sid]["model_id"] == mid

    def test_5_model_availability_after_analyze_to_mitigation(self, client):
        """When navigating to mitigation, real model remains accessible without re-upload."""
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

        # Call mitigate with session_id (even if frontend didn't supply model_id)
        r_mit = client.post(
            "/api/mitigate",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attr": "gender",
            },
        )
        assert r_mit.status_code == 200, f"Mitigate failed: {r_mit.text}"
        mit_data = r_mit.json()
        thr = mit_data["threshold"]
        assert thr["is_simulation"] is False, "Threshold must use real model, not simulation"
        assert thr["simulation_note"] is None, "Real model threshold must not have simulation_note"

    def test_6_mitigation_request_with_explicit_model_id(self, client):
        """Mitigate request containing model_id resolves and binds model."""
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        with open(PKL_PATH, "rb") as f:
            r_model = client.post(
                "/api/upload-model",
                files={"file": ("credit_risk_v2_model.pkl", f, "application/octet-stream")},
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
        assert r_mit.status_code == 200
        thr = r_mit.json()["threshold"]
        assert thr["is_simulation"] is False
        assert thr["after"]["metrics_mode"] == "model_level"

    def test_7_threshold_adjustment_real_metrics_values(self, client):
        """Real model threshold adjustment calculates genuine, non-collapsed performance metrics."""
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
        assert 0.50 <= after["accuracy"] <= 0.85, f"Unexpected accuracy: {after['accuracy']}"
        assert 0.50 <= after["precision"] <= 0.85
        assert 0.50 <= after["recall"] <= 1.0
        assert 0.50 <= after["f1"] <= 0.90
        assert after["positive_prediction_rate"] < 1.0, "Positive rate must be strictly < 1.0 (no collapse)"
        assert after["eod_available"] is True
        assert after["aod_available"] is True

    def test_8_no_model_case_correctly_enters_simulation(self, client):
        """When no model was provided, threshold adjustment properly labels simulation."""
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
        assert thr["is_simulation"] is True, "No-model case must be labelled is_simulation=True"
        assert thr["simulation_note"] is not None
        assert "GBM simulation" in thr["simulation_note"]

    def test_9_incompatible_model_prediction_error_handling(self, client):
        """Model that fails prediction during analyze reports 500 without corrupting session."""
        from unittest.mock import MagicMock
        with open(CSV_PATH, "rb") as f:
            r_csv = client.post("/api/upload", files={"file": ("credit_risk_v2.csv", f, "text/csv")})
        sid = r_csv.json()["session_id"]

        broken_model = MagicMock()
        broken_model.predict.side_effect = RuntimeError("Broken custom estimator")
        import numpy as np
        broken_model.feature_names_in_ = np.array(["duration", "amount"])

        app.state.sessions["broken_model_test"] = {
            "model": broken_model,
            "model_id": "broken_model_test",
        }

        r_an = client.post(
            "/api/analyze",
            json={
                "session_id": sid,
                "target_col": "credit_risk",
                "sensitive_attrs": ["gender"],
                "model_id": "broken_model_test",
            },
        )
        assert r_an.status_code == 500
        assert "Model prediction failed" in r_an.json()["detail"]

    def test_10_multi_group_attribute_real_model_mitigation(self, client):
        """Multi-group attribute (age_group, 4 categories) executes real model threshold adjustment."""
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
        assert len(thr["thresholds"]) == 4, f"Expected 4 age group thresholds, got {len(thr['thresholds'])}"
        assert thr["after"]["positive_prediction_rate"] < 1.0
