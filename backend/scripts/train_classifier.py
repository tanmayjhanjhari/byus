"""
ByUs BiasPatternClassifier Training Script
Run: python backend/scripts/train_classifier.py
"""

import sys, os, json
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
TRAINING_FILE = os.path.join(ROOT, 'data', 'bias_training_data.json')
os.makedirs(os.path.dirname(TRAINING_FILE), exist_ok=True)

SCENARIOS = ['criminal_justice','education','healthcare','hiring','income','lending','other']

def encode_scenario(scenario):
    s = str(scenario).lower()
    for i, name in enumerate(SCENARIOS):
        if name in s: return i
    return 6

if os.path.exists(TRAINING_FILE):
    with open(TRAINING_FILE) as f:
        training_data = json.load(f)
    print(f"[Loader] Found existing file with {len(training_data)} examples")
else:
    training_data = []
    print("[Loader] No existing file -- starting fresh")

def extract_meta_features(df, target_col, sensitive_attr, scenario):
    df = df.copy().dropna(subset=[target_col, sensitive_attr])
    if len(df) < 50:
        raise ValueError(f"Too few rows after cleaning: {len(df)}")
    y = df[target_col]
    if set(y.dropna().unique()).issubset({0,1,0.0,1.0,'0','1'}):
        y_bin = y.astype(float).astype(int)
    elif y.nunique() == 2:
        vals = sorted(y.astype(str).unique())
        y_bin = y.astype(str).map({vals[0]: 0, vals[1]: 1})
    else:
        y_bin = (y > y.median()).astype(int)
    df = df.copy(); df['__y__'] = y_bin
    le = LabelEncoder()
    df['__s__'] = le.fit_transform(df[sensitive_attr].astype(str))
    group_names = {i: n for i, n in enumerate(le.classes_)}
    groups = df['__s__'].unique()
    group_stats = {}
    for g in groups:
        mask = df['__s__'] == g
        group_stats[group_names[g]] = {"count": int(mask.sum()), "positive_rate": float(df.loc[mask,'__y__'].mean())}
    rates = [v["positive_rate"] for v in group_stats.values()]
    counts = [v["count"] for v in group_stats.values()]
    priv_rate = max(rates); unpriv_rate = min(rates)
    spd = priv_rate - unpriv_rate
    di = unpriv_rate / priv_rate if priv_rate > 0 else 1.0
    exclude = {target_col, sensitive_attr, '__y__', '__s__'}
    correlations = []
    for col in df.columns:
        if col in exclude: continue
        try:
            col_data = df[col]
            if col_data.dtype not in ['int64','float64','int32','float32']:
                col_data = LabelEncoder().fit_transform(col_data.fillna('missing').astype(str))
            r = abs(float(np.corrcoef(col_data, df['__s__'])[0,1]))
            if not np.isnan(r): correlations.append(r)
        except: pass
    return {"spd": round(abs(spd),4), "di": round(float(di),4),
            "top_proxy_r": round(max(correlations),4) if correlations else 0.0,
            "group_ratio": round(min(counts)/max(counts),4) if max(counts)>0 else 1.0,
            "proxy_count": int(sum(1 for r in correlations if r > 0.2)),
            "rate_variance": round(float(np.std(rates)),4),
            "scenario": scenario, "group_stats": group_stats}

def auto_label(spd, di, top_proxy_r, group_ratio, proxy_count, rate_variance, **_):
    spd = abs(spd)
    if spd >= 0.2 or di < 0.5: severity = "high"
    elif spd >= 0.1 or di < 0.8: severity = "medium"
    elif spd >= 0.05: severity = "low"
    else: return "none", "low"
    if top_proxy_r >= 0.30 or proxy_count >= 2: cause = "proxy"
    elif top_proxy_r < 0.15 and group_ratio < 0.25: cause = "underrepresentation"
    elif rate_variance > 0.04 and top_proxy_r < 0.30: cause = "historical_skew"
    elif group_ratio < 0.35: cause = "underrepresentation"
    else: cause = "historical_skew"
    return cause, severity

def add_example(features, cause, severity, source, scenario):
    sc = encode_scenario(scenario)
    row = {"spd": features["spd"], "di": features["di"],
           "top_proxy_r": features["top_proxy_r"], "group_ratio": features["group_ratio"],
           "proxy_count": features["proxy_count"], "rate_variance": features["rate_variance"],
           "scenario": sc, "cause": cause, "severity": severity, "source": source, "auto": True}
    is_dup = any(abs(r['spd']-row['spd'])<0.01 and r['scenario']==sc and r['cause']==cause for r in training_data)
    if not is_dup:
        training_data.append(row)
        print(f"  OK {source} -> {cause}/{severity} (SPD={features['spd']:.3f}, DI={features['di']:.3f})")
        return True
    print(f"  SKIP Duplicate: {source}")
    return False

print("\n=== DATASET 1: UCI Adult Income ===")
try:
    from fairlearn.datasets import fetch_adult
    data = fetch_adult(as_frame=True); df = data.frame
    df.columns = [c.strip() for c in df.columns]
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    # fairlearn fetch_adult uses 'class' as target, values are '>50K' / '<=50K'
    target_col = 'class' if 'class' in df.columns else 'income'
    df['income_binary'] = (df[target_col].str.strip().isin(['>50K', 1, '1'])).astype(int)
    # Remove rows with '?' in any string column
    str_cols = df.select_dtypes(include='object').columns
    for sc2 in str_cols:
        df = df[df[sc2] != '?']
    for attr, src, sc in [("sex","UCI Adult - sex","income"),("race","UCI Adult - race","income")]:
        f = extract_meta_features(df,'income_binary',attr,sc); c,s = auto_label(**f); add_example(f,c,s,src,sc)
except Exception as e: print(f"  WARN UCI Adult: {e}")

print("\n=== DATASET 2: COMPAS ===")
try:
    df = pd.read_csv("https://raw.githubusercontent.com/propublica/compas-analysis/master/compas-scores-two-years.csv")
    df = df[df['days_b_screening_arrest'].between(-30,30)]
    df = df[df['is_recid']!=-1]; df = df[df['c_charge_degree']!='O']; df = df[df['score_text']!='N/A']
    for attr, src, sc in [("race","COMPAS - race","criminal_justice"),("sex","COMPAS - sex","criminal_justice")]:
        if attr in df.columns:
            f = extract_meta_features(df,'two_year_recid',attr,sc); c,s = auto_label(**f); add_example(f,c,s,src,sc)
except Exception as e: print(f"  WARN COMPAS: {e}")

print("\n=== DATASET 3: Titanic ===")
try:
    df = pd.read_csv("https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv").dropna(subset=['Survived','Sex','Pclass'])
    df['Sex_str'] = df['Sex']; df['Pclass_str'] = df['Pclass'].astype(str)
    for attr, src, sc in [("Sex_str","Titanic - sex","other"),("Pclass_str","Titanic - class","other")]:
        f = extract_meta_features(df,'Survived',attr,sc); c,s = auto_label(**f); add_example(f,c,s,src,sc)
except Exception as e: print(f"  WARN Titanic: {e}")

print("\n=== DATASET 4: Pima Diabetes ===")
try:
    cols = ['Pregnancies','Glucose','BloodPressure','SkinThickness','Insulin','BMI','DiabetesPedigree','Age','Outcome']
    df = pd.read_csv("https://raw.githubusercontent.com/jbrownlee/Datasets/master/pima-indians-diabetes.csv", names=cols)
    df['AgeGroup'] = pd.cut(df['Age'], bins=[0,30,45,100], labels=['young','middle','senior']); df = df.dropna(subset=['AgeGroup'])
    f = extract_meta_features(df,'Outcome','AgeGroup','healthcare'); c,s = auto_label(**f)
    add_example(f,c,s,"Pima Diabetes - age group","healthcare")
except Exception as e: print(f"  WARN Pima: {e}")

print("\n=== DATASET 5: Bank Marketing ===")
try:
    df = pd.read_csv("https://archive.ics.uci.edu/ml/machine-learning-databases/00222/bank-additional-full.csv", sep=';')
    df['subscribed'] = (df['y']=='yes').astype(int)
    df['age_group'] = pd.cut(df['age'],bins=[0,25,40,60,100],labels=['young','adult','middle','senior'])
    df['marital_str'] = df['marital']; df = df.dropna(subset=['age_group'])
    for attr, src, sc in [("age_group","Bank Marketing - age group","lending"),("marital_str","Bank Marketing - marital","lending")]:
        f = extract_meta_features(df,'subscribed',attr,sc); c,s = auto_label(**f); add_example(f,c,s,src,sc)
except Exception as e: print(f"  WARN Bank: {e}")

print("\n=== DATASET 6: Law School ===")
try:
    from fairlearn.datasets import fetch_lawschool_gpa
    data = fetch_lawschool_gpa(as_frame=True); df = data.frame
    df['pass_bar'] = (df['ugpa'] > df['ugpa'].median()).astype(int)
    for attr, src in [("race1","Law School - race"),("gender","Law School - gender")]:
        if attr in df.columns:
            f = extract_meta_features(df,'pass_bar',attr,'education'); c,s = auto_label(**f); add_example(f,c,s,src,"education")
except Exception as e: print(f"  WARN Law School: {e}")

print("\n=== DATASET 7: ByUs Credit Risk V2 ===")
try:
    csv_path = os.path.join(ROOT,'backend','sample_data','credit_risk_v2.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for attr, src in [("gender","ByUs CreditRisk - gender"),("age_group","ByUs CreditRisk - age_group")]:
            if attr in df.columns:
                f = extract_meta_features(df,'credit_risk',attr,'lending'); c,s = auto_label(**f); add_example(f,c,s,src,"lending")
    else: print(f"  WARN not found: {csv_path}")
except Exception as e: print(f"  WARN CreditRisk: {e}")

print("\n=== DATASET 8: UCI Adult preprocessed ===")
try:
    csv_path = os.path.join(ROOT,'backend','sample_data','adult_income.csv')
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        for attr, src, sc in [("sex","Adult preprocessed - sex","income"),("race","Adult preprocessed - race","income")]:
            if attr in df.columns:
                target = 'income_binary' if 'income_binary' in df.columns else 'income'
                f = extract_meta_features(df,target,attr,sc); c,s = auto_label(**f); add_example(f,c,s,src,sc)
    else: print(f"  WARN adult_income.csv not found")
except Exception as e: print(f"  WARN Adult preprocessed: {e}")

print("\n=== SAVING ===")
with open(TRAINING_FILE,'w') as f: json.dump(training_data, f, indent=2)
print(f"Saved {len(training_data)} total examples -> {TRAINING_FILE}")

print("\n=== RETRAINING ===")
X = np.array([[d['spd'],d['di'],d['top_proxy_r'],d['group_ratio'],d['proxy_count'],d['rate_variance'],d['scenario']] for d in training_data], dtype=float)
y_cause = [d['cause'] for d in training_data]; y_severity = [d['severity'] for d in training_data]
clf_cause = RandomForestClassifier(n_estimators=200,max_depth=6,min_samples_leaf=1,random_state=42)
clf_sev = GradientBoostingClassifier(n_estimators=200,max_depth=3,learning_rate=0.05,random_state=42)
cv = min(5, len(training_data))
cause_acc = cross_val_score(clf_cause,X,y_cause,cv=cv,scoring='accuracy').mean()
sev_acc = cross_val_score(clf_sev,X,y_severity,cv=cv,scoring='accuracy').mean()
print(f"\nModel Performance ({len(training_data)} training examples):")
print(f"   Cause classifier accuracy:    {cause_acc*100:.1f}%")
print(f"   Severity classifier accuracy: {sev_acc*100:.1f}%")
cause_dist = {}
for d in training_data: cause_dist[d['cause']] = cause_dist.get(d['cause'],0)+1
print(f"\nCause distribution:"); [print(f"   {c:<22} {'#'*n} ({n})") for c,n in sorted(cause_dist.items())]
auto_count = sum(1 for d in training_data if d.get('auto'))
print(f"\nSource: seed={len(training_data)-auto_count}, auto={auto_count}")
print(f"\nDONE -- restart backend to use updated training data")
