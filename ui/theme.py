"""Dark blue design system.

The app uses one fixed dark-blue theme so every page and widget stays consistent.
"""
from string import Template

import streamlit as st

DARK = dict(
    scheme="dark", bg="#0B1020", surface="#10172E", card="#141C38", card2="#1B2549", border="#26315A",
    text="#E8ECF8", muted="#93A0BD", primary="#6366F1", violet="#8B5CF6", sky="#38BDF8", emerald="#10B981",
    amber="#F59E0B", red="#F87171", shadow="0 10px 30px rgba(0,0,0,.35)",
    hero="radial-gradient(900px 420px at 10% -10%, rgba(99,102,241,.38), transparent 60%),"
         "radial-gradient(700px 400px at 100% 0%, rgba(56,189,248,.20), transparent 55%)",
)
LIGHT = dict(
    scheme="light", bg="#F4F6FB", surface="#FFFFFF", card="#FFFFFF", card2="#EEF2FF", border="#D9E0EC",
    text="#0F172A", muted="#5B6B82", primary="#4F46E5", violet="#7C3AED", sky="#0284C7", emerald="#047857",
    amber="#B45309", red="#B91C1C", shadow="0 8px 24px rgba(15,23,42,.08)",
    hero="radial-gradient(900px 420px at 10% -10%, rgba(99,102,241,.16), transparent 60%),"
         "radial-gradient(700px 400px at 100% 0%, rgba(56,189,248,.16), transparent 55%)",
)


def theme_name() -> str:
    """Return the app's fixed dark-blue theme name."""
    return "dark"


def colors() -> dict:
    """Return the color tokens used by the fixed dark-blue theme."""
    return DARK


CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp{background:$bg;color:$text;color-scheme:$scheme;font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp label,.stApp li,.stApp input,.stApp textarea{font-family:'Inter',system-ui,sans-serif}
.block-container{padding-top:2.2rem;padding-bottom:4rem;max-width:1180px}
[data-testid="stHeader"]{background:transparent!important}
[data-testid="stSidebar"]{background:$surface!important;border-right:1px solid $border}
[data-testid="stSidebar"] .block-container{padding-top:1.2rem}

/* ---- native text, readable in both modes ---- */
[data-testid="stMarkdownContainer"] > p,[data-testid="stMarkdownContainer"] > ul > li,
[data-testid="stMarkdownContainer"] > ol > li,[data-testid="stMarkdownContainer"] > h1,
[data-testid="stMarkdownContainer"] > h2,[data-testid="stMarkdownContainer"] > h3,
[data-testid="stMarkdownContainer"] > h4,[data-testid="stMarkdownContainer"] > h5,
[data-testid="stMarkdownContainer"] > h6,[data-testid="stMarkdownContainer"] > p strong,
[data-testid="stHeading"] *,[data-testid="stWidgetLabel"],[data-testid="stWidgetLabel"] *,
[data-testid="stPageLink-NavLink"] *,[data-testid="stCheckbox"] *,[data-testid="stToggle"] *,
[data-testid="stRadio"] label *{color:$text!important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] *{color:$muted!important}
[data-testid="stPageLink-NavLink"]{border-radius:10px}
[data-testid="stPageLink-NavLink"]:hover{background:$card2!important}
[data-testid="stPageLink-NavLink"][aria-current="page"]{background:$card2!important;border:1px solid $border}
[data-testid="stAlert"]{background:$card2!important;border:1px solid $border;border-radius:12px}
[data-testid="stAlert"] *{color:$text!important}
hr{border-color:$border!important}

/* ---- inputs, selects, popovers ---- */
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{
  background:$card2!important;border-color:$border!important;color:$text!important}
input:not([type="checkbox"]):not([type="radio"]),textarea{
  background:$card2!important;color:$text!important;-webkit-text-fill-color:$text!important;caret-color:$text}
input::placeholder,textarea::placeholder{color:$muted!important;-webkit-text-fill-color:$muted!important;opacity:.85}
[data-baseweb="select"] *{color:$text!important}
[data-baseweb="select"] svg{fill:$muted!important}
[data-baseweb="popover"]>div,[data-baseweb="popover"] ul,[data-baseweb="menu"]{background:$card!important;border:1px solid $border}
[data-baseweb="popover"] li,[role="option"]{color:$text!important;background:transparent!important}
[data-baseweb="popover"] li:hover,[role="option"]:hover,[aria-selected="true"][role="option"]{background:$card2!important}
[data-baseweb="tag"]{background:rgba(99,102,241,.22)!important}
[data-baseweb="tag"] span{color:$text!important}
[data-testid="stNumberInput"] button{background:$card2!important;color:$text!important;border-color:$border!important}
[data-testid="stSliderThumbValue"],[data-testid="stTickBarMin"],[data-testid="stTickBarMax"]{color:$text!important}
[data-testid="stFileUploaderDropzone"]{background:$card2!important;border:1px dashed $border!important}
[data-testid="stFileUploaderDropzone"] *{color:$text!important}

/* ---- tabs, expanders, forms, dialogs, chat ---- */
button[data-baseweb="tab"] p{color:$muted!important}
button[data-baseweb="tab"][aria-selected="true"] p{color:$primary!important;font-weight:700}
[data-baseweb="tab-border"]{background:$border!important}
[data-testid="stExpander"] details{background:$card!important;border:1px solid $border!important;border-radius:12px}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary *{color:$text!important}
[data-testid="stForm"]{background:$card;border:1px solid $border;border-radius:16px}
[data-testid="stVerticalBlockBorderWrapper"]{border-color:$border!important}
div[role="dialog"]{background:$card!important;color:$text}
div[role="dialog"] h1,div[role="dialog"] h2,div[role="dialog"] h3{color:$text!important}
[data-testid="stChatMessage"]{background:$card;border:1px solid $border;border-radius:12px}
[data-testid="stChatInput"]{background:$card2}

/* ---- buttons ---- */
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"],
[data-testid="stDownloadButton"] button{background:$card!important;color:$text!important;border:1px solid $border!important;border-radius:12px;font-weight:600}
[data-testid="stBaseButton-secondary"] p,[data-testid="stBaseButton-secondaryFormSubmit"] p,
[data-testid="stDownloadButton"] button p{color:$text!important}
[data-testid="stBaseButton-secondary"]:hover,[data-testid="stBaseButton-secondaryFormSubmit"]:hover{border-color:$primary!important}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{background:linear-gradient(90deg,$primary,$violet)!important;border:none!important;border-radius:12px;font-weight:600}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p{color:#fff!important}

/* ---- GradPath components (declared last so they win) ---- */
.gp-brand{display:flex;align-items:center;gap:10px}
.gp-brand b{font-size:1.2rem;letter-spacing:-.02em;color:$text}
.gp-brand b i{font-style:normal;background:linear-gradient(90deg,$primary,$sky);-webkit-background-clip:text;background-clip:text;color:transparent}
.gp-title{font-size:1.9rem;font-weight:800;letter-spacing:-.025em;color:$text;line-height:1.15}
.gp-sub{color:$muted;font-size:1rem;margin-top:.25rem}
.gp-muted{color:$muted!important;font-size:.88rem}
.gp-card{background:$card;border:1px solid $border;border-radius:16px;padding:1.1rem 1.25rem;box-shadow:$shadow;margin-bottom:.9rem;color:$text}
.gp-card h4{margin:0 0 .4rem;font-size:1.02rem;font-weight:700;color:$text!important}
.gp-card p{margin:.2rem 0;color:$muted!important;font-size:.92rem}
.gp-card b{color:$text}
.gp-metric .l{color:$muted;font-size:.8rem;font-weight:600;margin-bottom:.2rem}
.gp-metric .v{font-size:2.1rem;font-weight:800;color:$text;line-height:1.1;letter-spacing:-.02em}
.gp-metric .h{color:$muted;font-size:.78rem;margin-top:.3rem}
.gp-accent{background:linear-gradient(135deg,$primary,$violet);color:#fff;border-radius:18px;padding:1.4rem 1.6rem;box-shadow:$shadow;margin-bottom:.9rem}
.gp-accent *{color:#fff!important}
.gp-accent .big{font-size:2.8rem;font-weight:800;line-height:1;letter-spacing:-.03em}
.gp-accent p{opacity:.9;margin:.4rem 0 0}
.gp-insight{border-left:4px solid $primary;background:$card2;border-radius:10px;padding:.75rem 1rem;margin:.1rem 0 1.1rem;font-size:.9rem;line-height:1.5;color:$text}
.gp-insight b{color:$primary}
.gp-badge{display:inline-block;padding:.16rem .65rem;border-radius:999px;font-size:.74rem;font-weight:600;margin:.12rem .25rem .12rem 0;border:1px solid transparent;white-space:nowrap}
.b-success{color:$emerald!important;background:rgba(16,185,129,.14);border-color:rgba(16,185,129,.4)}
.b-warn{color:$amber!important;background:rgba(245,158,11,.14);border-color:rgba(245,158,11,.4)}
.b-danger{color:$red!important;background:rgba(239,68,68,.12);border-color:rgba(239,68,68,.4)}
.b-info{color:$sky!important;background:rgba(56,189,248,.13);border-color:rgba(56,189,248,.4)}
.b-violet{color:$violet!important;background:rgba(139,92,246,.14);border-color:rgba(139,92,246,.4)}
.b-neutral{color:$muted!important;background:$card2;border-color:$border}
.gp-bar{height:8px;background:$card2;border-radius:99px;overflow:hidden;margin:.35rem 0 .2rem}
.gp-bar>div{height:100%;border-radius:99px;background:linear-gradient(90deg,$primary,$sky)}
.gp-bar.green>div{background:linear-gradient(90deg,$emerald,$sky)}
.gp-row{display:flex;justify-content:space-between;gap:.8rem;align-items:center}
.gp-list{margin:0;padding:0;list-style:none}
.gp-list li{padding:.55rem 0;border-bottom:1px solid $border;color:$text;font-size:.92rem}
.gp-list li:last-child{border-bottom:none}
.gp-avatar{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,$primary,$violet);color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
.gp-tablewrap{overflow:auto;border:1px solid $border;border-radius:14px;background:$card;margin-bottom:.9rem}
.gp-table{width:100%;border-collapse:collapse;font-size:.88rem}
.gp-table th{text-align:left;color:$muted;font-weight:600;font-size:.76rem;padding:.6rem .7rem;border-bottom:1px solid $border;position:sticky;top:0;background:$card;white-space:nowrap}
.gp-table td{padding:.6rem .7rem;border-bottom:1px solid $border;color:$text;vertical-align:top}
.gp-table tr:last-child td{border-bottom:none}
.gp-empty{text-align:center;padding:2.2rem 1rem;border:1px dashed $border;border-radius:16px;color:$muted}
.gp-empty b{display:block;color:$text;font-size:1.05rem;margin-bottom:.3rem}
.gp-hero{background:$hero;border:1px solid $border;border-radius:24px;padding:2.4rem 2.2rem;margin-bottom:1.2rem}
.gp-hero h1{font-size:3rem;font-weight:800;letter-spacing:-.035em;line-height:1.08;margin:.6rem 0;color:$text}
.gp-hero h1 span{background:linear-gradient(90deg,$primary,$sky);-webkit-background-clip:text;background-clip:text;color:transparent}
.gp-hero p{color:$muted!important;font-size:1.08rem;max-width:34rem}
.gp-nav{display:flex;justify-content:space-between;align-items:center;padding:.2rem 0 1.2rem}
.gp-nav a{color:$muted!important;text-decoration:none;margin-left:1.5rem;font-weight:500;font-size:.92rem}
.gp-nav a:hover{color:$text!important}
.gp-btn{display:inline-block;padding:.72rem 1.35rem;border-radius:12px;font-weight:600;text-decoration:none!important;margin:.5rem .6rem .2rem 0;font-size:.95rem}
.gp-btn.primary{background:linear-gradient(90deg,$primary,$violet);color:#fff!important}
.gp-btn.ghost{border:1px solid $border;color:$text!important;background:$card}
.gp-section{font-size:1.6rem;font-weight:800;letter-spacing:-.02em;color:$text;margin:2.2rem 0 .3rem}
.gp-footer{border-top:1px solid $border;margin-top:3rem;padding-top:1.2rem;color:$muted;font-size:.85rem}
.gp-bubble{max-width:78%;padding:.6rem .9rem;border-radius:14px;margin:.35rem 0;font-size:.92rem;line-height:1.45}
.gp-bubble small{display:block;opacity:.7;margin-top:.25rem;font-size:.7rem}
.gp-bubble.me{margin-left:auto;background:linear-gradient(135deg,$primary,$violet);color:#fff}
.gp-bubble.me *{color:#fff!important}
.gp-bubble.them{background:$card2;border:1px solid $border;color:$text}
@media (max-width:768px){.gp-hero h1{font-size:2.1rem}.gp-nav a{display:none}.gp-title{font-size:1.5rem}.gp-hero{padding:1.5rem 1.2rem}.gp-bubble{max-width:92%}}
</style>
""")

HIDE_SIDEBAR = ("<style>[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl'],"
                "[data-testid='collapsedControl']{display:none!important}</style>")


def inject_css(hide_sidebar: bool = False) -> None:
    """Apply the shared CSS theme and optionally hide navigation before onboarding."""
    st.markdown(CSS.safe_substitute(colors()), unsafe_allow_html=True)
    if hide_sidebar:
        st.markdown(HIDE_SIDEBAR, unsafe_allow_html=True)
