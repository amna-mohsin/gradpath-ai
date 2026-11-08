"""Run behavior checks against the saved placement model without database access.

Run from the project root with ``python -m ml.sanity_check``.

The checks compare example profiles, probe whether improvements to one input
usually lower predictions, and compare predictions for extreme profiles.
They are diagnostics, not proof of real-world model quality.
"""
import joblib
import numpy as np
import pandas as pd

from ml.train_model import ARTIFACT_DIR, FEATURES


def main():
    """Load the saved artifact and print three prediction-behavior checks."""
    artifact_path = ARTIFACT_DIR / "placement_model.joblib"
    if not artifact_path.is_file():
        raise FileNotFoundError(
            f"No saved model at {artifact_path}. Train a model before running this check."
        )

    artifact = joblib.load(artifact_path)
    model, metadata = artifact["pipeline"], artifact["meta"]
    thresholds = metadata["thresholds"]

    def predict(rows):
        """Return model estimates as percentages for one or more feature rows."""
        return model.predict_proba(pd.DataFrame(rows)[FEATURES])[:, 1] * 100

    def label(probability):
        """Map an estimated percentage to the saved readiness thresholds."""
        if probability >= thresholds["job_ready"]:
            return "Job Ready"
        if probability >= thresholds["developing"]:
            return "Developing"
        return "Needs Improvement"

    print(
        f"Model: {metadata['model_name']} | data: {metadata['data_source']} | "
        f"Job Ready from {thresholds['job_ready']:.0f}%, "
        f"Developing from {thresholds['developing']:.0f}%\n"
    )

    print("CHECK 1 - example students (CGPA is shown as a share of the maximum)")
    people = {
        "Weak profile": dict(cgpa_ratio=0.55, projects=0, internship=0, communication=3, extracurricular=1),
        "Average profile": dict(cgpa_ratio=0.75, projects=2, internship=0, communication=6, extracurricular=5),
        "Good profile": dict(cgpa_ratio=0.85, projects=4, internship=1, communication=8, extracurricular=7),
        "Strong profile": dict(cgpa_ratio=0.95, projects=5, internship=1, communication=9, extracurricular=9),
    }
    probabilities = predict(list(people.values()))
    for (name, _), probability in zip(people.items(), probabilities):
        print(f"  {name:16s} {probability:5.1f}%  {label(probability)}")
    ordered = all(
        probabilities[index] <= probabilities[index + 1] + 1e-9
        for index in range(len(probabilities) - 1)
    )
    print(
        "  ->",
        "PASS: estimates rise from weak to strong"
        if ordered else "WARNING: estimates do not rise steadily from weak to strong",
    )

    print("\nCHECK 2 - improving one thing should not lower the estimate (500 random profiles)")
    rng = np.random.default_rng(0)
    baseline = pd.DataFrame({
        "cgpa_ratio": rng.uniform(0.5, 0.95, 500),
        "projects": rng.integers(0, 6, 500),
        "internship": rng.integers(0, 2, 500),
        "communication": rng.integers(3, 10, 500),
        "extracurricular": rng.integers(0, 10, 500),
    })
    original_probabilities = predict(baseline)
    bumps = {
        "cgpa_ratio": 0.05,
        "projects": 1,
        "internship": 1,
        "communication": 1,
        "extracurricular": 1,
    }
    worst_count = 0
    for feature, step in bumps.items():
        improved = baseline.copy()
        upper_bound = 1.0 if feature in ("cgpa_ratio", "internship") else 10
        improved[feature] = (improved[feature] + step).clip(upper=upper_bound)
        changes = predict(improved) - original_probabilities
        decreasing_count = int((changes < -0.5).sum())
        worst_count = max(worst_count, decreasing_count)
        print(
            f"  more {feature:16s}: estimate dropped by >0.5 points for "
            f"{decreasing_count}/500 profiles (largest drop {changes.min():.1f})"
        )
    print(
        "  ->",
        "PASS: behaves sensibly"
        if worst_count <= 25
        else "WARNING: some inputs behave unexpectedly (small drops can occur with tree models)",
    )

    print("\nCHECK 3 - extreme profiles")
    lowest = predict([dict(
        cgpa_ratio=0.0, projects=0, internship=0, communication=1, extracurricular=0
    )])[0]
    highest = predict([dict(
        cgpa_ratio=1.0, projects=8, internship=1, communication=10, extracurricular=10
    )])[0]
    print(
        f"  lowest profile: {lowest:.1f}%   highest profile: {highest:.1f}%   ->",
        "PASS" if lowest < highest else "WARNING: highest profile does not score above the lowest",
    )


if __name__ == "__main__":
    main()
