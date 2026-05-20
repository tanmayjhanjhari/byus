from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from bson import ObjectId
from typing import Optional
import json
from ..database import get_db
from ..routers.auth import require_user, get_current_user
from ..services.auth_service import serialize_doc

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.post("/save")
async def save_report(
    body: dict,
    user: dict = Depends(require_user)
):
    """Save a completed analysis to user's history."""
    db = get_db()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    # Check not already saved
    existing = await db.reports.find_one({"session_id": session_id})
    if existing:
        return {"message": "Already saved.", "report_id": str(existing["_id"])}

    report_doc = {
        "user_id":       ObjectId(user["id"]),
        "session_id":    session_id,
        "created_at":    datetime.utcnow(),
        # Dataset info
        "filename":      body.get("filename", "Unknown"),
        "row_count":     body.get("row_count", 0),
        "target_col":    body.get("target_col", ""),
        "sensitive_attrs": body.get("sensitive_attrs", []),
        "scenario":      body.get("scenario", "Other"),
        # Results
        "audit_score":   body.get("audit_score"),
        "grade":         body.get("grade"),
        "overall_severity": body.get("overall_severity"),
        "metrics_summary":  body.get("metrics_summary", {}),
        "winner_technique": body.get("winner_technique"),
        "bias_reduction_pct": body.get("bias_reduction_pct"),
        # Full data for re-viewing
        "full_metrics":      body.get("full_metrics", {}),
        "mitigation_results": body.get("mitigation_results", {}),
        "pattern_predictions": body.get("pattern_predictions", {}),
        "pdf_available": True,
    }

    result = await db.reports.insert_one(report_doc)
    report_id = str(result.inserted_id)

    # Update user summary stats
    all_scores = await db.reports.find(
        {"user_id": ObjectId(user["id"])},
        {"audit_score": 1}
    ).to_list(1000)
    scores = [r["audit_score"] for r in all_scores if r.get("audit_score")]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    await db.users.update_one(
        {"_id": ObjectId(user["id"])},
        {"$set": {
            "total_analyses": len(all_scores),
            "avg_audit_score": avg_score,
            "last_active": datetime.utcnow()
        }}
    )

    return {"message": "Report saved.", "report_id": report_id}

@router.get("/history")
async def get_history(
    user: dict = Depends(require_user),
    limit: int = Query(20, le=100),
    skip: int = Query(0)
):
    """Get user's analysis history, newest first."""
    db = get_db()
    cursor = db.reports.find(
        {"user_id": ObjectId(user["id"])},
        {
            "full_metrics": 0,   # exclude heavy fields from list view
            "mitigation_results": 0
        }
    ).sort("created_at", -1).skip(skip).limit(limit)

    reports = []
    async for doc in cursor:
        reports.append(serialize_doc(doc))

    total = await db.reports.count_documents(
        {"user_id": ObjectId(user["id"])}
    )

    return {
        "reports": reports,
        "total": total,
        "has_more": (skip + limit) < total
    }

@router.get("/history/{report_id}")
async def get_report_detail(
    report_id: str,
    user: dict = Depends(require_user)
):
    """Get full detail of a specific past report."""
    db = get_db()
    try:
        doc = await db.reports.find_one({
            "_id": ObjectId(report_id),
            "user_id": ObjectId(user["id"])
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid report ID.")
    if not doc:
        raise HTTPException(status_code=404, detail="Report not found.")
    return serialize_doc(doc)

@router.get("/summary")
async def get_summary(user: dict = Depends(require_user)):
    """Dashboard summary for the logged-in user."""
    db = get_db()
    uid = ObjectId(user["id"])

    total = await db.reports.count_documents({"user_id": uid})
    if total == 0:
        return {
            "total_analyses": 0,
            "avg_audit_score": None,
            "most_common_bias_cause": None,
            "scenarios_analyzed": [],
            "recent_reports": [],
            "grade_distribution": {}
        }

    # Aggregate stats
    pipeline = [
        {"$match": {"user_id": uid}},
        {"$group": {
            "_id": None,
            "avg_score": {"$avg": "$audit_score"},
            "grades": {"$push": "$grade"},
            "scenarios": {"$push": "$scenario"},
        }}
    ]
    agg = await db.reports.aggregate(pipeline).to_list(1)
    stats = agg[0] if agg else {}

    # Grade distribution
    grades = stats.get("grades", [])
    grade_dist = {}
    for g in grades:
        if g:
            grade_dist[g] = grade_dist.get(g, 0) + 1

    # Unique scenarios
    scenarios = list(set(s for s in stats.get("scenarios", []) if s))

    # Most common cause from pattern predictions
    cause_counts = {}
    async for doc in db.reports.find(
        {"user_id": uid},
        {"pattern_predictions": 1}
    ):
        for attr, pred in doc.get("pattern_predictions", {}).items():
            cause = pred.get("predicted_cause")
            if cause and cause != "none":
                cause_counts[cause] = cause_counts.get(cause, 0) + 1
    most_common_cause = max(cause_counts, key=cause_counts.get) if cause_counts else None

    # Recent 5 reports
    recent_cursor = db.reports.find(
        {"user_id": uid},
        {"full_metrics": 0, "mitigation_results": 0}
    ).sort("created_at", -1).limit(5)
    recent = [serialize_doc(doc) async for doc in recent_cursor]

    return {
        "total_analyses":       total,
        "avg_audit_score":      round(stats.get("avg_score", 0), 1),
        "most_common_bias_cause": most_common_cause,
        "scenarios_analyzed":   scenarios,
        "recent_reports":       recent,
        "grade_distribution":   grade_dist
    }

@router.delete("/history/{report_id}")
async def delete_report(
    report_id: str,
    user: dict = Depends(require_user)
):
    db = get_db()
    result = await db.reports.delete_one({
        "_id": ObjectId(report_id),
        "user_id": ObjectId(user["id"])
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"message": "Report deleted."}
