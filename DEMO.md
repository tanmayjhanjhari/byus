# FairEnough — How to Use

FairEnough is an AI-powered bias auditing platform. Follow the steps below to audit your dataset for fairness issues and generate a professional PDF report.

---

## Step 1 — Upload Your Dataset

1. Open FairEnough in your browser (`http://localhost:5173` for local dev, or your deployed URL).
2. On the **Upload & Configure** page, drag and drop your dataset file into the upload zone — or click to browse.
3. Supported formats: **CSV, Excel (.xlsx / .xls), JSON, TSV, Parquet, ZIP**.
4. FairEnough will auto-detect the file format, clean missing values, and show you a preprocessing summary.

> **Tip:** You can also load a built-in sample dataset (UCI Adult Income) by clicking "Load Sample Dataset" on the home page.

---

## Step 2 — Configure Your Analysis

After uploading, you'll see the configuration panel:

1. **Target Variable** — Select the column you want to predict (e.g., `income_binary`, `hired`, `loan_approved`).
2. **Sensitive Attributes** — Check the demographic columns to audit for bias (e.g., `sex`, `race`, `age`). Suggested attributes are highlighted automatically.
3. **Detect Scenario** — Click "Detect Scenario with Gemini" to let AI classify your dataset type (income, hiring, lending, healthcare, etc.). You can also override this manually.
4. *(Optional)* Upload a trained `.pkl` or `.joblib` scikit-learn model to audit your model's actual predictions.

---

## Step 3 — Run Bias Analysis

Click **Run Bias Analysis**. FairEnough will:

- Compute fairness metrics: Statistical Parity Difference (SPD), Disparate Impact (DI), Equal Opportunity Difference (EOD), and Average Odds Difference (AOD).
- Assign a bias severity rating: **Low / Medium / High**.
- Give your dataset an **Audit Score (0–100)** and a letter grade (A, B, C, or F).
- Predict the **root cause** of bias (proxy features, underrepresentation, or historical skew) using a trained ML classifier.

---

## Step 4 — Explore Results

On the **Results** page you'll find:

- A breakdown of bias metrics for each sensitive attribute.
- A root cause prediction with confidence percentage.
- An AI-generated plain-language explanation (Gemini Powered).
- SHAP feature importance charts (if a model was uploaded).

---

## Step 5 — Run Bias Mitigation

Go to the **Remediate** page to automatically apply bias mitigation:

- FairEnough tests three techniques: **Reweighing**, **Disparate Impact Remover**, and **Equalized Odds Post-processing**.
- It shows you how much bias each technique reduces, and the trade-off on model accuracy.
- The **best technique** is highlighted with its bias reduction percentage.

---

## Step 6 — Download the Audit Report

On the **Report** page:

1. Review your final Audit Summary — score, grade, severity, scenario, and recommended fix.
2. Click **Download PDF** to get a professional, dark-themed PDF report suitable for compliance or HR review.
3. *(Optional)* Sign in or create a free account to **save the report to your history** and access it from your dashboard anytime.

---

## Step 7 — Your Dashboard

After signing in, your **Dashboard** shows:

- Your average audit score across all analyses.
- A history of all past reports.
- Click any report to view its details — score, grade, root cause, and metrics breakdown.
- Download a PDF for any saved report, even after the session has expired.

---

## Notes

- No data is permanently stored on the server unless you explicitly save a report to your account.
- All analysis happens server-side using your uploaded dataset.
- FairEnough uses **Google Gemini** for AI-powered scenario detection, explanations, and action plans.
