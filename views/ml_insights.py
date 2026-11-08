"""Career officer page explaining trained-model metrics and limitations."""
import pandas as pd
import streamlit as st

from services.prediction_service import load_metrics
from ui import charts, insights
from ui.components import empty_state, html_table, insight, metric_row, page_header


def render():
    """Render model metrics, evaluation charts, and interpretation notes."""
    page_header("How the estimate works", "How the model was built, how well it performs on unseen students, and its limits.")
    m = load_metrics()
    if not m:
        empty_state("No trained model found", "Run `python -m ml.train_model --data ml/data/placement.csv` and commit ml/artifacts/. Until then the app uses a deterministic rule-based demo scorer.")
        return
    if m["data_source"] == "synthetic":
        st.warning("This model is trained on SYNTHETIC practice data. Retrain with the Kaggle dataset before presenting results as findings.")
    insight(f"The model learned from <b>{m['n_train']}</b> past students and was then tested on <b>{m['n_test']}</b> different students it had never seen. "
            f"Only <b>{100 * m['placement_rate']:.0f}%</b> of students in the data were placed, so a lazy model that always answered 'not placed' would be "
            f"right {100 * m['baseline_accuracy']:.0f}% of the time while being useless. That is why we look at more than accuracy.", "In simple terms")
    if m.get("trainer_version", 1) >= 2:
        tuning_status = "all three candidates" if m.get("tuned") else "skipped (fast mode)"
    elif m.get("tuned"):
        tuning_status = "legacy results; retrain for the three-model comparison"
    else:
        tuning_status = "skipped or not recorded"
    st.markdown(f"**Selected model:** {m['model_name']} (calibrated) &nbsp;|&nbsp; **Data:** {m['data_source']} &nbsp;|&nbsp; "
                f"**Tuning:** {tuning_status}")
    metric_row([{"label": "Accuracy", "value": f"{m['accuracy']:.2f}", "hint": f"Lazy baseline {m['baseline_accuracy']:.2f}"},
                {"label": "Precision", "value": f"{m['precision']:.2f}", "hint": "'Placed' calls that were right"},
                {"label": "Recall", "value": f"{m['recall']:.2f}", "hint": "Placed students found"},
                {"label": "F1", "value": f"{m['f1']:.2f}", "hint": "Balance of both"},
                {"label": "ROC-AUC", "value": f"{m['roc_auc']:.2f}", "hint": "1.0 = perfect"}])

    fit_check = m.get("fit_check")
    if fit_check:
        st.markdown("##### Fit check: learning patterns or memorizing examples?")
        metric_row([{"label": "Training AUC", "value": f"{fit_check['train_roc_auc']:.3f}", "hint": "Seen during model fitting"},
                    {"label": "Validation AUC", "value": f"{fit_check['cv_roc_auc']:.3f}", "hint": "Cross-validation on training data"},
                    {"label": "Test AUC", "value": f"{fit_check['test_roc_auc']:.3f}", "hint": "Held-out students"},
                    {"label": "Train-test gap", "value": f"{fit_check['gap']:.3f}", "hint": "Smaller is generally better"}])
        if fit_check["verdict"].startswith("Good fit"):
            st.success(fit_check["verdict"])
        else:
            st.warning(fit_check["verdict"])
        insight("A large training-to-test gap can indicate overfitting. Low performance on both training and held-out data can indicate underfitting. "
                "These scores are diagnostics, not proof that the model will generalize to another university or dataset.", "How to read the fit check")

    c1, c2 = st.columns(2)
    with c1:
        charts.show(charts.confusion_heatmap(m["confusion_matrix"]))
        insight(insights.confusion(m))
    with c2:
        charts.show(charts.importance_bar(m["feature_importance"]))
        insight(insights.importance(m))
    if m.get("roc_curve") and m.get("calibration"):
        c1, c2 = st.columns(2)
        with c1:
            charts.show(charts.roc_chart(m["roc_curve"], m["roc_auc"]))
            insight(insights.roc(m))
        with c2:
            charts.show(charts.calibration_chart(m["calibration"]))
            insight(insights.calibration(m))
    if m.get("category_outcomes"):
        charts.show(charts.category_outcomes_chart(m["category_outcomes"]))
        insight(insights.categories(m))

    st.markdown("##### Candidate model comparison")
    has_fit_comparison = all("train_roc_auc" in result for result in m["comparison"].values())
    if has_fit_comparison:
        comparison_rows = [
            {
                "Model": name,
                "Training AUC": result["train_roc_auc"],
                "Validation AUC": result["cv_roc_auc_mean"],
                "Train-validation gap": result["gap"],
                "Selection score": result["selection_score"],
                "Selected": "Yes" if name == m["model_name"] else "",
            }
            for name, result in m["comparison"].items()
        ]
        html_table(
            pd.DataFrame(comparison_rows),
            badge_cols={"Selected": lambda value: "success" if value else "neutral"},
            fmt={"Training AUC": "{:.3f}", "Validation AUC": "{:.3f}",
                 "Train-validation gap": "{:.3f}", "Selection score": "{:.3f}"},
        )
        st.caption("The full training workflow tunes Logistic Regression, Random Forest, and Gradient Boosting using cross-validation. "
                   "The selection score subtracts a small penalty when training AUC substantially exceeds validation AUC. "
                   "Fast mode skips hyperparameter tuning.")
    else:
        comparison_rows = [
            {"Model": name, "Mean ROC-AUC": result["cv_roc_auc_mean"],
             "Spread (+/-)": result["cv_roc_auc_std"],
             "Selected": "Yes" if name == m["model_name"] else ""}
            for name, result in m["comparison"].items()
        ]
        html_table(
            pd.DataFrame(comparison_rows),
            badge_cols={"Selected": lambda value: "success" if value else "neutral"},
            fmt={"Mean ROC-AUC": "{:.3f}", "Spread (+/-)": "{:.3f}"},
        )
        st.caption("These metrics are from an earlier trainer version. Retrain the model to produce the three-candidate fit comparison.")
    if m.get("thresholds"):
        th = m["thresholds"]
        st.caption(f"Category cut-offs learned from the data: Developing from {th['developing']:.0f}%, Job Ready from {th['job_ready']:.0f}%.")
    st.markdown("""##### Limitations
- Features: CGPA, projects, internship (yes/no), communication and extracurricular score only. Skills and certifications are not model inputs.
- The model reflects historical patterns in one dataset; it may not match your university or job market.
- Percentages are estimates, not guarantees, and should support (not replace) human advice.""")
