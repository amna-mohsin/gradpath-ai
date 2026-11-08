"""Train, tune, calibrate, and evaluate the placement-readiness model.

Usage from the project root:
    python -m ml.train_model --data ml/data/placement.csv
    python -m ml.train_model --data ml/data/placement.csv --fast
    python -m ml.train_model --data ml/data/placement.csv --compare-features
    python -m ml.train_model --synthetic

The training workflow keeps a stratified test split untouched while it tunes
three candidate models, calibrates the selected model, and chooses a decision
threshold using out-of-fold training predictions.
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.ensemble import (GradientBoostingClassifier, HistGradientBoostingClassifier,
                              RandomForestClassifier)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_recall_curve, precision_score, recall_score,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import (RandomizedSearchCV, StratifiedKFold, cross_val_predict,
                                     cross_val_score, cross_validate, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

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
OVERFIT_PENALTY = 0.25


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


def build_models():
    """Return each candidate estimator with its regularized tuning search space."""
    return {
        "Logistic Regression": (
            Pipeline([
                ("scale", StandardScaler()),
                ("poly", PolynomialFeatures(include_bias=False)),
                ("scale2", StandardScaler()),
                ("clf", LogisticRegression(max_iter=5000, class_weight="balanced")),
            ]),
            {"poly__degree": [1, 2], "clf__C": [0.003, 0.01, 0.03, 0.1, 0.3, 1, 3, 10]},
        ),
        "Random Forest": (
            Pipeline([
                ("scale", StandardScaler()),
                ("clf", RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1)),
            ]),
            {"clf__n_estimators": [200, 300, 500], "clf__max_depth": [4, 6, 8, 10],
             "clf__min_samples_leaf": [3, 5, 10, 20], "clf__max_features": ["sqrt", 0.8]},
        ),
        "Gradient Boosting (monotonic)": (
            Pipeline([
                ("scale", StandardScaler()),
                ("clf", HistGradientBoostingClassifier(
                    monotonic_cst=[1] * len(FEATURES), random_state=42
                )),
            ]),
            {"clf__max_iter": [100, 200, 300], "clf__learning_rate": [0.03, 0.05, 0.1],
             "clf__max_depth": [2, 3, 4], "clf__min_samples_leaf": [20, 40, 80],
             "clf__l2_regularization": [0.0, 0.1, 1.0]},
        ),
    }


def _grid_size(grid):
    """Return the number of possible parameter combinations in a search grid."""
    return int(np.prod([len(values) for values in grid.values()]))


def _fit_candidate(pipe, grid, X, y, cv, fast, iters):
    """Fit one candidate and return its estimator and train/validation ROC-AUC."""
    if fast:
        scores = cross_validate(pipe, X, y, cv=cv, scoring="roc_auc",
                                return_train_score=True, n_jobs=-1)
        fitted = pipe.fit(X, y)
        return (fitted, float(scores["test_score"].mean()), float(scores["test_score"].std()),
                float(scores["train_score"].mean()), {})

    search = RandomizedSearchCV(
        pipe, grid, n_iter=min(iters, _grid_size(grid)), cv=cv, scoring="roc_auc",
        random_state=42, n_jobs=-1, return_train_score=True,
    )
    search.fit(X, y)
    best_index = search.best_index_
    params = {
        key.split("__")[-1]: value.item() if isinstance(value, np.generic) else value
        for key, value in search.best_params_.items()
    }
    return (
        search.best_estimator_,
        float(search.cv_results_["mean_test_score"][best_index]),
        float(search.cv_results_["std_test_score"][best_index]),
        float(search.cv_results_["mean_train_score"][best_index]),
        params,
    )


def _categorize(p_pct, dev, ready):
    """Map estimated placement percentages into the three readiness categories."""
    return np.where(p_pct >= ready, "Job Ready", np.where(p_pct >= dev, "Developing", "Needs Improvement"))


def fit_verdict(train_auc, test_auc):
    """Describe train/test AUC patterns as a cautionary fit diagnostic."""
    gap = train_auc - test_auc
    if test_auc < 0.70:
        return "Possible underfit: discrimination is weak on held-out data; review the data and features."
    if gap > 0.08:
        return "Possible overfit: training performance is notably higher than held-out performance."
    return "Good fit check: training and held-out scores are reasonably close."


def train(data, source, fast=False, iters=15):
    """Compare, calibrate, evaluate, and persist the placement model and metrics."""
    if not fast and iters < 1:
        raise ValueError("The number of tuning iterations must be at least 1.")
    X, y = data[FEATURES], data["target"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    cv = StratifiedKFold(5, shuffle=True, random_state=42)

    candidates = build_models()
    if not fast:
        print(f"Tuning all three models ({iters} settings per model, up to 5 folds each)...")
    fitted, comparison = {}, {}
    for name, (pipe, grid) in candidates.items():
        estimator, validation_auc, validation_std, training_auc, params = _fit_candidate(
            pipe, grid, X_tr, y_tr, cv, fast, iters
        )
        gap = max(training_auc - validation_auc, 0.0)
        comparison[name] = {
            "cv_roc_auc_mean": round(validation_auc, 4),
            "cv_roc_auc_std": round(validation_std, 4),
            "train_roc_auc": round(training_auc, 4),
            "gap": round(gap, 4),
            "selection_score": round(validation_auc - OVERFIT_PENALTY * gap, 4),
            "best_params": params,
        }
        fitted[name] = estimator

    print(f"\n{'Model':20s} {'Train AUC':>10s} {'Valid AUC':>10s} {'Gap':>7s} {'Score':>7s}")
    for name, result in comparison.items():
        print(f"{name:20s} {result['train_roc_auc']:10.3f} {result['cv_roc_auc_mean']:10.3f} "
              f"{result['gap']:7.3f} {result['selection_score']:7.3f}   {result['best_params']}")
    best = max(comparison, key=lambda name: comparison[name]["selection_score"])
    best_pipe = fitted[best]

    # Out-of-fold calibrated probabilities on the TRAINING data -> choose the decision threshold
    oof = cross_val_predict(CalibratedClassifierCV(clone(best_pipe), method="isotonic", cv=3),
                            X_tr, y_tr, cv=cv, method="predict_proba")[:, 1]
    prec, rec, thr = precision_recall_curve(y_tr, oof)
    f1s = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-9, None)
    # Prefer the lowest threshold within 1% of the best F1 to avoid an unstable extreme cutoff.
    near_best = np.flatnonzero(f1s >= 0.99 * f1s.max())
    t_best = float(thr[near_best[0]])

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

    train_auc = roc_auc_score(y_tr, model.predict_proba(X_tr)[:, 1])
    test_auc = roc_auc_score(y_te, proba)
    fit_check = {
        "train_roc_auc": round(float(train_auc), 4),
        "cv_roc_auc": comparison[best]["cv_roc_auc_mean"],
        "test_roc_auc": round(float(test_auc), 4),
        "gap": round(float(train_auc - test_auc), 4),
    }
    fit_check["verdict"] = fit_verdict(fit_check["train_roc_auc"], fit_check["test_roc_auc"])

    imp = permutation_importance(model, X_te, y_te, scoring="roc_auc", n_repeats=10, random_state=42)
    fpr, tpr, _ = roc_curve(y_te, proba)
    keep = np.unique(np.linspace(0, len(fpr) - 1, 60).astype(int))
    frac_pos, mean_pred = calibration_curve(y_te, proba, n_bins=8, strategy="quantile")

    metrics = {
        "trainer_version": 2,
        "model_name": best, "data_source": source, "n_rows": int(len(data)), "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)), "placement_rate": round(base_rate, 4), "tuned": not fast,
        "decision_threshold": round(t_best, 4), "thresholds": {"developing": dev, "job_ready": ready},
        "accuracy": round(accuracy_score(y_te, pred), 4), "precision": round(precision_score(y_te, pred, zero_division=0), 4),
        "recall": round(recall_score(y_te, pred, zero_division=0), 4), "f1": round(f1_score(y_te, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_te, proba), 4), "avg_precision": round(average_precision_score(y_te, proba), 4),
        "brier_score": round(brier_score_loss(y_te, proba), 4),
        "baseline_accuracy": round(1 - float(y_te.mean()), 4),
        "confusion_matrix": confusion_matrix(y_te, pred).tolist(), "comparison": comparison, "features": FEATURES,
        "fit_check": fit_check,
        "feature_importance": {f: round(float(v), 4) for f, v in zip(FEATURES, imp.importances_mean)},
        "roc_curve": {"fpr": [round(float(x), 4) for x in fpr[keep]], "tpr": [round(float(x), 4) for x in tpr[keep]]},
        "calibration": {"predicted": [round(float(x), 4) for x in mean_pred], "actual": [round(float(x), 4) for x in frac_pos]},
        "category_outcomes": outcomes,
    }
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": model, "features": FEATURES, "meta": metrics}, ARTIFACT_DIR / "placement_model.joblib")
    (ARTIFACT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"\nBest model: {best} (calibrated) | decision threshold {t_best:.2f}")
    print(f"FIT CHECK -> train AUC {fit_check['train_roc_auc']:.3f} | validation AUC {fit_check['cv_roc_auc']:.3f} | "
          f"test AUC {fit_check['test_roc_auc']:.3f} | gap {fit_check['gap']:.3f}")
    print("           ", fit_check["verdict"])
    print(f"TEST SET -> accuracy {metrics['accuracy']:.3f} (always-'No' baseline {metrics['baseline_accuracy']:.3f}) | "
          f"precision {metrics['precision']:.3f} | recall {metrics['recall']:.3f} | F1 {metrics['f1']:.3f} | "
          f"ROC-AUC {metrics['roc_auc']:.3f} | Brier {metrics['brier_score']:.3f}")
    print("Placed rate by readiness category (test set):", {k: v for k, v in outcomes.items()})
    print(f"Saved to {ARTIFACT_DIR}")
    return metrics


def compare_feature_sets(path):
    """Compare selected optional numeric CSV fields without changing model inputs."""
    raw = pd.read_csv(path)
    base = load_kaggle(path)
    normalized_columns = {column.strip().lower().replace(" ", "_"): column for column in raw.columns}
    optional_features = {
        "Previous semester result": "prev_sem_result",
        "Academic performance": "academic_performance",
        "IQ (diagnostic only)": "iq",
    }
    X_base, y = base[FEATURES], base["target"]
    cv = StratifiedKFold(5, shuffle=True, random_state=42)
    estimator = GradientBoostingClassifier(
        n_estimators=150, max_depth=3, learning_rate=0.1, subsample=0.85, random_state=42
    )

    baseline = cross_val_score(estimator, X_base, y, cv=cv, scoring="roc_auc", n_jobs=-1)
    print("\nFeature-set comparison (same Gradient Boosting estimator, 5-fold ROC-AUC):")
    print(f"  {'Current five features':45s} {baseline.mean():.3f} +/- {baseline.std():.3f}")

    available = {}
    for label, normalized_name in optional_features.items():
        column_name = normalized_columns.get(normalized_name)
        if column_name is not None:
            values = pd.to_numeric(raw.loc[base.index, column_name], errors="coerce")
            if values.notna().all():
                available[label] = values
            else:
                print(f"  Skipped {label}: values are missing or non-numeric.")
    for label, values in available.items():
        scores = cross_val_score(
            estimator, X_base.assign(**{label: values}), y, cv=cv, scoring="roc_auc", n_jobs=-1
        )
        print(f"  {'Current features + ' + label:45s} {scores.mean():.3f} +/- {scores.std():.3f}")

    combined = [label for label in available if label != "IQ (diagnostic only)"]
    if combined:
        combined_features = {label: available[label] for label in combined}
        scores = cross_val_score(
            estimator, X_base.assign(**combined_features), y, cv=cv, scoring="roc_auc", n_jobs=-1
        )
        print(f"  {'Current features + all non-IQ extras':45s} {scores.mean():.3f} +/- {scores.std():.3f}")
    print("\nThis is a diagnostic comparison, not proof that a feature is appropriate or causal.")
    print("Review data leakage, fairness, and whether a feature is available and appropriate at prediction time.")
    if "IQ (diagnostic only)" in available:
        print("IQ is sensitive personal data. Do not collect or use it for student placement decisions.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="Path to the Kaggle CSV")
    ap.add_argument("--synthetic", action="store_true", help="Use generated practice data")
    ap.add_argument("--fast", action="store_true", help="Skip hyper-parameter search")
    ap.add_argument("--iters", type=int, default=15, help="Settings tried per model during tuning (default: 15)")
    ap.add_argument("--compare-features", action="store_true",
                    help="Check whether selected optional CSV columns add cross-validated signal")
    args = ap.parse_args()
    if args.compare_features:
        if not args.data:
            ap.error("--compare-features requires --data PATH")
        compare_feature_sets(args.data)
    elif args.data:
        train(load_kaggle(args.data), source=f"Kaggle CSV ({Path(args.data).name})",
              fast=args.fast, iters=args.iters)
    elif args.synthetic:
        train(make_synthetic(), source="synthetic", fast=args.fast, iters=args.iters)
    else:
        ap.error("Provide --data PATH or --synthetic")
