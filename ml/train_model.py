"""Train, tune, calibrate and evaluate the placement model.

Usage (from the project root):
    python -m ml.train_model --data ml/data/placement.csv          # full run (tuning, ~2-5 min)
    python -m ml.train_model --data ml/data/placement.csv --fast   # skip hyper-parameter search
    pythopip install -r requirements.tpip install -r requirements.txtxtn -m ml.train_model --synthetic                           # practice data (clearly labelled)

What it does
 1. Splits the data 80/20 (stratified). The 20% TEST set is never used for any decision.
 2. Tunes Random Forest and Gradient Boosting with a randomised search (cross-validation on the training part).
 3. Picks the best model by 5-fold cross-validated ROC-AUC.
 4. CALIBRATES it so a prediction of 30% really means "about 30 in 100 such students were placed".
 5. Chooses the decision threshold that maximises F1 (using out-of-fold predictions, not the test set).
 6. Evaluates once on the untouched test set and saves metrics, curves and category outcomes.
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import (RandomizedSearchCV, StratifiedKFold, cross_val_predict,
                                     cross_val_score, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
FEATURES = ["cgpa_ratio", "projects", "internship", "communication", "extracurricular"]
ALIASES = {
    "cgpa": ["cgpa", "gpa"],
    "internship": ["internship_experience", "internships", "internship"],
    "projects": ["projects_completed", "projects", "project_count"],
    "communication": ["communication_skills", "communication"],
    "extracurricular": ["extra_curricular_score", "extracurricular_score", "extra_curricular", "extracurricular"],
    "target": ["placement", "placed", "status"],
}
CATEGORIES = ["Needs Improvement", "Developing", "Job Ready"]


def _find(df, key):
    """Resolve a logical feature name to a matching CSV column alias."""
    cols = {c.strip().lower().replace(" ", "_"): c for c in df.columns}
    for alias in ALIASES[key]:
        if alias in cols:
            return cols[alias]
    raise KeyError(f"Could not find a column for '{key}'. Columns in your CSV: {list(df.columns)}. "
                   f"Edit ALIASES in ml/train_model.py to match.")


def _yes_no(series):
    """Convert common placement and internship labels into binary values."""
    return series.astype(str).str.strip().str.lower().map(
        {"yes": 1, "y": 1, "placed": 1, "true": 1, "1": 1, "no": 0, "n": 0, "not placed": 0, "false": 0, "0": 0})


def load_kaggle(path):
    """Load and normalize the placement CSV into the trainer's feature schema."""
    raw = pd.read_csv(path)
    cgpa = pd.to_numeric(raw[_find(raw, "cgpa")], errors="coerce")
    scale = 10.0 if cgpa.max() > 4.5 else 4.0
    data = pd.DataFrame({
        "cgpa_ratio": (cgpa / scale).clip(0, 1),
        "projects": pd.to_numeric(raw[_find(raw, "projects")], errors="coerce"),
        "internship": _yes_no(raw[_find(raw, "internship")]),
        "communication": pd.to_numeric(raw[_find(raw, "communication")], errors="coerce"),
        "extracurricular": pd.to_numeric(raw[_find(raw, "extracurricular")], errors="coerce"),
        "target": _yes_no(raw[_find(raw, "target")]),
    }).dropna()
    data["target"] = data["target"].astype(int)
    print(f"Loaded {len(data)} rows (CGPA scale detected: {scale:g}). Placement rate: {data['target'].mean():.1%}")
    return data


def make_synthetic(n=3000, seed=42):
    """Generate labelled practice data for local training and demonstrations."""
    rng = np.random.default_rng(seed)
    d = pd.DataFrame({
        "cgpa_ratio": rng.uniform(0.5, 1.0, n), "projects": rng.poisson(2.2, n).clip(0, 8),
        "internship": rng.binomial(1, 0.45, n), "communication": rng.integers(3, 11, n),
        "extracurricular": rng.integers(0, 11, n),
    })
    z = (7 * (d.cgpa_ratio - 0.75) + 0.35 * d.projects + 1.0 * d.internship
         + 0.25 * (d.communication - 6) + 0.08 * (d.extracurricular - 5) + rng.normal(0, 0.9, n) - 0.8)
    d["target"] = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(int)
    return d


def _search(pipe, grid, X, y, cv, n_iter=12):
    """Tune a model pipeline by cross-validated ROC-AUC and return the winner."""
    s = RandomizedSearchCV(pipe, grid, n_iter=n_iter, cv=3, scoring="roc_auc", random_state=42, n_jobs=-1)
    return s.fit(X, y).best_estimator_


def _categorize(p_pct, dev, ready):
    """Map estimated placement percentages into the three readiness categories."""
    return np.where(p_pct >= ready, "Job Ready", np.where(p_pct >= dev, "Developing", "Needs Improvement"))


def train(data, source, fast=False):
    """Compare, calibrate, evaluate, and persist the placement model and metrics."""
    X, y = data[FEATURES], data["target"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    cv = StratifiedKFold(5, shuffle=True, random_state=42)

    pipes = {
        "Logistic Regression": Pipeline([("scale", StandardScaler()),
                                         ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))]),
        "Random Forest": Pipeline([("scale", StandardScaler()),
                                   ("clf", RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=3,
                                                                  class_weight="balanced", random_state=42, n_jobs=-1))]),
        "Gradient Boosting": Pipeline([("scale", StandardScaler()),
                                       ("clf", GradientBoostingClassifier(random_state=42))]),
    }
    if not fast:
        print("Tuning Random Forest and Gradient Boosting (this takes a few minutes)...")
        pipes["Random Forest"] = _search(pipes["Random Forest"], {
            "clf__n_estimators": [200, 300, 500], "clf__max_depth": [4, 6, 8, 12, None],
            "clf__min_samples_leaf": [1, 3, 5, 10], "clf__max_features": ["sqrt", 0.8]}, X_tr, y_tr, cv)
        pipes["Gradient Boosting"] = _search(pipes["Gradient Boosting"], {
            "clf__n_estimators": [100, 200, 300], "clf__learning_rate": [0.03, 0.05, 0.1],
            "clf__max_depth": [2, 3, 4], "clf__subsample": [0.7, 0.85, 1.0]}, X_tr, y_tr, cv)

    comparison = {}
    for name, pipe in pipes.items():
        sc = cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring="roc_auc")
        comparison[name] = {"cv_roc_auc_mean": round(float(sc.mean()), 4), "cv_roc_auc_std": round(float(sc.std()), 4)}
        print(f"{name:20s} CV ROC-AUC = {sc.mean():.3f} +/- {sc.std():.3f}")
    best = max(comparison, key=lambda k: comparison[k]["cv_roc_auc_mean"])
    best_pipe = pipes[best]

    # Out-of-fold calibrated probabilities on the TRAINING data -> choose the decision threshold
    oof = cross_val_predict(CalibratedClassifierCV(clone(best_pipe), method="isotonic", cv=3),
                            X_tr, y_tr, cv=cv, method="predict_proba")[:, 1]
    prec, rec, thr = precision_recall_curve(y_tr, oof)
    f1s = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-9, None)
    t_best = float(thr[int(np.argmax(f1s))])

    model = CalibratedClassifierCV(clone(best_pipe), method="isotonic", cv=5).fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    pred = (proba >= t_best).astype(int)

    base_rate = float(y_tr.mean())
    ready = round(100 * t_best, 1)
    dev = round(min(100 * base_rate, 0.6 * ready), 1)
    cats = _categorize(proba * 100, dev, ready)
    outcomes = {}
    for c in CATEGORIES:
        mask = cats == c
        outcomes[c] = {"n": int(mask.sum()), "placed_rate": round(float(y_te[mask].mean()), 4) if mask.sum() else None}

    imp = permutation_importance(model, X_te, y_te, scoring="roc_auc", n_repeats=10, random_state=42)
    fpr, tpr, _ = roc_curve(y_te, proba)
    keep = np.unique(np.linspace(0, len(fpr) - 1, 60).astype(int))
    frac_pos, mean_pred = calibration_curve(y_te, proba, n_bins=8, strategy="quantile")

    metrics = {
        "model_name": best, "data_source": source, "n_rows": int(len(data)), "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)), "placement_rate": round(base_rate, 4), "tuned": not fast,
        "decision_threshold": round(t_best, 4), "thresholds": {"developing": dev, "job_ready": ready},
        "accuracy": round(accuracy_score(y_te, pred), 4), "precision": round(precision_score(y_te, pred, zero_division=0), 4),
        "recall": round(recall_score(y_te, pred, zero_division=0), 4), "f1": round(f1_score(y_te, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_te, proba), 4), "avg_precision": round(average_precision_score(y_te, proba), 4),
        "brier_score": round(brier_score_loss(y_te, proba), 4),
        "baseline_accuracy": round(1 - float(y_te.mean()), 4),
        "confusion_matrix": confusion_matrix(y_te, pred).tolist(), "comparison": comparison, "features": FEATURES,
        "feature_importance": {f: round(float(v), 4) for f, v in zip(FEATURES, imp.importances_mean)},
        "roc_curve": {"fpr": [round(float(x), 4) for x in fpr[keep]], "tpr": [round(float(x), 4) for x in tpr[keep]]},
        "calibration": {"predicted": [round(float(x), 4) for x in mean_pred], "actual": [round(float(x), 4) for x in frac_pos]},
        "category_outcomes": outcomes,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "features": FEATURES, "meta": metrics}, ARTIFACT_DIR / "placement_model.joblib")
    (ARTIFACT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"\nBest model: {best} (calibrated) | decision threshold {t_best:.2f}")
    print(f"TEST SET -> accuracy {metrics['accuracy']:.3f} (always-'No' baseline {metrics['baseline_accuracy']:.3f}) | "
          f"precision {metrics['precision']:.3f} | recall {metrics['recall']:.3f} | F1 {metrics['f1']:.3f} | "
          f"ROC-AUC {metrics['roc_auc']:.3f} | Brier {metrics['brier_score']:.3f}")
    print("Placed rate by readiness category (test set):", {k: v for k, v in outcomes.items()})
    print(f"Saved to {ARTIFACT_DIR}")
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="Path to the Kaggle CSV")
    ap.add_argument("--synthetic", action="store_true", help="Use generated practice data")
    ap.add_argument("--fast", action="store_true", help="Skip hyper-parameter search")
    args = ap.parse_args()
    if args.data:
        train(load_kaggle(args.data), source=f"Kaggle CSV ({Path(args.data).name})", fast=args.fast)
    elif args.synthetic:
        train(make_synthetic(), source="synthetic", fast=args.fast)
    else:
        ap.error("Provide --data PATH or --synthetic")
