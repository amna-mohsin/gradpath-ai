"""Student page explaining a readiness estimate and possible improvements."""
from types import SimpleNamespace

import streamlit as st

from core.config import CGPA_SCALE
from services.prediction_service import (CATEGORY_MEANING, PredictionService, PredictorFactory, load_metrics)
from services.recommendation_service import RecommendationService
from ui import charts, insights
from ui.components import badge, category_kind, esc, html, insight, list_items, page_header, progress_bar
from views.common import get_student


def _what_if(stu, res):
    """Render unsaved profile sliders and show their changed estimate."""
    with st.expander("Try a what-if scenario: how would my estimate change?"):
        st.caption("Move the sliders to see the effect of improving one area. Nothing is saved.")
        c1, c2, c3 = st.columns(3)
        cg = c1.slider("CGPA", 0.0, float(CGPA_SCALE), float(stu.cgpa or 0), 0.05, key="wi_cg")
        pr = c2.slider("Projects", 0, 10, int(stu.projects or 0), key="wi_pr")
        it = c3.slider("Internships", 0, 4, int(stu.internships or 0), key="wi_it")
        c1, c2 = st.columns(2)
        cm = c1.slider("Communication", 1, 10, int(stu.communication or 5), key="wi_cm")
        ex = c2.slider("Extracurricular", 0, 10, int(stu.extracurricular or 0), key="wi_ex")
        ghost = SimpleNamespace(cgpa=cg, projects=pr, internships=it, communication=cm, extracurricular=ex,
                                skill_list=stu.skill_list, learning_list=stu.learning_list, cert_list=stu.cert_list)
        new = PredictorFactory.create().predict(ghost)
        delta = new.probability - res.probability
        html(f'<div class="gp-card"><div class="gp-row"><div><b style="font-size:1.4rem">{new.probability:.0f}%</b> '
             f'<span class="gp-muted">new estimate (was {res.probability:.0f}%, {delta:+.1f} points)</span></div>'
             f'{badge(new.category, category_kind(new.category))}</div></div>')


def _levers(stu):
    """Show model-driven estimate changes for feasible profile improvements."""
    plan = RecommendationService.ml_actions(stu)
    base, items = plan["baseline"], plan["items"]
    who = "the prediction model" if plan["is_ml"] else "the demo scorer"
    st.markdown("##### Your biggest levers")
    if not items:
        st.info("None of the improvements we tested would raise your estimate. Your profile is already near the top of what the model can measure.")
        return
    top_gain = max(i["gain"] for i in items) or 1
    for i, it in enumerate(items, 1):
        up = badge(f"Moves you to {it['new_category']}", "success") if it["moves_up"] else ""
        html(f'''<div class="gp-card"><div class="gp-row"><b>{i}. {esc(it["title"])}</b>
            <span><b style="font-size:1.2rem">+{it["gain"]:.1f}</b> <span class="gp-muted">points</span></span></div>
            <p>{esc(it["detail"])}</p>{progress_bar(100 * it["gain"] / top_gain, "", green=True)}
            <span class="gp-muted">Estimate would go from {base.probability:.0f}% to {it["new_probability"]:.0f}%</span> {up}</div>''')
    comb = plan["combined"]
    if comb is not None:
        html(f'''<div class="gp-accent"><div style="opacity:.9;font-weight:600">If you did the top {len(plan["combined_titles"])} together</div>
            <div class="big">{base.probability:.0f}% &rarr; {comb.probability:.0f}%</div>
            <p>{esc(" + ".join(plan["combined_titles"]))}. Category: {esc(base.category)} &rarr; {esc(comb.category)}.</p></div>''')
    insight(f"We asked {who} the same question for each action: <b>\"what would your estimate be if you did this?\"</b> "
            "The bigger the number, the more that action helps according to the patterns it learned from past students. "
            "These are estimates, not promises. They tell you where to spend your effort first.", "How these were calculated")


def render():
    """Render the student's estimate, factor analysis, and improvement guidance."""
    stu = get_student()
    page_header("Understand your career readiness",
                "Review your profile and discover areas that may strengthen your preparation for employment.")
    res = PredictionService.estimate(stu, save=stu.profile_completion() >= 50)

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        charts.show(charts.gauge(res.probability, res.category))
        html(f'<div style="text-align:center">{badge(res.category, category_kind(res.category))}'
             f'{badge(f"Profile {stu.profile_completion()}% complete", "neutral")}</div>')
    with right:
        charts.show(charts.factor_bars(res.factors))
    insight(insights.gauge(res))
    insight(insights.factors(res), "Reading the bars")
    html('<div class="gp-card"><h4>What the three categories mean</h4>' + list_items(
        [f'{badge(k, category_kind(k))} {esc(v)}' for k, v in CATEGORY_MEANING.items()]) + "</div>")

    c1, c2 = st.columns(2)
    with c1:
        html('<div class="gp-card"><h4>Main positive factors</h4>' + (list_items(
            [f'<b>{esc(f["name"])}</b> <span class="gp-muted">{esc(f["note"])}</span>' for f in res.strengths]) if res.strengths
            else '<p>No factor is strong yet. Small improvements add up quickly.</p>') + "</div>")
    with c2:
        html('<div class="gp-card"><h4>Areas requiring improvement</h4>' + (list_items(
            [f'<b>{esc(f["name"])}</b> <span class="gp-muted">{esc(f["note"])}</span>' for f in res.weaknesses]) if res.weaknesses
            else '<p>No major weak areas detected.</p>') + "</div>")

    _levers(stu)
    _what_if(stu, res)

    st.markdown("##### Other recommendations (skills and certifications)")
    extra = [a for a in RecommendationService.next_actions(res, 7) if a["factor"] in ("Technical skills", "Certifications")]
    if not extra:
        st.caption("Your skills and certifications look good.")
    for a in extra:
        html(f'<div class="gp-card"><h4>{esc(a["title"])}</h4><p>{esc(a["detail"])}</p></div>')

    st.markdown("##### How each input influenced the picture")
    rows = "".join(f'<tr><td><b>{esc(f["name"])}</b></td><td>{f["weight"]}</td><td>{f["score"]}/100</td><td>{esc(f["note"])}</td></tr>' for f in res.factors)
    html(f'<div class="gp-tablewrap"><table class="gp-table"><tr><th>Factor</th><th>Weight</th><th>Your score</th><th>Details</th></tr>{rows}</table></div>')

    hist = PredictionService.history(stu.id)
    if len(hist) >= 2:
        charts.show(charts.history_line(hist))
        insight(insights.history(hist))
    st.caption(f"Estimator in use: {res.strategy}.")
    m = load_metrics()
    if res.is_ml and m:
        st.caption(f"Model trained on '{m['data_source']}' | test ROC-AUC {m['roc_auc']:.2f}")
    html('<div class="gp-footer">Statistical estimate from a Random Forest model trained on \'Kaggle CSV (placement.csv)\' '
         '(hold-out ROC-AUC 0.93). It reflects patterns in historical data, not your individual future, and does not guarantee employment.</div>')