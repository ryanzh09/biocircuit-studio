from __future__ import annotations

import html
import json
import logging
import math
from pathlib import Path

import pandas as pd
import streamlit as st

from workflow_context import (PLAN_FIELDS, PRESET_PLANS, clean_plan, experiment_checklist,
    build_fit_lab_template, load_fit_lab_template_from_package)

from microfluidic_agent import (
    AREA_CM2_DEFAULT,
    DEFAULT_OPENAI_MODEL,
    ask_openai_design_agent,
    build_design_package,
    generate_openai_design_package,
    parse_requirement,
    summarize_existing_results,
)


ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT.parents[1] / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger("organoid_v2")
if not logger.handlers:
    handler = logging.FileHandler(LOG_DIR / "application.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
OPENAI_MODEL_OPTIONS = [
    DEFAULT_OPENAI_MODEL,
    "gpt-5.4",
    "gpt-5.2",
]


st.set_page_config(
    page_title="BioCircuit Studio | Chip Design Workshop",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>

    :root {
      --bg0: #f5f7fb;
      --bg1: #ffffff;
      --bg2: #eef3fb;
      --bg3: #f8fbff;
      --border: #d7e0ee;
      --border2: #b8c8df;
      --accent: #6dbaf7;
      --accent2: #2f6fb3;
      --accent-soft: rgba(109, 186, 247, 0.16);
      --text0: #121926;
      --text1: #405065;
      --text2: #6d7c90;
      --green: #2f7d62;
      --yellow: #9a6b16;
      --red: #b44c4c;
      --mono: "SFMono-Regular", "Fira Code", "Consolas", monospace;
      --serif: "Cormorant Garamond", "Baskerville", "Times New Roman", serif;
      --sans: "IBM Plex Sans", "Helvetica Neue", sans-serif;
    }
    .stApp {
      background:
        radial-gradient(circle at top right, rgba(109, 186, 247, 0.12), transparent 28%),
        linear-gradient(180deg, #f9fbfe 0%, #f3f6fb 52%, #f7f9fc 100%);
      color: var(--text0);
      font-family: var(--sans);
    }
    header[data-testid="stHeader"] {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
      background: transparent !important;
      height: 0 !important;
    }
    div[data-testid="stToolbar"] {
      display: none !important;
    }
    div[data-testid="stDecoration"] {
      display: none !important;
      visibility: hidden !important;
      pointer-events: none !important;
      height: 0 !important;
    }
    h1, h2, h3, h4, p, li, label, span { color: var(--text0); letter-spacing: 0; }
    h1, h2, h3 { font-family: var(--serif); letter-spacing: 0.01em; }
    h1 { font-size: 2.15rem; margin-bottom: 0.2rem; font-weight: 600; }
    h2 { font-size: 1.55rem; }
    h3 { font-size: 1.2rem; }
    h4 { font-family: var(--sans); font-weight: 600; }
    section[data-testid="stSidebar"] {
      background: var(--bg1); border-right: 1px solid var(--border);
    }
    .block-container { padding-top: 1rem; max-width: 1180px; }
    .top-nav-shell {
      position: relative;
      z-index: 40;
      pointer-events: auto;
      margin: 0 0 0.45rem;
    }
    .top-nav-title {
      margin-top: 0.2rem;
      color: var(--text2);
      font-size: 0.82rem;
    }
    textarea,
    input,
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {
      background: var(--bg0) !important;
      color: var(--text0) !important;
      border-color: var(--border2) !important;
      caret-color: var(--accent) !important;
      box-shadow: none !important;
    }
    input[type="number"],
    div[data-baseweb="input"] input[type="number"],
    input[type="number"]:focus,
    div[data-baseweb="input"] input[type="number"]:focus,
    input[type="number"]:invalid,
    div[data-baseweb="input"] input[type="number"]:invalid {
      border-color: var(--border2) !important;
      box-shadow: none !important;
      outline: none !important;
    }
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="popover"] div[role="listbox"] {
      background: var(--bg0) !important;
      color: var(--text0) !important;
      border-color: var(--border2) !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] div,
    div[data-baseweb="menu"] li,
    div[role="option"] {
      color: var(--text0) !important;
    }
    [data-baseweb="tag"] {
      background: var(--bg3) !important;
      border: 1px solid var(--border2) !important;
      color: var(--text1) !important;
    }
    [data-baseweb="tag"] span {
      color: var(--text1) !important;
    }
    .stMultiSelect [data-baseweb="select"] input {
      background: transparent !important;
    }
    .stButton > button,
    button[kind="secondary"],
    button[kind="primary"],
    button[data-testid="baseButton-secondary"],
    button[data-testid="baseButton-primary"] {
      background: var(--bg1) !important;
      border: 1px solid var(--border2) !important;
      border-radius: 12px !important;
      color: var(--text0) !important;
      font-weight: 600 !important;
      box-shadow: none !important;
    }
    .stButton > button:hover,
    button[kind="secondary"]:hover,
    button[kind="primary"]:hover,
    button[data-testid="baseButton-secondary"]:hover,
    button[data-testid="baseButton-primary"]:hover {
      background: var(--accent-soft) !important;
      border-color: var(--accent) !important;
      color: var(--accent) !important;
    }
    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
      background: var(--accent-soft) !important;
      border-color: var(--accent) !important;
      color: var(--accent) !important;
    }
    .stButton > button:disabled,
    button:disabled {
      background: var(--bg2) !important;
      border-color: var(--border) !important;
      color: var(--text2) !important;
      opacity: 0.75 !important;
    }
    div[data-testid="stForm"] {
      border: 1px solid var(--border);
      background: var(--bg1);
      border-radius: 8px;
      padding: 1rem;
    }
    div[data-testid="stTabs"] button {
      color: var(--text1); font-size: 0.86rem;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
      color: var(--accent);
    }
    div[data-testid="stMetric"] {
      background: rgba(255,255,255,0.88); border: 1px solid var(--border); border-radius: 14px; padding: 10px;
      box-shadow: 0 14px 30px rgba(25, 45, 78, 0.06);
    }
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      color: var(--text0);
    }
    .agent-note {
      background: rgba(255,255,255,0.88); border: 1px solid var(--border); border-left: 4px solid var(--accent);
      border-radius: 14px; padding: 12px 14px; margin: 8px 0 12px; color: var(--text1);
      font-size: 0.94rem; box-shadow: 0 12px 24px rgba(25, 45, 78, 0.05);
    }
    .source-ok {
      background: rgba(109, 186, 247, 0.12); border: 1px solid var(--accent); border-radius: 14px;
      padding: 10px 12px; margin-bottom: 8px; color: var(--text1);
    }
    .source-warn {
      background: rgba(154, 107, 22, 0.08); border: 1px solid var(--yellow); border-radius: 14px;
      padding: 10px 12px; margin-bottom: 8px; color: var(--text1);
    }
    .step-card, .section-card {
      background: rgba(255,255,255,0.9); border: 1px solid var(--border); border-radius: 16px;
      padding: 14px 15px; height: 100%; box-shadow: 0 18px 36px rgba(25, 45, 78, 0.05);
    }
    .step-card:hover {
      border-color: var(--accent);
      box-shadow: 0 0 0 1px rgba(109, 186, 247, 0.18), 0 18px 36px rgba(25, 45, 78, 0.05);
    }
    .step-card.active { border-color: var(--accent); box-shadow: 0 0 0 1px rgba(57,208,200,0.12); }
    .card-link {
      text-decoration: none !important;
      color: inherit !important;
      display: block;
      height: 100%;
    }
    .card-link:hover h4 {
      color: var(--accent);
    }
    .step-card .kicker {
      color: var(--accent2); font-family: var(--mono); font-size: 0.72rem; text-transform: uppercase;
      margin-bottom: 5px;
    }
    .step-card h4, .section-card h4 {
      margin: 0 0 6px 0; font-size: 0.94rem; color: var(--text0);
    }
    .step-card p, .section-card p {
      color: var(--text1); font-size: 0.82rem; margin: 0;
    }
    .pill-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .pill {
      display: inline-flex; align-items: center; border: 1px solid var(--border2); color: var(--text1);
      background: #f7fbff; border-radius: 999px; padding: 4px 10px; font-size: 0.76rem;
      font-family: var(--mono);
    }
    .callout-grid {
      display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin: 12px 0;
    }
    .flow-row {
      display: flex;
      align-items: stretch;
      gap: 10px;
      margin: 10px 0 16px;
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .flow-box {
      min-width: 154px;
      background: rgba(255,255,255,0.95);
      border: 1px solid var(--border2);
      border-radius: 14px;
      padding: 10px 12px;
      flex: 0 0 auto;
      box-shadow: 0 14px 28px rgba(25, 45, 78, 0.05);
    }
    .flow-box b {
      display: block;
      color: var(--text0);
      font-size: 0.84rem;
      margin-bottom: 4px;
    }
    .flow-box span {
      color: var(--text1);
      font-size: 0.78rem;
    }
    .flow-arrow {
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--accent);
      font-size: 1.15rem;
      min-width: 18px;
      flex: 0 0 auto;
    }
    .callout {
      background: rgba(255,255,255,0.9); border: 1px solid var(--border); border-radius: 14px; padding: 12px;
    }
    .callout b { display: block; font-size: 0.84rem; margin-bottom: 4px; color: var(--text0); }
    .callout span { color: var(--text1); font-size: 0.8rem; }
    .compact-list {
      margin: 0.25rem 0 0 0; padding-left: 1rem; color: var(--text1); font-size: 0.86rem;
    }
    .compact-list li { margin-bottom: 0.25rem; color: var(--text1); }
    .formula-box {
      background: rgba(255,255,255,0.92); border: 1px solid var(--border); border-radius: 14px;
      color: var(--accent); font-family: var(--mono); padding: 12px; font-size: 0.96rem;
    }
    div[data-testid="stExpander"] {
      background: rgba(255,255,255,0.9); border: 1px solid var(--border); border-radius: 14px;
    }
    div[data-testid="stExpander"] pre,
    div[data-testid="stExpander"] code,
    div[data-testid="stCodeBlock"] pre,
    div[data-testid="stCodeBlock"] code {
      background: #05080d !important;
      color: #f3f7fb !important;
    }
    .stDataFrame, div[data-testid="stTable"] {
      border: 1px solid var(--border); border-radius: 14px;
    }
    .hero-shell {
      background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(243,248,255,0.96) 100%);
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 26px 28px;
      margin: 4px 0 18px;
      box-shadow: 0 24px 40px rgba(25, 45, 78, 0.08);
    }
    .hero-shell h1 { margin: 0; }
    .hero-shell p {
      color: var(--text1);
      font-size: 1rem;
      margin: 0.4rem 0 0;
      max-width: 58rem;
    }
    .hero-kicker {
      color: var(--accent2);
      font-family: var(--mono);
      font-size: 0.76rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 0.55rem;
    }
    .home-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin: 16px 0 10px;
    }
    .home-card {
      background: rgba(255,255,255,0.95);
      border: 1px solid var(--border);
      border-radius: 22px;
      padding: 20px 20px 18px;
      box-shadow: 0 24px 40px rgba(25, 45, 78, 0.07);
    }
    .home-card .eyebrow {
      color: var(--accent2);
      font-family: var(--mono);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 0.55rem;
    }
    .home-card h3 { margin: 0 0 0.4rem; }
    .home-card p {
      color: var(--text1);
      margin: 0 0 0.75rem;
      font-size: 0.92rem;
    }
    .api-summary {
      background: rgba(255,255,255,0.92);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 14px 16px;
      margin: 0 0 14px;
      box-shadow: 0 18px 30px rgba(25, 45, 78, 0.06);
    }
    .api-summary b {
      display: block;
      margin-bottom: 4px;
      color: var(--text0);
    }
    .api-summary span {
      color: var(--text1);
      font-size: 0.9rem;
    }
    .api-summary .stTextInput,
    .api-summary .stSelectbox {
      margin-top: 0.8rem;
    }
    .chat-panel {
      background: rgba(255,255,255,0.94);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 14px 14px 12px;
      box-shadow: 0 18px 30px rgba(25, 45, 78, 0.06);
      position: sticky;
      top: 1rem;
    }
    .chat-log {
      max-height: 29rem;
      overflow-y: auto;
      margin-bottom: 0.75rem;
      padding-right: 0.2rem;
    }
    .chat-bubble {
      border-radius: 14px;
      padding: 10px 11px;
      margin-bottom: 8px;
      font-size: 0.84rem;
      line-height: 1.5;
      border: 1px solid var(--border);
      white-space: pre-wrap;
    }
    .chat-bubble.user {
      background: rgba(109, 186, 247, 0.12);
      border-color: rgba(109, 186, 247, 0.45);
    }
    .chat-bubble.assistant {
      background: rgba(255,255,255,0.95);
    }
    .chat-bubble b {
      display: block;
      margin-bottom: 0.28rem;
      color: var(--text0);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    @media (max-width: 900px) {
      .callout-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .home-grid { grid-template-columns: 1fr; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def split_lines(value: str) -> list[str]:
    return [v.strip() for v in value.replace(";", "\n").replace(",", "\n").splitlines() if v.strip()]


def bullet_list(items: list[str]) -> None:
    for item in items:
        st.markdown(f"- {item}")


def compact_list(items: list[str], limit: int | None = None) -> None:
    shown = items if limit is None else items[:limit]
    body = "".join(f"<li>{html.escape(item)}</li>" for item in shown)
    st.markdown(f'<ul class="compact-list">{body}</ul>', unsafe_allow_html=True)


def dataframe_or_empty(df: pd.DataFrame | None) -> None:
    if df is None or df.empty:
        st.info("No data available.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


def pills(items: list[str]) -> None:
    body = '<div class="pill-row">' + "".join(f'<span class="pill">{html.escape(item)}</span>' for item in items) + "</div>"
    st.markdown(body, unsafe_allow_html=True)


def step_card(step: str, title: str, text: str, active: bool = False, href: str | None = None) -> None:
    cls = "step-card active" if active else "step-card"
    card = f"""
      <div class="{cls}">
        <div class="kicker">{html.escape(step)}</div>
        <h4>{html.escape(title)}</h4>
        <p>{html.escape(text)}</p>
      </div>
    """
    if href:
        card = f'<a class="card-link" href="{html.escape(href)}">{card}</a>'
    st.markdown(card, unsafe_allow_html=True)


def workflow_hint(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="section-card">
          <h4>{html.escape(title)}</h4>
          <p>{html.escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def go_to_page(page_name: str) -> None:
    st.session_state["app_page"] = page_name


def render_top_nav(title: str) -> None:
    st.markdown('<div class="top-nav-shell">', unsafe_allow_html=True)
    button_cols = st.columns([0.22, 0.78])
    with button_cols[0]:
        st.button("Home", key=f"home_button_{title}", width="stretch", on_click=go_to_page, args=("home",))
    with button_cols[1]:
        st.markdown(f'<div class="top-nav-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_api_credentials_panel(*, compact: bool = False) -> None:
    if compact:
        with st.container(border=True):
            st.markdown("**OpenAI API connection**")
            st.markdown("Use your own ChatGPT API key to generate the workflow draft views. The key stays in this local Streamlit session and is only used when you generate a package.")
            st.caption("API unavailable? You can continue using premade templates with limited customization.")
            api_cols = st.columns([1.15, 0.85])
            with api_cols[0]:
                st.text_input(
                    "OpenAI API key",
                    key="openai_api_key",
                    type="password",
                    placeholder="sk-...",
                    help="Your key stays local in this Streamlit session and is used only when you click Generate Workflow Draft.",
                )
            with api_cols[1]:
                current_model = st.session_state.get("openai_model_name", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL
                if current_model not in OPENAI_MODEL_OPTIONS:
                    current_model = DEFAULT_OPENAI_MODEL
                st.selectbox(
                    "OpenAI model",
                    OPENAI_MODEL_OPTIONS,
                    key="openai_model_name",
                    help="Defaulted to the current recommended general-purpose model for complex tool-heavy workflows.",
                )
        return

    api_cols = st.columns([1.15, 0.85])
    with api_cols[0]:
        st.text_input(
            "OpenAI API key",
            key="openai_api_key",
            type="password",
            placeholder="sk-...",
            help="Your key stays local in this Streamlit session and is used only when you click Generate Workflow Draft.",
        )
    with api_cols[1]:
        current_model = st.session_state.get("openai_model_name", DEFAULT_OPENAI_MODEL) or DEFAULT_OPENAI_MODEL
        if current_model not in OPENAI_MODEL_OPTIONS:
            current_model = DEFAULT_OPENAI_MODEL
        st.selectbox(
            "OpenAI model",
            OPENAI_MODEL_OPTIONS,
            key="openai_model_name",
            help="Defaulted to the current recommended general-purpose model for complex tool-heavy workflows.",
        )


def render_home_page() -> None:
    st.markdown(
        """
        <div class="hero-shell">
          <div class="hero-kicker">Organ-on-Chip Planning and Impedance Analysis</div>
          <h1>BioCircuit Studio</h1>
          <p>This prototype explores how experimental information can be organized from organ-on-chip planning to electrochemical impedance spectroscopy (EIS) data analysis.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### Choose a Workspace")
    st.markdown(
        """
        <div class="home-grid">
          <div class="home-card">
            <div class="eyebrow">Design Path</div>
            <h3>Chip Design Workshop</h3>
            <p>Organize biological goals and experimental conditions into a structured experiment plan for researcher review.</p>
          </div>
          <div class="home-card">
            <div class="eyebrow">Data Path</div>
            <h3>Fit Lab</h3>
            <p>Explore how impedance spectra can be fitted with an electrical model and translated into parameters for comparison between experimental conditions.</p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    choice_cols = st.columns(2)
    with choice_cols[0]:
        st.button("Open Chip Design Workshop", key="home_open_agent", width="stretch", on_click=go_to_page, args=("agent",))
    with choice_cols[1]:
        st.button("Open Fit Lab", key="home_open_fitlab", width="stretch", on_click=go_to_page, args=("fitlab",))


def section_title(section_key: str) -> str:
    return {
        "summary": "Assay Summary",
        "build": "Build View",
        "operate": "Operate View",
        "analyze": "Analyze View",
        "export": "Export",
    }.get(section_key, "Current View")


def set_chat_open(is_open: bool) -> None:
    st.session_state["design_chat_open"] = is_open


def queue_chat_send(section_key: str) -> None:
    draft = st.session_state.get("design_chat_draft", "").strip()
    if not draft:
        return
    st.session_state["design_chat_pending"] = {"section": section_key, "message": draft}
    st.session_state["design_chat_draft"] = ""


def render_design_agent_chat(section_key: str) -> None:
    messages = st.session_state.setdefault("design_chat_messages", [])
    with st.container(border=True):
        top_cols = st.columns([0.74, 0.26])
        with top_cols[0]:
            st.markdown("#### Ask the Agent")
        with top_cols[1]:
            st.button("Close", key=f"close_chat_{section_key}", width="stretch", on_click=set_chat_open, args=(False,))

        if not messages:
            st.markdown("Ask the agent any questions, request any changes, or ask for clarification about the current design view.")

        if messages:
            log_body = ['<div class="chat-log">']
            for msg in messages:
                role = "user" if msg.get("role") == "user" else "assistant"
                title = "You" if role == "user" else "Agent"
                log_body.append(
                    f'<div class="chat-bubble {role}"><b>{html.escape(title)}</b>{html.escape(str(msg.get("content", "")))}</div>'
                )
            log_body.append("</div>")
            st.markdown("".join(log_body), unsafe_allow_html=True)

        st.text_area(
            "Design-agent message",
            key="design_chat_draft",
            height=110,
            label_visibility="collapsed",
            placeholder="Ask the agent any questions, request any changes, or ask for clarification about this design section.",
        )
        st.button("Send", key=f"send_chat_{section_key}", type="primary", width="stretch", on_click=queue_chat_send, args=(section_key,))


def use_current_design_in_fit_lab() -> None:
    package = st.session_state.get("package")
    if not isinstance(package, dict):
        return
    fit_lab_template = build_fit_lab_template(
        package,
        float(st.session_state.get("area_cm2", AREA_CM2_DEFAULT)),
    )
    package["fit_lab_template"] = fit_lab_template
    st.session_state["fit_lab_design_template"] = fit_lab_template
    st.session_state["app_page"] = "fitlab"


def clear_fit_lab_design_template() -> None:
    st.session_state.pop("fit_lab_design_template", None)
    st.session_state["fit_lab_package_uploader_nonce"] = (
        st.session_state.get("fit_lab_package_uploader_nonce", 0) + 1
    )


def render_fit_lab_panel(
    area_cm2: float,
    *,
    home_mode: bool = False,
    design_template: dict[str, object] | None = None,
) -> None:
    del home_mode
    html_path = ROOT / "fitlab_assets" / "eis_simulator_v2.html"
    if not html_path.exists():
        st.error(f"Bundled Fit Lab file is missing: {html_path}")
        return

    html_source = html_path.read_text(encoding="utf-8")
    chart_source = (ROOT / "fitlab_assets" / "chart.umd.js").read_text(encoding="utf-8")
    html_source = html_source.replace('<script src="chart.umd.js"></script>', '<script>' + chart_source + '</script>')
    context_json = json.dumps(design_template or {}, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    html_source = html_source.replace("/* WORKFLOW_CONTEXT */ {}", context_json)
    safe_area = area_cm2 if area_cm2 > 0 else AREA_CM2_DEFAULT


    if design_template:
        template_name = html.escape(str(design_template.get("template_name", "Custom chip design")))
        cells = ", ".join(str(item) for item in design_template.get("cells", [])) or "Not specified"
        readouts = ", ".join(str(item) for item in design_template.get("readouts", [])) or "EIS"
        circuit = html.escape(str(design_template.get("equivalent_circuit", "")))
        context_css = """
        <style>
        .workshop-template {
          border: 1px solid #b8d9f5; border-left: 5px solid #6dbaf7;
          border-radius: 10px; background: rgba(255,255,255,0.88);
          padding: 12px 14px; margin: 0 0 16px; color: #1a1a1a;
        }
        .workshop-template strong { display:block; font-size:14px; margin-bottom:5px; }
        .workshop-template span { display:block; color:#53657a; font-size:12px; line-height:1.5; }
        </style>
        """
        context_html = f"""
        <div class="workshop-template">
          <strong>Chip Design Workshop template loaded: {template_name}</strong>
          <span>Cells: {html.escape(cells)}</span>
          <span>Readouts: {html.escape(readouts)}</span>
          <span>Active sensing area: {safe_area:.4g} cm²</span>
          <span>Fitting model: {circuit}</span>
        </div>
        """
        html_source = html_source.replace("</head>", f"{context_css}</head>", 1)
        html_source = html_source.replace('<div class="container">', f'<div class="container">{context_html}', 1)

    st.iframe(html_source, width="stretch", height=2460)


def output_flow_row(steps: list[tuple[str, str]]) -> None:
    pieces: list[str] = ['<div class="flow-row">']
    for idx, (title, text) in enumerate(steps):
        pieces.append(
            f"""
            <div class="flow-box">
              <b>{html.escape(title)}</b>
              <span>{html.escape(text)}</span>
            </div>
            """
        )
        if idx < len(steps) - 1:
            pieces.append('<div class="flow-arrow">→</div>')
    pieces.append("</div>")
    st.markdown("".join(pieces), unsafe_allow_html=True)


def set_active_output_section(section_key: str) -> None:
    st.session_state["active_output_section"] = section_key


def render_output_nav(items: list[tuple[str, str]]) -> str:
    current = st.session_state.setdefault("active_output_section", items[0][0])
    widths: list[float] = []
    for idx in range(len(items)):
        widths.append(1.0)
        if idx < len(items) - 1:
            widths.append(0.2)
    cols = st.columns(widths)
    col_idx = 0
    for idx, (key, label) in enumerate(items):
        button_type = "primary" if current == key else "secondary"
        with cols[col_idx]:
            st.button(
                label,
                key=f"output_nav_{key}",
                type=button_type,
                width="stretch",
                on_click=set_active_output_section,
                args=(key,),
            )
        col_idx += 1
        if idx < len(items) - 1:
            with cols[col_idx]:
                st.markdown(
                    '<div style="display:flex; align-items:center; justify-content:center; width:100%; height:100%; min-height:2.6rem; margin:0; padding:0; color: var(--accent); font-size: 1.05rem; line-height:1;">→</div>',
                    unsafe_allow_html=True,
                )
            col_idx += 1
    return st.session_state.get("active_output_section", items[0][0])


def brief(items: list[str], n: int = 2) -> str:
    return " / ".join(items[:n]) if items else "not specified"


def workflow_graph() -> str:
    return """
    digraph {
      graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.5, ranksep=0.6]
      node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=11]
      edge [color="#39d0c8", fontcolor="#adbac7", arrowsize=0.7]
      user [label="Input"]
      kb [label="2-paper KB"]
      select [label="Chip"]
      protocol [label="Protocol"]
      analysis [label="Analysis"]
      report [label="Export"]
      user -> select
      kb -> select
      select -> protocol
      select -> analysis
      protocol -> report
      analysis -> report
    }
    """


def chip_graph(template_key: str) -> str:
    if template_key == "mdck_membrane_filter":
        return """
        digraph {
          graph [rankdir=LR, bgcolor="transparent", pad=0.25, nodesep=0.42, ranksep=0.7]
          node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=11]
          edge [color="#39d0c8", arrowsize=0.7]
          pump [label="Pump / medium reservoir"]
          apical_in [label="Apical inlet"]
          apical [label="Apical channel\\ndrug / media flow"]
          epithelium [label="Epithelial layer"]
          membrane [label="Basement membrane\\n/ porous support"]
          basal [label="Basal channel\\nreceiver flow"]
          basal_out [label="Outlet / collection"]
          instrument [label="EIS instrument"]
          pump -> apical_in -> apical -> epithelium -> membrane -> basal -> basal_out -> pump
          instrument -> epithelium [style=dashed]
        }
        """
    return """
    digraph {
      graph [rankdir=LR, bgcolor="transparent", pad=0.25, nodesep=0.42, ranksep=0.7]
      node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=11]
      edge [color="#39d0c8", arrowsize=0.7]
      pump [label="Pump / medium reservoir"]
      inlet [label="Inlet"]
      chamber [label="Perfusion channel\\nmedia or blood-like flow"]
      endothelium [label="Endothelium"]
      membrane [label="Basement membrane\\n/ ECM support"]
      outlet [label="Outlet / collection"]
      instrument [label="EIS instrument"]
      reference [label="Blank / reference lane"]
      pump -> inlet -> chamber -> endothelium -> membrane -> outlet -> pump
      instrument -> endothelium [style=dashed]
      reference -> membrane [style=dotted]
    }
    """


def chip_layer_graph(template_key: str) -> str:
    if template_key == "mdck_membrane_filter":
        return """
        digraph {
          graph [rankdir=TB, bgcolor="transparent", pad=0.15, nodesep=0.22, ranksep=0.28]
          node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=11, margin="0.12,0.08"]
          edge [color="#39d0c8", arrowsize=0.55]
          top [label="Apical microchannel\\ncell seeding + drug exposure"]
          cells [label="Epithelial monolayer\\nMDCK / epithelial barrier"]
          membrane [label="Porous membrane / filter\\nbarrier support"]
          basal [label="Basal microchannel\\nreceiver medium + sampling"]
          electrode [label="EIS electrode pair\\nacross barrier"]
          top -> cells -> membrane -> basal
          electrode -> membrane [style=dashed]
        }
        """
    return """
    digraph {
      graph [rankdir=TB, bgcolor="transparent", pad=0.15, nodesep=0.22, ranksep=0.28]
      node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=11, margin="0.12,0.08"]
      edge [color="#39d0c8", arrowsize=0.55]
      open [label="Open culture chamber\\ncell access + medium exchange"]
      cells [label="Endothelial barrier layer\\nover sensing region"]
      electrode [label="Planar EIS electrodes\\nunder barrier region"]
      substrate [label="Glass / polymer substrate\\nwith routed contact pads"]
      open -> cells -> electrode -> substrate
    }
    """


def chip_build_flow_graph(template_key: str) -> str:
    if template_key == "mdck_membrane_filter":
        template_label = "Membrane chip"
        alignment = "Align apical / basal layers"
        culture = "Seed epithelial cells\\non membrane"
        dose = "Dose apical side\\nsample basal side"
    else:
        template_label = "Open EIS chip"
        alignment = "Align chamber\\nto electrode region"
        culture = "Seed endothelial cells\\nover electrode window"
        dose = "Dose through inlet\\nmonitor barrier"
    return f"""
    digraph {{
      graph [rankdir=LR, bgcolor="transparent", pad=0.15, nodesep=0.35, ranksep=0.5]
      node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=10, margin="0.11,0.07"]
      edge [color="#39d0c8", arrowsize=0.6]
      a [label="1. Select\\n{template_label}"]
      b [label="2. Fabricate\\nelectrode substrate"]
      c [label="3. {alignment}"]
      d [label="4. Sterilize + prime\\nbubble-free channels"]
      e [label="5. {culture}"]
      f [label="6. Baseline EIS\\nthen drug protocol"]
      g [label="7. {dose}"]
      a -> b -> c -> d -> e -> f -> g
    }}
    """


def analyze_view_graph(template_key: str) -> str:
    if template_key == "mdck_membrane_filter":
        barrier_label = "Membrane-supported\\nepithelial barrier"
        reference_label = "Blank membrane\\nreference lane"
    else:
        barrier_label = "Endothelial barrier\\nover sensing region"
        reference_label = "Blank / no-cell\\nreference lane"
    return f"""
    digraph {{
      graph [rankdir=LR, bgcolor="transparent", pad=0.2, nodesep=0.4, ranksep=0.55]
      node [shape=box, style="rounded,filled", fillcolor="#161b22", color="#444c56", fontcolor="#e6edf3", fontname="Helvetica", fontsize=11]
      edge [color="#39d0c8", arrowsize=0.65]
      instrument [label="EIS instrument"]
      work [label="Working electrode"]
      sense [label="Counter / sense electrode"]
      barrier [label="{barrier_label}"]
      reference [label="{reference_label}"]
      model [label="Equivalent circuit\\nR_bulk + CPE + barrier RC"]
      instrument -> work
      instrument -> sense
      work -> barrier
      sense -> barrier
      barrier -> model [style=dashed]
      reference -> instrument [style=dotted]
    }}
    """


def chip_decision_summary(template_key: str) -> list[tuple[str, str, str]]:
    if template_key == "mdck_membrane_filter":
        return [
            ("Biology", "Polarized epithelial barrier", "Use apical-basal compartments."),
            ("Physical Structure", "Porous membrane / filter", "Cells form a supported monolayer across two compartments."),
            ("Readout", "EIS across barrier", "Pair with receiver-side sampling when needed."),
        ]
    return [
        ("Biology", "Endothelial barrier response", "Use open/perfusable EIS sensing."),
        ("Physical Structure", "Planar electrode region", "Cells sit over a fixed sensing area inside a perfused chamber."),
        ("Readout", "Longitudinal EIS / TEER", "Track barrier resistance and capacitance."),
    ]


ASSAY_PRESETS = {
    "Custom": {
        "goal": "Custom",
        "cells": [],
        "drugs": [],
        "readouts": [],
        "notes": "",
    },
    "Endothelial drug-response barrier assay": {
        "goal": "Drug response",
        "cells": ["iPSC-Endo", "Endothelial cells"],
        "drugs": ["Test compound"],
        "readouts": ["EIS", "TEER", "CLER", "CLEC", "CPE"],
        "notes": "Build an endothelial barrier chip for longitudinal impedance monitoring before and after drug exposure.",
    },
    "MDCK apical-basal transport assay": {
        "goal": "Permeability / transport",
        "cells": ["MDCK", "Epithelial cells"],
        "drugs": ["Apical drug dosing", "Basal receiver sampling"],
        "readouts": ["EIS", "TEER", "Barrier resistance", "Permeability support"],
        "notes": "Build a membrane-supported epithelial chip with apical-basal compartmentalization.",
    },
    "Barrier maturation time-course": {
        "goal": "Maturation time course",
        "cells": ["Barrier-forming cells"],
        "drugs": ["Culture maturation (no added perturbation)"],
        "readouts": ["EIS", "TEER", "Barrier resistance", "Capacitance", "Time course"],
        "notes": "Track barrier formation and stability over repeated EIS sweeps.",
    },
}

CELL_OPTIONS = [
    "iPSC-Endo",
    "Endothelial cells",
    "HUVEC",
    "HBMEC",
    "MDCK",
    "Epithelial cells",
    "Barrier-forming cells",
    "Caco-2",
    "Custom biological model",
]

DRUG_OPTIONS = [
    "Test compound",
    "Culture maturation (no added perturbation)",
    "Dose-response series",
    "Washout / recovery",
    "Apical drug dosing",
    "Basal drug dosing",
    "Basal receiver sampling",
    "Inflammatory stimulus",
    "No drug",
]

READOUT_OPTIONS = [
    "EIS",
    "TEER",
    "CLER",
    "CLEC",
    "CPE",
    "Barrier resistance",
    "Capacitance",
    "Nyquist plot",
    "Bode plot",
    "Permeability support",
    "Time course",
]

USER_OPTIONS_PATH = ROOT / "agent_user_options.json"


def unique_options(*groups: list[str]) -> list[str]:
    seen = set()
    merged = []
    for group in groups:
        for item in group:
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                merged.append(cleaned)
    return merged


def load_user_options() -> dict[str, list[str]]:
    if not USER_OPTIONS_PATH.exists():
        return {"cells": [], "drugs": [], "readouts": []}
    try:
        with USER_OPTIONS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"cells": [], "drugs": [], "readouts": []}
    return {
        "cells": [str(x) for x in data.get("cells", [])],
        "drugs": [str(x) for x in data.get("drugs", [])],
        "readouts": [str(x) for x in data.get("readouts", [])],
    }


def save_user_options(options: dict[str, list[str]]) -> None:
    clean = {
        "cells": unique_options(options.get("cells", [])),
        "drugs": unique_options(options.get("drugs", [])),
        "readouts": unique_options(options.get("readouts", [])),
    }
    with USER_OPTIONS_PATH.open("w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)


def add_option(category: str, value: str) -> None:
    cleaned = value.strip()
    if not cleaned:
        return
    options = st.session_state.setdefault("user_options", load_user_options())
    options[category] = unique_options(options.get(category, []), [cleaned])
    save_user_options(options)


def all_cell_options() -> list[str]:
    user = st.session_state.setdefault("user_options", load_user_options())
    return unique_options(CELL_OPTIONS, user.get("cells", []))


def all_drug_options() -> list[str]:
    user = st.session_state.setdefault("user_options", load_user_options())
    return unique_options(DRUG_OPTIONS, user.get("drugs", []))


def all_readout_options() -> list[str]:
    user = st.session_state.setdefault("user_options", load_user_options())
    return unique_options(READOUT_OPTIONS, user.get("readouts", []))


def option_defaults(preset_name: str) -> dict[str, list[str] | str]:
    return ASSAY_PRESETS[preset_name]


def compose_requirement(goal: str, cells: list[str], drugs: list[str], readouts: list[str], custom_notes: str) -> str:
    parts = [
        f"Goal: {goal}",
        f"Biological model: {', '.join(cells) if cells else 'not specified'}",
        f"Experimental condition: {', '.join(drugs) if drugs else 'not specified'}",
        f"Electrical readouts: {', '.join(readouts) if readouts else 'not specified'}",
    ]
    if custom_notes.strip():
        parts.append(f"Additional user notes: {custom_notes.strip()}")
    return ". ".join(parts)


def apply_preset_defaults(preset_name: str) -> None:
    defaults = option_defaults(preset_name)
    st.session_state["primary_goal"] = defaults["goal"]
    st.session_state["cell_model"] = defaults["cells"]
    st.session_state["drug_setup"] = defaults["drugs"]
    st.session_state["electrical_readouts"] = defaults["readouts"]
    st.session_state["custom_requirement"] = defaults["notes"]
    for field in PLAN_FIELDS:
        st.session_state[field] = PRESET_PLANS.get(preset_name, {}).get(field, "")
    st.session_state["_applied_preset"] = preset_name


def edit_current_workflow() -> None:
    snapshot = st.session_state.get("_input_snapshot", {})
    for key, value in snapshot.items():
        if value is not None:
            st.session_state[key] = value
    st.session_state["_applied_preset"] = snapshot.get("assay_preset", "Custom")
    st.session_state["preset_widget_version"] = st.session_state.get("preset_widget_version", 0) + 1
    st.session_state.generated = False


def queue_reset_input_page() -> None:
    st.session_state["_reset_requested"] = True


def clear_input_page_to_custom() -> None:
    st.session_state["preset_widget_version"] = st.session_state.get("preset_widget_version", 0) + 1
    st.session_state["assay_preset"] = "Custom"
    st.session_state["_applied_preset"] = "Custom"
    st.session_state["primary_goal"] = "Custom"
    st.session_state["custom_goal_text"] = ""
    st.session_state["cell_model"] = []
    st.session_state["drug_setup"] = []
    st.session_state["electrical_readouts"] = []
    st.session_state["custom_requirement"] = ""
    st.session_state["active_area_cm2"] = 0.0
    st.session_state["active_area_cm2_text"] = "0.0"
    st.session_state["new_cell_option"] = ""
    st.session_state["new_drug_option"] = ""
    st.session_state["new_readout_option"] = ""
    for field in PLAN_FIELDS:
        st.session_state[field] = ""


def generate_package_from_inputs(
    requirement_text: str,
    cells: list[str],
    drugs: list[str],
    readouts: list[str],
    api_key: str,
    model_name: str,
    plan: dict[str, str],
) -> dict[str, object]:
    req = parse_requirement(requirement_text, cells, drugs, readouts)
    req.update(clean_plan(plan))
    if api_key.strip():
        return generate_openai_design_package(req, api_key=api_key, model=model_name.strip() or DEFAULT_OPENAI_MODEL)
    package = build_design_package(req)
    package["generation"] = {
        "mode": "local_template",
        "model": "local_rule_based",
    }
    return package


def render_add_option(label: str, category: str, key: str) -> None:
    cols = st.columns([1, 0.25])
    with cols[0]:
        value = st.text_input(label, key=key, label_visibility="collapsed", placeholder=label)
    with cols[1]:
        if st.button("Add", key=f"add_{key}", width="stretch"):
            add_option(category, value)
            st.rerun()


def render_input_page() -> None:
    if st.session_state.pop("_reset_requested", False):
        clear_input_page_to_custom()
        st.rerun()

    render_top_nav("Chip Design Workshop")
    st.title("Chip Design Workshop")
    if st.session_state.get("openai_api_key", "").strip():
        st.markdown(
            f'<div class="source-ok">OpenAI API is connected. The current model is <b>{html.escape(st.session_state.get("openai_model_name", DEFAULT_OPENAI_MODEL))}</b>.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="source-warn">No OpenAI API key is loaded. The app will stay in local template mode until one is added below.</div>',
            unsafe_allow_html=True,
        )

    render_api_credentials_panel(compact=True)
    st.markdown("#### Workflow")
    workflow_cols = st.columns(5)
    with workflow_cols[0]:
        step_card("Step 1", "Preset", "Select an assay type as a starting point.", href="#step-1-preset")
    with workflow_cols[1]:
        step_card("Step 2", "Experimental Parameters", "Define the biological model, experimental condition, control, measurement schedule, and readouts.", href="#step-2-experimental-parameters")
    with workflow_cols[2]:
        step_card("Step 3", "Additional Experimental Details", "Specify available components, flow conditions, and other experimental constraints.", href="#step-3-optional-experiment-notes")
    with workflow_cols[3]:
        step_card("Step 4", "Generate Workflow Draft", "Generate a suggested configuration, experimental sequence, and analysis setup.", href="#step-4-generate-workflow-draft")
    with workflow_cols[4]:
        step_card(
            "Step 5",
            "Researcher Review",
            "Check the draft against the research question, supporting sources, and experimental constraints. Revise before use.",
        )

    st.caption("A researcher must review the AI-generated workflow before experimental use.")
    st.markdown('<div id="step-1-preset"></div>', unsafe_allow_html=True)
    st.subheader("Step 1 Preset")
    preset_name = st.selectbox(
        "Assay preset",
        list(ASSAY_PRESETS.keys()),
        index=list(ASSAY_PRESETS).index(st.session_state.get("assay_preset", "Custom")),
        key=f"preset_widget_{st.session_state.get('preset_widget_version', 0)}",
        help="Start here. This preloads the most likely cells, drug setup, readouts, and notes for a common assay type.",
    )
    st.session_state["assay_preset"] = preset_name
    if st.session_state.get("_applied_preset") != preset_name:
        apply_preset_defaults(preset_name)
        st.rerun()

    goal_options = ["Drug response", "Permeability / transport", "Maturation time course", "Toxicity screening", "Custom"]
    st.markdown('<div id="step-2-experimental-parameters"></div>', unsafe_allow_html=True)
    st.subheader("Step 2 Experimental Parameters")
    st.markdown(
        '<div class="agent-note">Define the biological model, experimental condition, control, measurement schedule, and readouts to establish the experimental plan.</div>',
        unsafe_allow_html=True,
    )
    select_cols = st.columns(3)
    with select_cols[0]:
        cells = st.multiselect(
            "Biological Model",
            all_cell_options(),
            key="cell_model",
            help="Pick the barrier-forming or organoid-related cell model you are designing around.",
        )
        render_add_option("Add a biological model", "cells", "new_cell_option")
    with select_cols[1]:
        drugs = st.multiselect(
            "Experimental Condition / Perturbation",
            all_drug_options(),
            key="drug_setup",
            help="Pick the perturbation or dosing conditions the chip should support.",
        )
        render_add_option("Add an experimental condition", "drugs", "new_drug_option")
    with select_cols[2]:
        readouts = st.multiselect(
            "Electrical readouts",
            all_readout_options(),
            key="electrical_readouts",
            help="Pick the impedance or barrier outputs you want the agent to optimize for.",
        )
        render_add_option("Add a new readout", "readouts", "new_readout_option")

    plan_cols = st.columns(2)
    with plan_cols[0]:
        st.text_input("Control Condition", key="control_condition", placeholder="Examples: untreated control, vehicle control, cell-free blank")
        st.text_area("Research Question", key="research_question", height=90, placeholder="What do you want to investigate?")
        st.text_input("Biological Sample Baseline", key="baseline_plan", placeholder="Example: impedance before applying the experimental condition")
    with plan_cols[1]:
        st.text_input("Time Points / Measurement Schedule", key="measurement_schedule", placeholder="Example: baseline before treatment, 24 h, 48 h, endpoint")
        st.caption("Example time points are proposed inputs for researcher review; enter the schedule appropriate to your study.")
        st.text_area("Planned Comparison", key="planned_comparison", height=90, placeholder="Define the groups, matched time points, and baseline comparison.")
        st.caption("A cell-free reference characterizes the device and medium. Record the biological sample’s pretreatment baseline separately.")

    st.markdown('<div id="step-3-optional-experiment-notes"></div>' , unsafe_allow_html=True)
    st.subheader("Step 3 Additional Experimental Details")
    config_cols = st.columns([1, 1])
    with config_cols[0]:
        st.markdown(
            '<div class="agent-note">Add any and all additional information about your study, constraints, goals, controls, timing, flow conditions, membrane needs, or other priorities here so the agent can personalize the design package as much as possible.</div>',
            unsafe_allow_html=True,
        )
        custom_notes = st.text_area(
            "Extra instructions for the agent",
            height=170,
            placeholder="Example: Use low shear during attachment, add a no-cell control lane, and prioritize repeated EIS sweeps before and after drug dosing.",
            key="custom_requirement",
            help="This is optional. The app already builds a request from the structured selections above.",
        )
    with config_cols[1]:
        goal = st.selectbox(
            "Primary goal",
            goal_options,
            key="primary_goal",
            help="Choose the main biological question so the app can favor the right chip architecture and fitting plan.",
        )
        if goal == "Custom":
            custom_goal = st.text_input(
                "Custom goal",
                key="custom_goal_text",
                placeholder="Describe your custom study goal",
                help="Use this when your study goal does not fit the preset categories above.",
            )
        else:
            custom_goal = ""
        if "active_area_cm2_text" not in st.session_state:
            st.session_state["active_area_cm2_text"] = str(st.session_state.get("active_area_cm2", AREA_CM2_DEFAULT))
        area_text = st.text_input(
            "Active area (cm²)",
            key="active_area_cm2_text",
            placeholder=str(AREA_CM2_DEFAULT),
            help="This area is used later for TEER-style area-normalized outputs.",
        )
        area_error = None
        try:
            area_cm2 = float(area_text)
            if not math.isfinite(area_cm2) or area_cm2 <= 0 or area_cm2 > 20:
                area_error = "Enter an active area greater than 0 and at most 20 cm²."
        except ValueError:
            area_cm2 = AREA_CM2_DEFAULT
            area_error = "Enter a valid numeric active area in cm²."
        if area_error:
            st.caption(area_error)

    metadata_cols = st.columns(2)
    with metadata_cols[0]:
        st.text_area("Measurement Settings", key="measurement_settings", height=90, placeholder="Specify frequency range, AC amplitude, instrument, and other relevant settings.")
        st.text_input("Data Export Plan", key="export_plan", placeholder="Example: matrix spectra CSV with fit results CSV and workflow JSON")
    with metadata_cols[1]:
        st.text_area("Experimental Metadata Plan", key="metadata_plan", height=90, placeholder="Specify how biological model, condition, control, sample/chip IDs, time points, replicates, active area, and measurement settings will be recorded.")
    plan = clean_plan({field: st.session_state.get(field, "") for field in PLAN_FIELDS})
    st.markdown("#### Experiment Checklist")
    for label, complete in experiment_checklist(cells, drugs, readouts, plan):
        st.markdown(f"{'✓' if complete else '○'} {label}")
    st.caption("Completion reflects entered planning information. Review its suitability before experimental use.")

    effective_goal = custom_goal.strip() if goal == "Custom" and custom_goal.strip() else goal
    requirement_text = compose_requirement(effective_goal, cells, drugs, readouts, custom_notes)
    requirement_text += "\n" + "\n".join(f"{field.replace('_', ' ').title()}: {value or 'not specified'}" for field, value in plan.items())
    with st.expander("Preview the request the agent will use"):
        st.code(requirement_text, language="text")

    st.markdown('<div id="step-4-generate-workflow-draft"></div>', unsafe_allow_html=True)
    st.subheader("Step 4: Generate Workflow Draft")
    action_cols = st.columns([1, 0.25])
    with action_cols[0]:
        run_agent = st.button("Generate Workflow Draft", key="generate_workflow_draft", type="primary", width="stretch")
    with action_cols[1]:
        st.button("Reset", key="reset_workflow_input", width="stretch", on_click=queue_reset_input_page)
    st.caption("Next step: researcher review of the generated workflow.")

    if run_agent:
        if area_error:
            st.error(area_error)
            st.stop()
        try:
            generated_package = generate_package_from_inputs(
                requirement_text,
                cells,
                drugs,
                readouts,
                st.session_state.get("openai_api_key", ""),
                st.session_state.get("openai_model_name", DEFAULT_OPENAI_MODEL),
                plan,
            )
        except Exception as exc:
            logger.exception("workflow_generation failed")
            st.error(f"Could not generate the workflow draft: {exc}. Details are in V2/logs/application.log.")
        else:
            generated_package["requirement"]["active_area_cm2"] = area_cm2
            generated_package["fit_lab_template"] = build_fit_lab_template(generated_package, area_cm2)
            st.session_state["_input_snapshot"] = {key: st.session_state.get(key) for key in (*PLAN_FIELDS, "assay_preset", "primary_goal", "custom_goal_text", "cell_model", "drug_setup", "electrical_readouts", "custom_requirement", "active_area_cm2_text")}
            st.session_state.package = generated_package
            st.session_state.area_cm2 = area_cm2
            st.session_state.generated = True
            st.rerun()

# Keep planning inputs when Streamlit removes widgets on other pages.
# Assignment detaches these saved values from the hidden widget lifecycle.
for saved_key in (*PLAN_FIELDS, "assay_preset", "primary_goal", "custom_goal_text",
                  "cell_model", "drug_setup", "electrical_readouts", "custom_requirement",
                  "active_area_cm2", "active_area_cm2_text", "new_cell_option",
                  "new_drug_option", "new_readout_option", "openai_api_key", "openai_model_name"):
    if saved_key in st.session_state:
        st.session_state[saved_key] = st.session_state[saved_key]
st.session_state.setdefault("generated", False)
st.session_state.setdefault("user_options", load_user_options())
st.session_state.setdefault("app_page", "home")
if "_applied_preset" not in st.session_state:
    apply_preset_defaults(st.session_state.get("assay_preset", "Custom"))

current_page = st.session_state.get("app_page", "home")

if current_page == "home":
    render_home_page()
    st.stop()

if current_page == "fitlab":
    render_top_nav("Fit Lab")
    st.title("Fit Lab")
    st.markdown(
        '<div class="agent-note">Bring in a Chip Design Workshop package to preserve the chip model and active sensing area, then upload matrix-style EIS CSV data after the physical experiment. In the spectra CSV, row 1 is the frequency axis in Hz, followed by one 4-row block per spectrum: |Z|, Re(Z), |Im(Z)| (or negative Im(Z)), then phase. Uploads remain unverified until you confirm their experimental provenance.</div>',
        unsafe_allow_html=True,
    )

    st.subheader("Design Template")
    package_upload = st.file_uploader(
        "Load a Chip Design Workshop package",
        type=["json"],
        key=f"fit_lab_package_uploader_{st.session_state.get('fit_lab_package_uploader_nonce', 0)}",
        help="Use the JSON downloaded from the Export step if you are returning after fabricating and running the chip.",
    )
    if package_upload is not None:
        try:
            uploaded_package = json.loads(package_upload.getvalue().decode("utf-8"))
            if not isinstance(uploaded_package, dict) or "selected_template" not in uploaded_package:
                raise ValueError("This is not a Chip Design Workshop package.")
            st.session_state["fit_lab_design_template"] = load_fit_lab_template_from_package(uploaded_package)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("workflow_import rejected: %s", type(exc).__name__)
            st.error(f"Could not load the workflow template: {exc}")

    fit_lab_template = st.session_state.get("fit_lab_design_template")
    if isinstance(fit_lab_template, dict):
        template_cols = st.columns([1.5, 1, 1, 0.65])
        template_cols[0].metric("Chip Template", str(fit_lab_template.get("template_name", "Custom design")))
        template_cols[1].metric("Cells", len(fit_lab_template.get("cells", [])))
        template_cols[2].metric("Active Area", f"{fit_lab_template['active_area_cm2']:.4g} cm²" if fit_lab_template.get("active_area_cm2") else "Not specified")
        template_cols[3].button(
            "Clear",
            key="clear_fit_lab_design",
            width="stretch",
            on_click=clear_fit_lab_design_template,
        )
        st.markdown(
            '<div class="source-ok">Confirm the experimental context and active sensing area before fitting. Each spectrum should remain linked to its sample condition, time point, and replicate.</div>',
            unsafe_allow_html=True,
        )
        fit_lab_area = float(fit_lab_template.get("active_area_cm2") or AREA_CM2_DEFAULT)
    else:
        st.markdown(
            '<div class="source-warn">No workshop template is connected. Confirm the experimental context and active sensing area below before fitting. Each spectrum should remain linked to its sample condition, time point, and replicate.</div>',
            unsafe_allow_html=True,
        )
        fit_lab_area = AREA_CM2_DEFAULT

    render_fit_lab_panel(
        fit_lab_area,
        home_mode=False,
        design_template=fit_lab_template if isinstance(fit_lab_template, dict) else None,
    )
    st.stop()

if not st.session_state.generated:
    render_input_page()
    st.stop()

render_top_nav("BioCircuit Studio · Workflow Draft")
package = st.session_state.package
template = package["selected_template"]
area_cm2 = st.session_state.get("area_cm2", AREA_CM2_DEFAULT)
package["requirement"]["active_area_cm2"] = area_cm2
package["fit_lab_template"] = build_fit_lab_template(package, area_cm2)
generation = package.get("generation", {"mode": "local_template", "model": "local_rule_based"})

st.title("Chip Design Workshop")
st.markdown(
    '<div class="agent-note">The workflow draft connects the research question to a suggested configuration, experimental sequence, and analysis setup. Review each section before experimental use.</div>',
    unsafe_allow_html=True,
)
if generation.get("mode") == "openai_api":
    st.markdown(
        f'<div class="source-ok">Generated with OpenAI API model <b>{html.escape(str(generation.get("model", DEFAULT_OPENAI_MODEL)))}</b>. The local template and source rules were used as the grounding scaffold.</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="source-warn">Running in local template mode. Add an OpenAI API key on the input page if you want the ChatGPT API to generate the workflow draft views.</div>',
        unsafe_allow_html=True,
    )

st.info("Workflow status: draft awaiting researcher review")
question_cols = st.columns(2)
with question_cols[0]:
    st.markdown("#### Research Question")
    st.write(package["requirement"].get("research_question") or "Not specified. Define the research question in Edit Input.")
with question_cols[1]:
    st.markdown("#### Planned Comparison")
    st.write(package["requirement"].get("planned_comparison") or "Not specified. Define the comparison in Edit Input.")
top_cols = st.columns([1.15, 0.9, 0.9, 0.9, 1.1])
top_cols[0].metric("Chip", "Endo" if template["key"] == "endo_open_eis" else "MDCK")
top_cols[1].metric("Cells", len(package["chip_design"]["cells"]))
top_cols[2].metric("Conditions", len(package["requirement"]["drugs"]))
top_cols[3].metric("Base Papers", len(package["knowledge_base"]))
top_cols[4].metric("Mode", "OpenAI API" if generation.get("mode") == "openai_api" else "Local")
st.button("Edit Input", key="edit_workflow_input", on_click=edit_current_workflow)

st.markdown("#### Output Flow")
active_output_section = render_output_nav(
    [
        ("summary", "Assay Summary"),
        ("build", "Build View"),
        ("operate", "Operate View"),
        ("analyze", "Analyze View"),
        ("export", "Export"),
    ]
)

pending_chat = st.session_state.pop("design_chat_pending", None)
if pending_chat:
    user_message = str(pending_chat.get("message", "")).strip()
    if user_message:
        st.session_state.setdefault("design_chat_messages", []).append({"role": "user", "content": user_message})
        try:
            reply = ask_openai_design_agent(
                package,
                str(pending_chat.get("section", active_output_section)),
                user_message,
                st.session_state.get("openai_api_key", ""),
                st.session_state.get("openai_model_name", DEFAULT_OPENAI_MODEL),
                chat_history=st.session_state["design_chat_messages"][:-1],
            )
        except Exception as exc:
            reply = f"Could not reach the agent: {exc}"
        st.session_state["design_chat_messages"].append({"role": "assistant", "content": reply})
        st.rerun()

st.session_state.setdefault("design_chat_open", True)
st.session_state.setdefault("design_chat_messages", [])
chat_open = st.session_state.get("design_chat_open", True)
layout_cols = st.columns([1.78, 0.9]) if chat_open else st.columns([1.92, 0.16])
main_col = layout_cols[0]
chat_col = layout_cols[1]

with chat_col:
    if chat_open:
        render_design_agent_chat(active_output_section)
    else:
        st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)
        st.button("Open\nAgent\nChat", key=f"open_chat_{active_output_section}", width="stretch", on_click=set_chat_open, args=(True,))

with main_col:
    st.subheader(section_title(active_output_section))

    if active_output_section == "summary":
        st.markdown('<div class="agent-note">Review the selected variables before continuing to the suggested configuration, experimental workflow, and analysis setup.</div>', unsafe_allow_html=True)
        summary = package.get("views", {}).get("assay_summary", {})
        if summary.get("agent_summary"):
            st.markdown(f'<div class="formula-box">{html.escape(summary["agent_summary"])}</div>', unsafe_allow_html=True)
        s0, s1 = st.columns([1.1, 1])
        with s0:
            st.markdown('<div class="section-card"><h4>Selected Template</h4><p>Current chip direction</p></div>', unsafe_allow_html=True)
            pills([summary.get("template_name", template["name"])])
        with s1:
            st.markdown('<div class="section-card"><h4>Cells</h4><p>Detected from user input</p></div>', unsafe_allow_html=True)
            pills(package["chip_design"]["cells"])
        s2, s3 = st.columns(2)
        with s2:
            st.markdown('<div class="section-card"><h4>Experimental Condition / Perturbation</h4><p>Selected condition</p></div>', unsafe_allow_html=True)
            pills(package["requirement"]["drugs"] or ["Not specified"])
            st.markdown("**Control Condition**")
            st.write(package["requirement"].get("control_condition") or "Not specified")
            st.markdown("**Proposed Measurement Schedule**")
            st.write(package["requirement"].get("measurement_schedule") or "Not specified")
            st.markdown("**Biological Sample Baseline**")
            st.write(package["requirement"].get("baseline_plan") or "Not specified")
        with s3:
            st.markdown('<div class="section-card"><h4>Readouts</h4><p>Measurement targets</p></div>', unsafe_allow_html=True)
            pills(package["chip_design"]["target_readouts"])
        extra_cols = st.columns(2)
        with extra_cols[0]:
            if summary.get("design_focus"):
                st.markdown("#### Design Focus")
                bullet_list(summary["design_focus"])
        with extra_cols[1]:
            if summary.get("risk_flags"):
                st.markdown("#### Risk Flags")
                bullet_list(summary["risk_flags"])

    if active_output_section == "build":
        st.markdown("#### Suggested Experimental Configuration")
        st.markdown(f'<div class="formula-box">{html.escape(template["name"])}</div>', unsafe_allow_html=True)
        build_view = package.get("views", {}).get("build_view", {})
        st.markdown('<div class="agent-note">This draft organizes available chip, fluidic, electrode, and measurement components around the selected experimental goals.</div>', unsafe_allow_html=True)
        if build_view.get("overview"):
            st.markdown(f'<div class="formula-box">{html.escape(build_view["overview"])}</div>', unsafe_allow_html=True)

        decision_cols = st.columns(3)
        for idx, (kicker, title, text) in enumerate(chip_decision_summary(template["key"])):
            with decision_cols[idx]:
                step_card(kicker, title, text)

        diagram_cols = st.columns([1, 1])
        with diagram_cols[0]:
            st.markdown("#### Layer Stack")
            st.graphviz_chart(chip_layer_graph(template["key"]), width="stretch")
        with diagram_cols[1]:
            st.markdown("#### Researcher Review")
            bullet_list(["Biological model compatibility", "Electrode configuration", "Fluidic configuration", "Assembly feasibility"])
            st.caption("Confirm component compatibility and assembly feasibility before experimental use.")
            st.markdown("#### Ports and Electrodes")
            with st.expander("Ports"):
                bullet_list(build_view.get("ports", package["chip_design"]["ports"]))
            with st.expander("Electrodes"):
                bullet_list(build_view.get("electrodes", package["chip_design"]["electrodes"]))

        detail_cols = st.columns(2)
        with detail_cols[0]:
            with st.expander("Architecture details"):
                bullet_list(build_view.get("architecture", package["chip_design"]["architecture"]))
        with detail_cols[1]:
            with st.expander("Layer stack notes"):
                bullet_list(build_view.get("layer_stack", []))
        extra_cols = st.columns(2)
        with extra_cols[0]:
            with st.expander("Port strategy"):
                bullet_list(build_view.get("ports", package["chip_design"]["ports"]))
        with extra_cols[1]:
            with st.expander("Electrode strategy"):
                bullet_list(build_view.get("electrodes", package["chip_design"]["electrodes"]))
        with st.expander("Design decisions"):
            bullet_list(build_view.get("design_decisions", []))
        with st.expander("Tuning rules"):
            bullet_list(package["chip_design"]["tuning"])

    if active_output_section == "operate":
        st.markdown("#### Experimental Workflow")
        operate_view = package.get("views", {}).get("operate_view", {})
        st.markdown('<div class="agent-note">Review the proposed experimental sequence, flow conditions, biological baseline, and measurement schedule before use.</div>', unsafe_allow_html=True)
        if operate_view.get("overview"):
            st.markdown(f'<div class="formula-box">{html.escape(operate_view["overview"])}</div>', unsafe_allow_html=True)
        st.markdown("#### Flow Diagram")
        st.graphviz_chart(chip_graph(template["key"]), width="stretch")
        st.caption("Solid arrows show the recirculating flow loop through the pump, chip, and biological layers. Dashed arrows show where the EIS instrument senses the barrier. Dotted arrows show an optional blank or reference comparison path.")
        with st.expander("Flow path notes"):
            bullet_list(operate_view.get("flow_path", []))

        st.markdown("#### Assay Timeline")
        stages = [
            ("Assemble", "Connect the chip, fluidic components, electrodes, and measurement system."),
            ("Culture / Stabilize", "Establish the biological model under defined flow conditions."),
            ("Baseline", "Record impedance before applying the experimental condition."),
            ("Perturb", "Apply the test compound or selected condition." if package["requirement"]["drugs"] != ["Culture maturation (no added perturbation)"] else "Continue culture under the selected maturation conditions; no added perturbation is planned."),
            ("Monitor", "Repeat EIS measurements at defined time points."),
            ("Endpoint", "Collect the final measurement and perform the planned validation."),
        ]
        for start in (0, 3):
            if start:
                st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
            stage_cols = st.columns(3)
            for idx, (title, description) in enumerate(stages[start:start + 3]):
                with stage_cols[idx]:
                    step_card(str(start + idx + 1), title, description)
        st.caption("Record flow conditions, sample identity, time points, and measurement settings throughout the experiment.")
        st.info("Record a separate cell-free reference measurement for the device and medium. The biological sample’s pretreatment baseline is recorded after culture stabilization and before applying the experimental condition.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### Assemble")
            compact_list(operate_view.get("assembly", package["assembly_instruction"]), limit=4)
            with st.expander("Full assembly instruction"):
                bullet_list(operate_view.get("assembly", package["assembly_instruction"]))
        with c2:
            st.markdown("#### Measure")
            compact_list(operate_view.get("measurement", package["measurement_protocol"]), limit=4)
            with st.expander("Full measurement protocol"):
                bullet_list(operate_view.get("measurement", package["measurement_protocol"]))
        with st.expander("Timeline focus"):
            bullet_list(operate_view.get("timeline_focus", []))

    if active_output_section == "analyze":
        analyze_view = package.get("views", {}).get("analyze_view", {})
        st.markdown('<div class="agent-note">This view connects the EIS measurement setup with the electrical model, data fitting, output parameters, and quality-control rules.<br>Fitting impedance spectra produces model-derived parameters that can support comparisons between experimental conditions.</div>', unsafe_allow_html=True)
        if analyze_view.get("overview"):
            st.markdown(f'<div class="formula-box">{html.escape(analyze_view["overview"])}</div>', unsafe_allow_html=True)
        st.markdown("#### Electrode and Model Map")
        st.graphviz_chart(analyze_view_graph(template["key"]), width="stretch")

        theory = package["theory_and_fitting"]
        st.markdown(f'<div class="formula-box">{html.escape(theory["equivalent_circuit"])}</div>', unsafe_allow_html=True)
        with st.expander("Sensing strategy"):
            bullet_list(analyze_view.get("sensing_strategy", []))

        c1, c2, c3 = st.columns(3)
        with c1:
            step_card("Input", "Files", brief(analyze_view.get("input_ports", package["data_analysis"]["input_ports"]), 1))
            with st.expander("Input ports"):
                bullet_list(analyze_view.get("input_ports", package["data_analysis"]["input_ports"]))
        with c2:
            step_card("Output", "Results", brief(analyze_view.get("outputs", package["data_analysis"]["outputs"]), 1))
            with st.expander("Output files"):
                bullet_list(analyze_view.get("outputs", package["data_analysis"]["outputs"]))
        with c3:
            step_card("QC", "Rules", brief(analyze_view.get("qc_rules", package["data_analysis"]["qc_rules"]), 1))
            st.caption("Interpret model-derived parameters together with fit quality, experimental conditions, and the assumptions of the electrical model.")
            with st.expander("QC rules"):
                bullet_list(analyze_view.get("qc_rules", package["data_analysis"]["qc_rules"]))

        t1, t2 = st.columns(2)
        with t1:
            st.markdown("#### Parameters")
            compact_list(theory["terms"], limit=3)
            with st.expander("All model terms"):
                bullet_list(theory["terms"])
        with t2:
            st.markdown("#### Method")
            compact_list(theory["fitting"], limit=3)
            with st.expander("All fitting details"):
                bullet_list(theory["fitting"])
        with st.expander("Fitting focus"):
            bullet_list(analyze_view.get("fitting_focus", []))
        with st.expander("Parameter bounds"):
            st.dataframe(
                pd.DataFrame(theory["parameter_bounds"]).T.rename(columns={0: "low", 1: "high"}),
                width="stretch",
            )

        existing = summarize_existing_results()
        if existing:
            st.markdown("#### Local Result Snapshot")
            m1, m2, m3 = st.columns(3)
            table = existing["table"]
            m1.metric("Rows", existing["rows"])
            if "TEER_Ohm_cm2" in table:
                m2.metric("Peak TEER", f"{table['TEER_Ohm_cm2'].max():.2f} Ω·cm²")
            if "CLER_Ohm" in table:
                m3.metric("Peak CLER", f"{table['CLER_Ohm'].max():.2f} Ω")
            with st.expander("Summary table"):
                st.dataframe(existing["summary"], width="stretch")

    if active_output_section == "export":
        st.markdown(
            '<div class="agent-note">The proposed export links the analysis setup with experimental metadata, so each dataset retains the conditions under which it was collected.</div>',
            unsafe_allow_html=True,
        )
        st.button(
            "Open Workflow in Fit Lab",
            key="open_workflow_fit_lab",
            type="primary",
            width="stretch",
            on_click=use_current_design_in_fit_lab,
        )
        package_json = json.dumps(package, indent=2, ensure_ascii=False)
        st.download_button(
            "Download JSON",
            data=package_json.encode("utf-8"),
            file_name="microfluidic_eis_agent_design_package.json",
            mime="application/json",
        )
        export_cols = st.columns(2)
        with export_cols[0]:
            with st.expander("Preview JSON"):
                st.code(package_json, language="json")
        with export_cols[1]:
            st.markdown("#### Metadata to Include")
            bullet_list(["Biological model", "Experimental condition and control", "Time point", "Chip ID and sample ID", "Active sensing area", "Measurement settings"])
            st.caption("The workflow carries the proposed plan. Enter sample-specific identifiers, actual time points, replicates, and settings in Fit Lab; unknown values remain empty.")
