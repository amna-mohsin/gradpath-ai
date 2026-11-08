"""Plain-language explanations for charts, written for non-technical readers."""
import numpy as np

from core.config import CGPA_SCALE


def readiness_donut(df) -> str:
    """Explain the readiness category distribution in plain language."""
    n = len(df)
    c = df["Readiness"].value_counts()
    pct = lambda k: round(100 * c.get(k, 0) / n) if n else 0
    return (f"Each slice is a group of students. <b>{pct('Needs Improvement')}%</b> ({c.get('Needs Improvement', 0)} students) are in "
            f"<b>Needs Improvement</b>, usually because they need more projects, experience or skills. <b>{pct('Developing')}%</b> are "
            f"<b>Developing</b> (on the right track) and <b>{pct('Job Ready')}%</b> are <b>Job Ready</b>. "
            "A bigger green slice means a stronger placement outlook for the whole group.")


def department(df) -> str:
    """Explain student counts and average CGPA across departments."""
    t = df.groupby("Department").agg(n=("ID", "count"), cg=("CGPA", "mean"))
    big, best = t["n"].idxmax(), t["cg"].idxmax()
    return (f"Each bar is a department; taller bars mean more students, and a brighter colour means a higher average CGPA. "
            f"<b>{big}</b> has the most students ({int(t.loc[big, 'n'])}). <b>{best}</b> has the highest average CGPA ({t.loc[best, 'cg']:.2f}). "
            "Departments with dark bars may benefit from academic support.")


def cgpa(df) -> str:
    """Summarize the grade distribution and students below the guidance threshold."""
    counts, edges = np.histogram(df["CGPA"], bins=8)
    i = int(counts.argmax())
    low = 0.625 * CGPA_SCALE
    below = int((df["CGPA"] < low).sum())
    return (f"This shows how grades are spread. Most students ({int(counts[i])}) score between <b>{edges[i]:.2f}</b> and <b>{edges[i + 1]:.2f}</b>; "
            f"the average is <b>{df['CGPA'].mean():.2f}</b>. <b>{below}</b> student(s) are below {low:.2f}, who may need extra academic guidance.")


def skill_gaps(gaps) -> str:
    """Identify the most common career-skill gap for workshop planning."""
    top = gaps.sort_values("Students with gap", ascending=False).iloc[0]
    return (f"Each bar counts students who are missing, or still learning, a skill needed for their chosen career. "
            f"The longest bar is <b>{top['Skill']}</b> ({int(top['Students with gap'])} students), so a workshop on it would help the most people.")


def internship(df) -> str:
    """Explain internship participation and its relevance to practical experience."""
    p = round(100 * (df["Internships"] > 0).mean())
    return (f"<b>{p}%</b> of students have done at least one internship. Employers value real experience, so if the grey slice is large, "
            "consider more internship partnerships or practical projects.")


def source(df) -> str:
    """Clarify the distinction between registered and fictional demo records."""
    return ("Blue and light-blue bars separate <b>registered students</b> (real accounts) from <b>fictional demo records</b>, "
            "so demo data never gets mistaken for real results.")


def gauge(res) -> str:
    """Explain an individual readiness estimate and its statistical limitations."""
    if res.is_ml and res.base_rate:
        rel = (f"about <b>{res.lift}x</b> the average" if res.lift and res.lift >= 1 else "below the average")
        return (f"Your estimate is <b>{res.probability:.0f}%</b>. Among students in the data the model learned from, about "
                f"<b>{res.base_rate:.0f}%</b> were placed on average, so you are {rel}. "
                f"<b>{res.category}</b> means: {_meaning(res.category)} This is an estimate based on past patterns, not a promise.")
    return (f"This is a demo score of <b>{res.probability:.0f} out of 100</b> that adds up seven profile factors (CGPA counts most). "
            f"<b>{res.category}</b> means: {_meaning(res.category)} It is not a real probability.")


def _meaning(cat) -> str:
    """Retrieve the explanatory text for a readiness category."""
    from services.prediction_service import CATEGORY_MEANING
    return CATEGORY_MEANING[cat]


def factors(res) -> str:
    """Explain factor scores and highlight the student's improvement opportunities."""
    weak = ", ".join(f["name"] for f in res.weaknesses[:3]) or "none"
    return ("Each bar scores one part of your profile from 0 to 100. Long bars are strengths; short bars are the quickest ways to improve. "
            f"Your biggest opportunities right now: <b>{weak}</b>.")


def history(rows) -> str:
    """Describe how the student's saved estimate changed over time."""
    d = rows[-1].probability - rows[0].probability
    trend = "improved" if d > 0.5 else "dropped" if d < -0.5 else "stayed about the same"
    return f"Each point is a saved estimate. Since your first one, your estimate has <b>{trend}</b> ({d:+.1f} points)."


def confusion(m) -> str:
    """Explain test-set true and false predictions using plain-language metrics."""
    (tn, fp), (fn, tp) = m["confusion_matrix"]
    n = tn + fp + fn + tp
    return (f"We kept <b>{n}</b> students hidden from the model while training, then tested it on them. It correctly found <b>{tp}</b> of the "
            f"<b>{tp + fn}</b> students who were really placed (recall {100 * tp / max(tp + fn, 1):.0f}%). When it said 'placed', it was right "
            f"<b>{100 * tp / max(tp + fp, 1):.0f}%</b> of the time. It missed {fn} placed students and wrongly flagged {fp}. No model is perfect.")


def importance(m) -> str:
    """Explain which input features influence the trained model most."""
    imp = sorted(m["feature_importance"].items(), key=lambda kv: -kv[1])
    names = {"cgpa_ratio": "CGPA", "projects": "projects", "internship": "internship", "communication": "communication",
             "extracurricular": "extracurricular activity"}
    return (f"A longer bar means the model leans on that input more when judging. The strongest signal is <b>{names.get(imp[0][0], imp[0][0])}</b>, "
            f"followed by <b>{names.get(imp[1][0], imp[1][0])}</b>. Inputs with tiny bars barely change the result.")


def roc(m) -> str:
    """Explain the ROC curve and AUC as a model-ranking measure."""
    return (f"The closer the blue line hugs the top-left corner, the better; the dashed line is random guessing. The score (AUC) is <b>{m['roc_auc']:.2f}</b>: "
            f"if you pick one placed and one non-placed student at random, the model ranks the placed one higher about <b>{100 * m['roc_auc']:.0f}%</b> of the time.")


def calibration(m) -> str:
    """Explain how a calibration curve compares predicted and observed rates."""
    return ("If the green line follows the dashed diagonal, the percentages can be trusted: when the model says 30%, roughly 30 out of 100 "
            "such students were actually placed.")


def categories(m) -> str:
    """Summarize observed placement rates for the three readiness groups."""
    o = m["category_outcomes"]
    r = lambda k: "n/a" if o[k]["placed_rate"] is None else f"{100 * o[k]['placed_rate']:.0f}%"
    return (f"On the hidden test students, <b>{r('Job Ready')}</b> of those labelled Job Ready were really placed, versus <b>{r('Developing')}</b> for "
            f"Developing and <b>{r('Needs Improvement')}</b> for Needs Improvement. When the bars rise from left to right, the categories are meaningful.")


def applications(df) -> str:
    """Summarize application counts and identify the most popular listing."""
    top = df.sort_values("Applications", ascending=False).iloc[0]
    return (f"Each bar is a job and shows how many students applied. <b>{top['Job']}</b> is the most popular with {int(top['Applications'])} application(s). "
            "Low bars may need promotion or clearer requirements.")
