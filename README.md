# FairEnough

**FairEnough** is an open-source, AI-powered bias auditing platform for machine learning datasets. Upload a dataset, select sensitive attributes, and get a professional fairness audit report — powered by Google Gemini.

---

## What it does

- **Automated Bias Detection** — Computes Statistical Parity Difference (SPD), Disparate Impact (DI), Equal Opportunity Difference (EOD), and Average Odds Difference (AOD) for any sensitive attribute.
- **Audit Score & Grade** — Assigns a 0–100 fairness score and letter grade (A to F).
- **Root Cause Prediction** — Uses a trained ML classifier to identify whether bias stems from proxy features, underrepresentation, or historical skew.
- **Bias Mitigation** — Automatically tests Reweighing, Disparate Impact Remover, and Equalized Odds Post-processing — and picks the best technique.
- **AI Explanations** — Gemini Powered plain-language explanations of all metrics.
- **PDF Reports** — Generates a professional, dark-themed PDF audit report for compliance and HR review.
- **Dashboard** — Save reports to your account, track your average fairness score, and download PDFs of past audits.

---

## Supported Formats

CSV, Excel (.xlsx / .xls), JSON, TSV, Parquet, ZIP

---

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/tanmayjhanjhari/fairlens.git
cd fairlens
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # add your GEMINI_API_KEY and MONGODB_URI
uvicorn main:app --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Environment Variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for AI features |
| `MONGODB_URI` | MongoDB connection string (Atlas or local) |
| `SECRET_KEY` | JWT secret for auth (any random string) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, Tailwind CSS, Framer Motion |
| Backend | FastAPI (Python) |
| AI | Google Gemini (Gemini Powered) |
| Database | MongoDB Atlas |
| ML / Fairness | scikit-learn, AIF360, SHAP |
| PDF Reports | ReportLab |

---

## Usage Guide

See [`DEMO.md`](./DEMO.md) for a full step-by-step walkthrough.

---

## License

MIT
