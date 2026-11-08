"""Placement estimation.

STRATEGY PATTERN : PredictionStrategy -> RuleBasedStrategy | MLModelStrategy
FACTORY PATTERN  : PredictorFactory chooses the strategy (ML model if a trained one exists).
"""
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import pandas as pd

from core.config import CGPA_SCALE
from core.database import session_scope
from core.models import PlacementPrediction, Student
from core.repositories import PredictionRepository

ARTIFACT_DIR = Path(__file__).resolve().parent.parent / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "placement_model.joblib"
METRICS_PATH = ARTIFACT_DIR / "metrics.json"

FEATURES = ["cgpa_ratio", "projects", "internship", "communication", "extracurricular"]


DEFAULT_THRESHOLDS = (40.0, 70.0)  # (Developing starts, Job Ready starts) in percent

CATEGORY_MEANING = {
    "Needs Improvement": "Your profile is currently weaker than students who were typically placed. Focus on the recommended actions.",
    "Developing": "You are on the right track: stronger than average, but not yet at the level of most placed students.",
    "Job Ready": "Your profile closely resembles students who were typically placed. Keep it current and start applying.",
}


def categorize(score: float, thresholds: tuple = DEFAULT_THRESHOLDS) -> str:
    """Assign a readiness category using percentage cutoffs."""
    developing, job_ready = thresholds
    if score < developing:
        return "Needs Improvement"
    if score < job_ready:
        return "Developing"
    return "Job Ready"


def clamp01(x: float) -> float:
    """Clamp a numeric feature to the inclusive range from zero to one."""
    return max(0.0, min(1.0, x))


def factor_breakdown(st_: Student) -> List[dict]:
    """Score weighted profile factors for explanations across prediction strategies."""
    n_skills = len(st_.skill_list()) + 0.5 * len(st_.learning_list())
    rows = [
        ("CGPA", 30, clamp01((st_.cgpa or 0) / CGPA_SCALE), f"CGPA {st_.cgpa or 0:.2f} / {CGPA_SCALE:g}"),
        ("Projects", 20, clamp01((st_.projects or 0) / 4), f"{st_.projects or 0} completed (4+ is strong)"),
        ("Internships", 15, clamp01((st_.internships or 0) / 2), f"{st_.internships or 0} internship(s) (2+ is strong)"),
        ("Technical skills", 15, clamp01(n_skills / 8), f"{len(st_.skill_list())} confident, {len(st_.learning_list())} learning"),
        ("Certifications", 5, clamp01(len(st_.cert_list()) / 3), f"{len(st_.cert_list())} certification(s)"),
        ("Communication", 10, clamp01((st_.communication or 0) / 10), f"Self-rating {st_.communication or 0} / 10"),
        ("Extracurricular", 5, clamp01((st_.extracurricular or 0) / 10), f"Activity score {st_.extracurricular or 0} / 10"),
    ]
    return [{"name": n, "weight": w, "score": round(s * 100), "points": round(w * s, 1), "note": note}
            for n, w, s, note in rows]


def features_from_student(st_: Student) -> dict:
    """Convert student profile values to the feature names expected by the model."""
    return {
        "cgpa_ratio": clamp01((st_.cgpa or 0) / CGPA_SCALE),
        "projects": st_.projects or 0,
        "internship": 1 if (st_.internships or 0) > 0 else 0,
        "communication": st_.communication or 0,
        "extracurricular": st_.extracurricular or 0,
    }


@dataclass
class PredictionResult:
    """Hold an estimate, its explanatory factors, and model metadata."""

    probability: float
    category: str
    strategy: str
    is_ml: bool
    notice: str
    factors: List[dict] = field(default_factory=list)
    base_rate: Optional[float] = None          # average placement rate in the training data (%)
    thresholds: tuple = DEFAULT_THRESHOLDS

    @property
    def lift(self) -> Optional[float]:
        """Return the estimate as a multiple of the training-data base rate."""
        return round(self.probability / self.base_rate, 1) if self.base_rate else None

    @property
    def strengths(self) -> List[dict]:
        """Return factors scoring at least 70, ordered by weighted points."""
        return sorted([f for f in self.factors if f["score"] >= 70], key=lambda f: -f["points"])

    @property
    def weaknesses(self) -> List[dict]:
        """Return factors below 50, ordered by weighted improvement potential."""
        return sorted([f for f in self.factors if f["score"] < 50], key=lambda f: -(f["weight"] * (100 - f["score"])))


DEMO_NOTICE = ("This is a demonstration estimate, not a validated real-world machine-learning prediction. "
               "It does not guarantee employment.")


class PredictionStrategy(ABC):
    """Define the common interface for placement-estimation strategies."""

    name: str

    @abstractmethod
    def predict(self, student: Student) -> PredictionResult:
        """Estimate a student's placement readiness."""
        ...


class RuleBasedStrategy(PredictionStrategy):
    """Deterministic weighted score (no randomness). Used until a trained model exists."""
    name = "Rule-based demo scorer"

    def predict(self, student: Student) -> PredictionResult:
        """Return a deterministic weighted estimate and factor breakdown."""
        factors = factor_breakdown(student)
        score = round(sum(f["points"] for f in factors), 1)
        return PredictionResult(score, categorize(score), self.name, False, DEMO_NOTICE, factors)


@lru_cache(maxsize=1)
def load_artifact() -> Optional[dict]:
    """Load and cache the trained model artifact, returning ``None`` if unavailable."""
    if not MODEL_PATH.exists():
        return None
    try:
        import joblib
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


@lru_cache(maxsize=4096)
def _ml_probability(values: tuple) -> float:
    """Return the model's placement probability for one feature tuple, cached.

    The readiness page asks the model about ~10 profiles (baseline + what-if levers) on every rerun;
    identical inputs always give identical outputs, so each profile is only scored once per process.
    """
    artifact = load_artifact()
    X = pd.DataFrame([values], columns=artifact["features"])
    return float(artifact["pipeline"].predict_proba(X)[0][1])


def load_metrics() -> Optional[dict]:
    """Read model evaluation metrics from the local artifact directory."""
    if METRICS_PATH.exists():
        try:
            return json.loads(METRICS_PATH.read_text())
        except Exception:
            return None
    return None


class MLModelStrategy(PredictionStrategy):
    """Uses the scikit-learn pipeline trained by ml/train_model.py."""

    def __init__(self, artifact: dict):
        """Initialize the trained pipeline and its feature and threshold metadata."""
        self.pipeline = artifact["pipeline"]
        self.features = artifact["features"]
        self.meta = artifact.get("meta", {})
        self.name = f"scikit-learn {self.meta.get('model_name', 'model')} (calibrated)"
        th = self.meta.get("thresholds") or {}
        self.thresholds = (float(th.get("developing", 40)), float(th.get("job_ready", 70)))
        self.base_rate = round(100 * self.meta["placement_rate"], 1) if self.meta.get("placement_rate") else None

    def predict(self, student: Student) -> PredictionResult:
        """Predict a bounded placement probability and explain the model's context."""
        feats = features_from_student(student)
        prob = _ml_probability(tuple(feats[f] for f in self.features)) * 100
        prob = min(max(prob, 1.0), 99.0)  # never show an absolute 0% or 100%
        auc = self.meta.get("roc_auc")
        src = self.meta.get("data_source", "training data")
        notice = (f"Statistical estimate from a {self.meta.get('model_name', 'scikit-learn')} model trained on "
                  f"'{src}'" + (f" (hold-out ROC-AUC {auc:.2f})" if auc else "") +
                  ". It reflects patterns in historical data, not your individual future, and does not guarantee employment.")
        if self.meta.get("data_source") == "synthetic":
            notice = ("The model is trained on SYNTHETIC practice data, so this is a demonstration estimate. " + notice)
        prob = round(prob, 1)
        return PredictionResult(prob, categorize(prob, self.thresholds), self.name, True, notice,
                                factor_breakdown(student), self.base_rate, self.thresholds)


class PredictorFactory:
    """Choose a trained model when available, otherwise use the rule-based strategy."""

    @staticmethod
    def create(prefer: str = "auto") -> PredictionStrategy:
        """Create a prediction strategy, optionally forcing the rule-based scorer."""
        if prefer != "rule":
            artifact = load_artifact()
            if artifact:
                return MLModelStrategy(artifact)
        return RuleBasedStrategy()


class PredictionService:
    """Expose placement estimates and stored prediction history."""

    @staticmethod
    def estimate(student: Student, save: bool = False) -> PredictionResult:
        """Estimate readiness and optionally persist a changed result."""
        result = PredictorFactory.create().predict(student)
        if save:
            with session_scope() as s:
                repo = PredictionRepository(s)
                last = repo.latest(student.id)
                if not last or abs(last.probability - result.probability) > 0.05 or last.model_name != result.strategy:
                    repo.add(PlacementPrediction(student_id=student.id, probability=result.probability,
                                                 category=result.category, model_name=result.strategy))
        return result

    @staticmethod
    def history(student_id: int):
        """Return saved placement estimates for a student's history."""
        with session_scope() as s:
            return PredictionRepository(s).history(student_id)
