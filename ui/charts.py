"""Plotly charts styled for the active theme."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.config import READINESS_LEVELS
from ui.theme import colors

CAT_COLORS = {"Needs Improvement": "#F59E0B", "Developing": "#38BDF8", "Job Ready": "#10B981"}


def _text_color() -> str:
    """Return the foreground color used for chart labels in the fixed theme."""
    return colors()["text"]


def style(fig, height: int = 320):
    """Apply shared theme colors, axis formatting, spacing, and interaction settings."""
    c = colors()
    text = _text_color()
    fig.update_layout(height=height, margin=dict(l=64, r=28, t=48, b=96), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=text, family="Inter, sans-serif"),
                      title=dict(font=dict(size=15, color=text)),
                      legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=text)))
    fig.update_layout(dragmode=False, hovermode="closest", legend_itemclick=False, legend_itemdoubleclick=False)
    fig.update_xaxes(gridcolor=c["border"], zerolinecolor=c["border"], fixedrange=True,
                     color=text, title_font_color=text, tickfont_color=text,
                     linecolor=c["border"], automargin=True, title_standoff=12)
    fig.update_yaxes(gridcolor=c["border"], zerolinecolor=c["border"], fixedrange=True,
                     color=text, title_font_color=text, tickfont_color=text,
                     linecolor=c["border"], automargin=True, title_standoff=12)
    fig.update_coloraxes(colorbar=dict(tickfont=dict(color=text), title=dict(font=dict(color=text))))
    return fig


def show(fig) -> None:
    """Render a Plotly figure without Streamlit's automatic theme overriding it."""
    st.plotly_chart(style(fig), width="stretch", theme=None,
                    config={"displayModeBar": False, "scrollZoom": False,
                            "doubleClick": False, "showTips": False})


def gauge(value: float, category: str):
    """Build the readiness percentage gauge and category-colored indicator."""
    c = colors()
    text = _text_color()
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, number={"suffix": "%", "font": {"size": 44, "color": text}},
        gauge={"axis": {"range": [0, 100], "tickcolor": text, "tickfont": {"color": text}},
               "bar": {"color": CAT_COLORS.get(category, c["primary"])},
               "bgcolor": c["card2"], "borderwidth": 0,
               "steps": [{"range": [0, 40], "color": c["card2"]}, {"range": [40, 70], "color": c["card2"]},
                         {"range": [70, 100], "color": c["card2"]}]}))
    return style(fig, 260)


def factor_bars(factors):
    """Build a horizontal score chart with room for labels and score annotations."""
    df = pd.DataFrame(factors).sort_values("score")
    fig = px.bar(df, x="score", y="name", orientation="h", text="score", custom_data=["note"],
                 title="Factor strength (0-100)", color_discrete_sequence=[colors()["primary"]])
    fig.update_traces(hovertemplate="%{y}: %{x}/100<br>%{customdata[0]}<extra></extra>",
                      textposition="outside", textfont_color=_text_color(), cliponaxis=False)
    fig.update_xaxes(range=[0, 120], title_text="Score (0-100)", title_standoff=12,
                     tickmode="array", tickvals=[0, 20, 40, 60, 80, 100])
    fig.update_yaxes(title=None, automargin=True, tickfont_size=13)
    styled = style(fig, max(360, len(df) * 42 + 100))
    styled.update_layout(margin=dict(l=150, r=36, t=54, b=106))
    return styled


def history_line(rows):
    """Plot saved readiness estimates over time for one student."""
    df = pd.DataFrame([{"When": r.created_at, "Estimate (%)": r.probability} for r in rows])
    fig = px.line(df, x="When", y="Estimate (%)", markers=True, title="Your estimate over time",
                  color_discrete_sequence=[colors()["sky"]])
    fig.update_yaxes(range=[0, 100])
    return style(fig, 260)


def readiness_donut(df):
    """Show the share of students in each readiness category."""
    counts = df["Readiness"].value_counts().reindex(READINESS_LEVELS).fillna(0).reset_index()
    counts.columns = ["Readiness", "Students"]
    fig = px.pie(counts, names="Readiness", values="Students", hole=0.62, color="Readiness",
                 color_discrete_map=CAT_COLORS, title="Readiness category distribution")
    fig.update_traces(textfont_color=_text_color())
    return style(fig)


def readiness_by_source(df):
    """Compare readiness counts while distinguishing registered and demo records."""
    t = df.groupby(["Readiness", "Source"]).size().reset_index(name="Students")
    fig = px.bar(t, x="Readiness", y="Students", color="Source", barmode="stack",
                 category_orders={"Readiness": READINESS_LEVELS}, title="Readiness by data source",
                 color_discrete_sequence=[colors()["primary"], colors()["sky"]])
    fig.update_xaxes(tickangle=-25, title_standoff=26)
    styled = style(fig, 360)
    styled.update_layout(margin=dict(l=62, r=20, t=54, b=138))
    return styled


def department_bar(df):
    """Compare student counts by department and color bars by average CGPA."""
    t = df.groupby("Department").agg(Students=("ID", "count"), AvgCGPA=("CGPA", "mean")).reset_index()
    fig = px.bar(t, x="Department", y="Students", color="AvgCGPA", title="Students per department (colour = avg CGPA)",
                 color_continuous_scale=["#312E81", "#6366F1", "#38BDF8"])
    return style(fig)


def cgpa_hist(df):
    """Show how student CGPA values are distributed."""
    fig = px.histogram(df, x="CGPA", nbins=12, title="CGPA distribution", color_discrete_sequence=[colors()["violet"]])
    fig.update_layout(bargap=0.08)
    return style(fig)


def skill_gap_bar(gaps):
    """Rank career skills by the number of students with a gap."""
    fig = px.bar(gaps.sort_values("Students with gap"), x="Students with gap", y="Skill", orientation="h",
                 title="Most common skill gaps", color_discrete_sequence=[colors()["amber"]])
    return style(fig)


def internship_pie(df):
    """Show the proportion of students with internship experience."""
    t = df.assign(Group=df["Internships"].apply(lambda n: "Has internship" if n > 0 else "No internship"))["Group"].value_counts().reset_index()
    t.columns = ["Group", "Students"]
    fig = px.pie(t, names="Group", values="Students", hole=0.55, title="Internship participation",
                 color="Group", color_discrete_map={"Has internship": "#10B981", "No internship": "#64748B"})
    fig.update_traces(textfont_color=_text_color())
    return style(fig)


def confusion_heatmap(matrix):
    """Visualize correct and incorrect placement predictions in a confusion matrix."""
    fig = px.imshow(matrix, text_auto=True, x=["Predicted<br>Not placed", "Predicted<br>Placed"],
                    y=["Actual<br>Not placed", "Actual<br>Placed"],
                    color_continuous_scale=["#1B2549", "#6366F1"], title="How often the model was right (test students)")
    fig.update_traces(textfont_color=_text_color())
    fig.update_coloraxes(showscale=False)
    fig.update_xaxes(title=None, tickangle=0)
    fig.update_yaxes(title=None)
    styled = style(fig, 340)
    styled.update_layout(margin=dict(l=104, r=24, t=52, b=82))
    return styled


def importance_bar(imp: dict):
    """Rank model features by their permutation importance values."""
    df = pd.DataFrame({"Feature": list(imp), "Importance": list(imp.values())}).sort_values("Importance")
    fig = px.bar(df, x="Importance", y="Feature", orientation="h", title="Permutation importance (drop in ROC-AUC)",
                 color_discrete_sequence=[colors()["sky"]])
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, tickfont_size=12)
    styled = style(fig, max(340, len(df) * 38 + 100))
    styled.update_layout(margin=dict(l=112, r=24, t=52, b=72))
    return styled


def roc_chart(roc: dict, auc: float):
    """Compare the model's ROC curve with the random-guessing baseline."""
    c = colors()
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random guessing", line=dict(dash="dash", color=c["muted"]))
    fig.add_scatter(x=roc["fpr"], y=roc["tpr"], mode="lines", name=f"Our model (AUC {auc:.2f})", line=dict(color=c["primary"], width=3))
    fig.update_layout(title="ROC curve: how well the model separates the two groups")
    fig.update_xaxes(title="False positive rate")
    fig.update_yaxes(title="True positive rate")
    styled = style(fig, 360)
    styled.update_layout(margin=dict(l=78, r=24, t=52, b=88))
    return styled


def calibration_chart(cal: dict):
    """Compare predicted placement probabilities with observed placement rates."""
    c = colors()
    fig = go.Figure()
    fig.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="Perfect", line=dict(dash="dash", color=c["muted"]))
    fig.add_scatter(x=cal["predicted"], y=cal["actual"], mode="lines+markers", name="Our model",
                    line=dict(color=c["emerald"], width=3))
    fig.update_layout(title="Can you trust the percentages?")
    fig.update_xaxes(title="Predicted probability", tickformat=".0%")
    fig.update_yaxes(title="Observed placement rate", tickformat=".0%")
    styled = style(fig, 360)
    styled.update_layout(margin=dict(l=92, r=24, t=52, b=88))
    return styled


def category_outcomes_chart(outcomes: dict):
    """Compare observed placement rates across readiness categories."""
    rows = [{"Category": k, "Placed (%)": round(100 * v["placed_rate"], 1)} for k, v in outcomes.items() if v.get("placed_rate") is not None]
    df = pd.DataFrame(rows)
    fig = px.bar(df, x="Category", y="Placed (%)", color="Category", color_discrete_map=CAT_COLORS, text="Placed (%)",
                 category_orders={"Category": READINESS_LEVELS}, title="Actual placement rate by readiness category")
    fig.update_traces(textfont_color=_text_color())
    fig.update_layout(showlegend=False)
    fig.update_xaxes(title=None, tickangle=-18)
    fig.update_yaxes(title=None)
    styled = style(fig, 380)
    styled.update_layout(margin=dict(l=62, r=28, t=52, b=98))
    return styled


def applications_chart(df):
    """Compare application counts across job listings."""
    fig = px.bar(df.sort_values("Applications"), x="Applications", y="Job", orientation="h",
                 title="Applications per job", color_discrete_sequence=[colors()["violet"]])
    return style(fig, 320)
