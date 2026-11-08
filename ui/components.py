"""Reusable UI building blocks."""
from html import escape as esc
from typing import Callable, List, Optional

import streamlit as st

from core.config import TAGLINE


def clean(s: str) -> str:
    """Trim blank lines and surrounding whitespace from an HTML fragment."""
    return "\n".join(line.strip() for line in s.strip().splitlines() if line.strip())


def html(s: str) -> None:
    """Render cleaned application HTML through Streamlit's markdown renderer."""
    st.markdown(clean(s), unsafe_allow_html=True)


def brand_svg(size: int = 36) -> str:
    """Return the inline SVG used for the GradPath brand mark."""
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg">'
            '<defs><linearGradient id="gpg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#6366F1"/>'
            '<stop offset="1" stop-color="#8B5CF6"/></linearGradient></defs>'
            '<rect width="40" height="40" rx="11" fill="url(#gpg)"/>'
            '<path d="M20 9 L33 15 L20 21 L7 15 Z" fill="#fff"/>'
            '<path d="M13 19.5v5.5c0 2 3.1 4 7 4s7-2 7-4v-5.5l-7 3.3z" fill="#fff" fill-opacity=".85"/>'
            '<path d="M33 15v8" stroke="#38BDF8" stroke-width="2.2" stroke-linecap="round"/>'
            '<path d="M29.5 31l3.5-3.5 3.5 3.5" stroke="#38BDF8" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def brand(size: int = 36, tagline: bool = False) -> str:
    """Build the brand wordmark with an optional tagline."""
    tag = f'<div class="gp-muted" style="margin-top:.5rem">{esc(TAGLINE)}</div>' if tagline else ""
    return f'<div><div class="gp-brand">{brand_svg(size)}<b>GradPath <i>AI</i></b></div>{tag}</div>'


def page_header(title: str, subtitle: str = "") -> None:
    """Render the consistent title and optional subtitle used by app pages."""
    sub = f'<div class="gp-sub">{esc(subtitle)}</div>' if subtitle else ""
    html(f'<div style="margin-bottom:1.3rem"><div class="gp-title">{esc(title)}</div>{sub}</div>')


def badge(text: str, kind: str = "neutral") -> str:
    """Build an escaped status badge using a named visual style."""
    return f'<span class="gp-badge b-{kind}">{esc(str(text))}</span>'


def badges(items: List[str], kind: str = "neutral") -> str:
    """Build a sequence of badges or a placeholder when no values exist."""
    return "".join(badge(i, kind) for i in items) or '<span class="gp-muted">None yet</span>'


def category_kind(category: str) -> str:
    """Map a readiness category to its corresponding badge style."""
    return {"Job Ready": "success", "Developing": "info", "Needs Improvement": "warn"}.get(category, "neutral")


def status_kind(status: str) -> str:
    """Map a skill status to its corresponding badge style."""
    return {"Available": "success", "Needs improvement": "warn", "Missing": "danger"}.get(status, "neutral")


def progress_bar(pct: float, label: str = "", green: bool = False) -> str:
    """Build a bounded percentage bar with an optional label and green variant."""
    pct = max(0, min(100, pct))
    head = f'<div class="gp-row"><span class="gp-muted">{esc(label)}</span><b style="font-size:.85rem">{pct:.0f}%</b></div>' if label else ""
    return f'{head}<div class="gp-bar {"green" if green else ""}"><div style="width:{pct}%"></div></div>'


def card(title: str, body: str, accent: bool = False) -> str:
    """Wrap content in a standard or accent application card."""
    cls = "gp-accent" if accent else "gp-card"
    return f'<div class="{cls}"><h4 style="color:inherit">{esc(title)}</h4>{body}</div>' if title else f'<div class="{cls}">{body}</div>'


def metric_card(label: str, value, hint: str = "") -> str:
    """Build one metric card with an optional supporting hint."""
    h = f'<div class="h">{esc(hint)}</div>' if hint else ""
    return f'<div class="gp-card gp-metric"><div class="l">{esc(label)}</div><div class="v">{esc(str(value))}</div>{h}</div>'


def metric_row(items: List[dict]) -> None:
    """Render metric cards evenly across the current Streamlit page."""
    for col, item in zip(st.columns(len(items)), items):
        with col:
            html(metric_card(**item))


def empty_state(title: str, message: str) -> None:
    """Render a consistent message when a page has no records to show."""
    html(f'<div class="gp-empty"><b>{esc(title)}</b>{esc(message)}</div>')


def go(key: str, label: str, primary: bool = False, widget_key: Optional[str] = None) -> None:
    """Button that navigates to another page of the app."""
    if st.button(label, type="primary" if primary else "secondary", key=widget_key or f"go_{key}_{label}"):
        st.switch_page(st.session_state["nav"][key])


def list_items(items: List[str]) -> str:
    """Wrap already-prepared list item markup in the shared list style."""
    return '<ul class="gp-list">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def insight(text: str, title: str = "What this means") -> None:
    """Plain-language explanation shown under a chart or table."""
    html(f'<div class="gp-insight"><b>{esc(title)}:</b> {text}</div>')


def html_table(df, badge_cols: Optional[dict] = None, bar_cols: Optional[List[str]] = None,
               fmt: Optional[dict] = None, max_height: int = 460) -> None:
    """Theme-safe table (st.dataframe cannot be recoloured for light mode)."""
    badge_cols, bar_cols, fmt = badge_cols or {}, bar_cols or [], fmt or {}
    head = "".join(f"<th>{esc(str(c))}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in df.columns:
            v = r[c]
            if c in badge_cols:
                cell = badge(v, badge_cols[c](v))
            elif c in bar_cols:
                cell = f'<div style="min-width:110px"><b>{float(v):.0f}%</b>{progress_bar(float(v))}</div>'
            elif c in fmt:
                cell = esc(fmt[c].format(v))
            else:
                cell = esc(str(v))
            cells.append(f"<td>{cell}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    html(f'<div class="gp-tablewrap" style="max-height:{max_height}px"><table class="gp-table"><tr>{head}</tr>{"".join(rows)}</table></div>')


def bubble(body: str, when: str, mine: bool) -> str:
    """Build an escaped chat bubble with a timestamp and sender styling."""
    text = esc(body).replace("\n", "<br>")
    return f'<div class="gp-bubble {"me" if mine else "them"}">{text}<small>{esc(when)}</small></div>'


def request_confirm(key: str) -> None:
    """Set the session flag that opens a keyed confirmation prompt."""
    st.session_state[f"confirm_{key}"] = True


def confirm_box(key: str, message: str, on_confirm: Callable[[], None], yes_label: str = "Yes, delete") -> None:
    """Shows 'Are you sure?' with Yes/Cancel when request_confirm(key) was called."""
    flag = f"confirm_{key}"
    if not st.session_state.get(flag):
        return
    st.warning(message)
    c1, c2, _ = st.columns([1.2, 1, 4])
    if c1.button(yes_label, key=f"{key}_yes", type="primary"):
        st.session_state.pop(flag, None)
        on_confirm()
        st.rerun()
    if c2.button("Cancel", key=f"{key}_no"):
        st.session_state.pop(flag, None)
        st.rerun()
