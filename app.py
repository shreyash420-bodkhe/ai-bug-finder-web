from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

import streamlit as st

from auth_manager import AuthStore
from database import BugDatabase, HistoryStore
from engine import analyze_project_folder, create_fixed_project_zip, detect_bugs
from engine.ai_assistant import analyze_with_ai
from reports import create_json_report, create_pdf_report, report_as_markdown

st.set_page_config(page_title="AI Bug Finder", page_icon=":material/bug_report:", layout="wide")

try:
    deployment_secrets = st.secrets
except FileNotFoundError:
    deployment_secrets = {}

for secret_name in ("BUGFINDER_ADMIN_EMAIL", "BUGFINDER_ADMIN_PASSWORD"):
    if not os.getenv(secret_name) and deployment_secrets.get(secret_name):
        os.environ[secret_name] = str(deployment_secrets[secret_name])

auth_store = AuthStore()
history_store = HistoryStore()
auth_enabled = os.getenv("BUGFINDER_AUTH_ENABLED", "true").lower() == "true"

if auth_enabled:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("account_email", None)

    if not st.session_state["authenticated"]:
        st.html(
            """
            <style>
            @keyframes robot-idle { 0%, 100% { translate: 0 0; rotate: -1deg; } 50% { translate: 0 -5px; rotate: 1deg; } }
            @keyframes robot-type { 0%, 100% { translate: 0 0; } 50% { translate: 0 4px; } }
            @keyframes scan-sweep { 0% { transform: translateY(-58px); opacity: 0; } 16%, 84% { opacity: .9; } 100% { transform: translateY(68px); opacity: 0; } }
            @keyframes code-glow { 0%, 100% { opacity: .7; } 50% { opacity: 1; } }
            @keyframes signal-blink { 0%, 100% { opacity: .35; } 50% { opacity: 1; } }
            [data-testid="stAppViewContainer"] { background: #f5f2e9; }
            [data-testid="stHeader"] { background: transparent; }
            [data-testid="stMainBlockContainer"] { max-width: 1120px; padding-top: 2.4rem; padding-bottom: 3rem; }
            .auth-art { min-height: 620px; height: 100%; box-sizing: border-box; overflow: hidden; position: relative; display: flex; flex-direction: column; justify-content: space-between; padding: 38px; border-radius: 20px; color: #fffdf3; background: linear-gradient(145deg, #123c56 0%, #102c46 58%, #192b43 100%); }
            .auth-art:before { content: ''; position: absolute; inset: 0; pointer-events: none; opacity: .13; background-image: linear-gradient(rgba(255,255,255,.35) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.35) 1px, transparent 1px); background-size: 30px 30px; mask-image: linear-gradient(135deg, black, transparent 78%); }
            .auth-art > * { position: relative; z-index: 1; }
            .auth-brand { display: flex; align-items: center; gap: 12px; color: #f7f2df; font: 500 12px 'DM Mono', monospace; letter-spacing: 1px; text-transform: uppercase; }
            .auth-brand-mark { width: 34px; height: 34px; position: relative; display: inline-block; border: 1px solid rgba(255,255,255,.32); border-radius: 11px; background: #f4bd4d; }
            .auth-brand-mark:before, .auth-brand-mark:after { content: ''; position: absolute; top: 9px; width: 8px; height: 15px; border-radius: 8px; background: #173d35; }
            .auth-brand-mark:before { left: 7px; transform: rotate(-18deg); }
            .auth-brand-mark:after { right: 7px; transform: rotate(18deg); }
            .auth-copy { max-width: 390px; }
            .auth-copy h1 { margin: 0 0 12px; color: #fffdf3; font: 700 42px/1.08 'Manrope', 'Trebuchet MS', sans-serif; letter-spacing: 0; }
            .auth-copy p { margin: 0; max-width: 330px; color: #c4d7c9; font: 400 15px/1.65 'Manrope', 'Trebuchet MS', sans-serif; }
            .workstation-stage { height: 245px; position: relative; margin: 10px 0 12px; }
            .workstation-scene { width: 420px; height: 230px; position: absolute; top: 0; left: 50%; transform: translateX(-50%); transform-origin: center top; }
            .code-monitor { position: absolute; z-index: 2; top: 26px; left: 22px; width: 152px; height: 130px; }
            .monitor-frame { height: 116px; box-sizing: border-box; padding: 8px; border: 5px solid #102338; border-radius: 10px; background: linear-gradient(145deg, #1b2a40, #0b1729); box-shadow: 0 12px 24px rgba(0,0,0,.3), 0 0 18px rgba(32,202,238,.2); }
            .monitor-screen { height: 100%; overflow: hidden; padding: 5px 7px; box-sizing: border-box; border-radius: 3px; background: #101b30; }
            .screen-top { display: flex; gap: 4px; margin-bottom: 8px; }
            .screen-top i { width: 5px; height: 5px; border-radius: 50%; background: #f47888; }
            .screen-top i:nth-child(2) { background: #f2c66e; } .screen-top i:nth-child(3) { background: #7bdaa8; }
            .code-line { display: block; height: 4px; margin: 6px 0; border-radius: 4px; background: #56d9e2; box-shadow: 0 0 7px rgba(86,217,226,.35); animation: code-glow 2.4s ease-in-out infinite; }
            .code-line:nth-child(3n) { background: #f4c36b; } .code-line:nth-child(3n + 1) { background: #f47f92; }
            .code-line.short { width: 34%; } .code-line.medium { width: 58%; } .code-line.long { width: 82%; }
            .monitor-neck { width: 30px; height: 15px; margin: -1px auto 0; background: #173751; }
            .monitor-base { width: 72px; height: 6px; margin: 0 auto; border-radius: 6px 6px 2px 2px; background: #1a3952; }
            .desk { position: absolute; z-index: 1; left: 5px; right: 6px; top: 185px; height: 9px; border-radius: 8px; background: linear-gradient(90deg, #264f69, #386782, #183c55); box-shadow: 0 8px 12px rgba(0,0,0,.18); }
            .keyboard { position: absolute; z-index: 2; left: 132px; top: 168px; width: 164px; height: 21px; box-sizing: border-box; padding: 5px 8px; display: flex; gap: 4px; border: 1px solid #456f87; border-radius: 5px 5px 8px 8px; background: linear-gradient(#304e66, #182f46); transform: skewX(-15deg); }
            .keyboard i { flex: 1; height: 3px; border-radius: 2px; background: #65d9df; opacity: .75; }
            .robot { position: absolute; z-index: 3; top: 3px; left: 204px; width: 192px; height: 212px; animation: robot-idle 3.8s ease-in-out infinite; }
            .robot-head { position: absolute; z-index: 4; top: 24px; left: 39px; width: 132px; height: 93px; box-sizing: border-box; padding: 11px; border: 3px solid #173449; border-radius: 34px 39px 30px 30px; background: linear-gradient(135deg, #77e8ef 0%, #28a9ce 54%, #ee83a3 100%); box-shadow: inset -8px -7px 0 rgba(8,36,62,.22), 0 9px 16px rgba(0,0,0,.2); }
            .robot-face { width: 100%; height: 100%; position: relative; border: 2px solid rgba(98,222,239,.48); border-radius: 23px; background: #10172a; box-shadow: inset 0 0 19px rgba(12,8,25,.9), 0 0 13px rgba(39,209,238,.26); }
            .robot-eye { position: absolute; top: 23px; width: 12px; height: 19px; border-radius: 50%; background: #fff0a0; box-shadow: 0 0 13px rgba(255,231,126,.95); animation: signal-blink 3.6s ease-in-out infinite; }
            .robot-eye.left { left: 22px; } .robot-eye.right { right: 22px; }
            .robot-mouth { position: absolute; left: calc(50% - 3px); bottom: 12px; width: 6px; height: 4px; border-radius: 50%; background: #f3a36d; box-shadow: 0 0 7px #f3a36d; }
            .robot-ear { position: absolute; z-index: 3; top: 52px; width: 17px; height: 29px; border: 3px solid #173449; border-radius: 9px; background: #29bbd5; box-shadow: 0 0 9px rgba(38,210,239,.55); }
            .robot-ear.left { left: 29px; } .robot-ear.right { right: 9px; }
            .robot-neck { position: absolute; z-index: 2; top: 111px; left: 89px; width: 34px; height: 18px; border-radius: 6px; background: linear-gradient(90deg, #173449, #344b60, #173449); }
            .robot-body { position: absolute; z-index: 2; top: 125px; left: 53px; width: 100px; height: 76px; box-sizing: border-box; border: 3px solid #173449; border-radius: 29px 30px 21px 21px; background: linear-gradient(135deg, #e9f0e8, #9fcbd0 58%, #d6819c); box-shadow: inset -9px -7px 0 rgba(20,54,79,.18); }
            .robot-body:before { content: ''; position: absolute; top: 10px; left: 43px; width: 10px; height: 10px; border: 2px solid #42cfe0; border-radius: 50%; background: #18334b; box-shadow: 0 0 9px #42cfe0; }
            .robot-arm { position: absolute; z-index: 3; top: 137px; left: -8px; width: 112px; height: 25px; border: 3px solid #173449; border-radius: 18px; background: linear-gradient(90deg, #d7e5e2, #61b7cb); transform-origin: right center; animation: robot-type .28s ease-in-out infinite; }
            .robot-arm.second { top: 155px; left: -20px; width: 119px; height: 22px; background: linear-gradient(90deg, #afd4d6, #48a8c0); animation-delay: .14s; }
            .robot-hand { position: absolute; left: -8px; top: 3px; width: 20px; height: 17px; border: 2px solid #173449; border-radius: 8px; background: #74dbe1; }
            .scan-beam { position: absolute; z-index: 5; top: 92px; left: calc(50% - 153px); width: 306px; height: 3px; border-radius: 4px; pointer-events: none; background: #9af0f1; box-shadow: 0 0 13px rgba(77,224,245,.95); animation: scan-sweep 2.8s ease-in-out infinite; }
            .ai-scan-chip { position: absolute; z-index: 5; top: 2px; right: 4px; display: flex; align-items: center; gap: 6px; padding: 6px 9px; border: 1px solid rgba(106,224,239,.5); border-radius: 7px; background: rgba(14,37,59,.9); color: #b8f4f2; font: 500 10px 'DM Mono', monospace; text-transform: uppercase; }
            .ai-scan-chip:before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: #a7edc1; animation: signal-blink 1.2s ease-in-out infinite; }
            .auth-art-foot { display: flex; align-items: center; justify-content: space-between; padding-top: 16px; border-top: 1px solid rgba(255,255,255,.2); color: #c4d7c9; font: 400 11px 'DM Mono', monospace; letter-spacing: .5px; text-transform: uppercase; }
            .auth-ready { display: inline-flex; align-items: center; gap: 8px; }
            .auth-ready:before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: #a7d879; animation: signal-blink 1.7s ease-in-out infinite; }
            .auth-form-heading { margin: 0 0 5px; color: #183c34; font: 800 29px/1.2 'Manrope', 'Trebuchet MS', sans-serif; letter-spacing: 0; }
            .auth-form-note { margin: 0 0 22px; color: #64736c; font: 400 14px/1.5 'Manrope', 'Trebuchet MS', sans-serif; }
            [data-testid="stVerticalBlockBorderWrapper"] { border-color: #e6e0d2; border-radius: 17px; background: rgba(255,255,255,.83); box-shadow: 0 18px 45px rgba(26,55,46,.08); }
            [data-testid="stTextInput"] input { border-radius: 10px; }
            .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #e6e0d2; }
            .stTabs [data-baseweb="tab"] { padding: 10px 14px; }
            .stTabs [aria-selected="true"] { color: #173d35; }
            .stFormSubmitButton > button { min-height: 46px; border: 0; border-radius: 10px; background: #173d35; color: white; font-weight: 700; transition: transform .18s ease, background .18s ease; }
            .stFormSubmitButton > button:hover { transform: translateY(-2px); background: #245d4d; color: white; }
            @media (max-width: 760px) { [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 2rem; } .auth-art { min-height: 420px; padding: 26px; } .auth-copy h1 { font-size: 34px; } .workstation-stage { height: 190px; } .workstation-scene { transform: translateX(-50%) scale(.68); } .ai-scan-chip { top: 0; right: 20px; } }
            @media (prefers-reduced-motion: reduce) { *, *:before, *:after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; scroll-behavior: auto !important; transition-duration: .01ms !important; } }
            </style>
            """
        )

        visual_col, form_col = st.columns([1.05, 0.95], gap="large", vertical_alignment="center")
        with visual_col:
            st.html(
                """
                <section class="auth-art" aria-label="AI Bug Finder login">
                    <div class="auth-brand"><span class="auth-brand-mark"></span><span>AI Bug Finder / Private workspace</span></div>
                    <div class="auth-copy">
                        <h1>Catch the little things.</h1>
                        <p>A clear place to inspect your Python and keep your fixes close.</p>
                    </div>
                    <div class="workstation-stage" aria-hidden="true">
                        <div class="workstation-scene">
                            <div class="ai-scan-chip">AI scan</div>
                            <div class="code-monitor">
                                <div class="monitor-frame">
                                    <div class="monitor-screen">
                                        <div class="screen-top"><i></i><i></i><i></i></div>
                                        <span class="code-line long"></span><span class="code-line medium"></span>
                                        <span class="code-line short"></span><span class="code-line long"></span>
                                        <span class="code-line medium"></span><span class="code-line short"></span>
                                        <span class="code-line long"></span>
                                    </div>
                                </div>
                                <div class="monitor-neck"></div><div class="monitor-base"></div>
                            </div>
                            <div class="desk"></div>
                            <div class="keyboard"><i></i><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
                            <div class="robot">
                                <span class="robot-ear left"></span><span class="robot-ear right"></span>
                                <div class="robot-head">
                                    <div class="robot-face"><span class="robot-eye left"></span><span class="robot-eye right"></span><span class="robot-mouth"></span></div>
                                </div>
                                <div class="robot-neck"></div><div class="robot-body"></div>
                                <div class="robot-arm"><span class="robot-hand"></span></div>
                                <div class="robot-arm second"><span class="robot-hand"></span></div>
                            </div>
                            <div class="scan-beam"></div>
                        </div>
                    </div>
                    <div class="auth-art-foot"><span>Python inspection desk</span><span class="auth-ready">All systems ready</span></div>
                </section>
                """
            )

        with form_col:
            st.markdown('<div class="auth-form-heading">Welcome back</div>', unsafe_allow_html=True)
            st.markdown('<p class="auth-form-note">Sign in or create your account to continue.</p>', unsafe_allow_html=True)
            with st.container(border=True):
                register_tab, login_tab = st.tabs(["Register", "Login"])

                with register_tab:
                    with st.form("register_form"):
                        registration_email = st.text_input("Email address", key="registration_email")
                        registration_password = st.text_input("Password", type="password", key="registration_password")
                        confirm_password = st.text_input("Confirm password", type="password", key="confirm_password")
                        register_submitted = st.form_submit_button("Create account", type="primary")

                    if register_submitted:
                        if registration_password != confirm_password:
                            st.error("The passwords do not match.")
                        else:
                            registration_status = auth_store.register_user(registration_email, registration_password)
                            if registration_status == "registered":
                                st.success("Account created. Select Login and sign in with your email and password.")
                            elif registration_status == "invalid_email":
                                st.error("Enter a valid email address.")
                            elif registration_status == "weak_password":
                                st.error("Choose a password with at least 8 characters.")
                            elif registration_status == "already_registered":
                                st.error("An account with that email already exists.")
                            else:
                                st.error("That email address is reserved for the administrator.")

                with login_tab:
                    st.caption("New here? Register first, then return to log in with your email.")
                    with st.form("login_form"):
                        login_email = st.text_input("Email address", key="login_email")
                        login_password = st.text_input("Password", type="password", key="login_password")
                        login_submitted = st.form_submit_button("Login", type="primary")

                    if login_submitted:
                        is_valid, role = auth_store.validate_login(login_email, login_password)
                        if is_valid:
                            st.session_state["authenticated"] = True
                            st.session_state["role"] = role
                            st.session_state["account_email"] = login_email.strip().lower()
                            st.rerun()
                        st.error("Sign-in failed. If you have not registered yet, register first, then log in.")
        st.stop()

    if st.sidebar.button("Log out", icon=":material/logout:"):
        st.session_state["authenticated"] = False
        st.session_state["role"] = None
        st.session_state["account_email"] = None
        st.rerun()

    if st.session_state["role"] == "admin":
        st.title("Administrator")
        st.caption("Registered account emails and analysis history. Passwords are never shown or stored in plaintext.")
        st.subheader("Registered users")
        users = auth_store.list_users()
        if users:
            st.dataframe(users, hide_index=True, width="stretch")
        else:
            st.info("No user accounts have been registered yet.")

        st.subheader("Analysis history")
        all_history = list(reversed(history_store.list_all()))
        if all_history:
            history_rows = [
                {
                    "Email": record["user"],
                    "File": record["filename"],
                    "Created": record["created_at"].replace("T", " ")[:19],
                    "Findings": record["result"].get("summary", {}).get("total", 0),
                }
                for record in all_history
            ]
            st.dataframe(history_rows, hide_index=True, width="stretch")
            selected_record_label = st.selectbox(
                "Review an analysis",
                [
                    f"{record['user']} · {record['filename']} · {record['created_at'].replace('T', ' ')[:16]}"
                    for record in all_history
                ],
            )
            selected_record = all_history[
                [
                    f"{record['user']} · {record['filename']} · {record['created_at'].replace('T', ' ')[:16]}"
                    for record in all_history
                ].index(selected_record_label)
            ]
            with st.expander("View saved source and findings"):
                st.code(selected_record["source"], language="python")
                for issue in selected_record["result"].get("issues", []):
                    st.write(f"{issue.get('severity', 'finding')}: {issue.get('title', 'Issue')}")
                    st.caption(issue.get("message", ""))
        else:
            st.info("No analysis history has been saved yet.")
        st.stop()

    account_email = st.session_state["account_email"]
else:
    account_email = "Developer"

st.html(
        """
        <style>
        @keyframes hero-in { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes signal-pulse { 0%, 100% { box-shadow: 0 0 0 0 rgba(14, 116, 144, .28); } 50% { box-shadow: 0 0 0 7px rgba(14, 116, 144, 0); } }
        @keyframes button-sheen { from { transform: translateX(-130%) skewX(-18deg); } to { transform: translateX(240%) skewX(-18deg); } }
        [data-testid="stAppViewContainer"] { background: linear-gradient(145deg, #f7fafc 0%, #eef7f8 55%, #f8fbfc 100%); }
        [data-testid="stHeader"] { background: rgba(247, 250, 252, .72); }
        .block-container { max-width: 1480px; padding-top: 2.5rem; padding-bottom: 4rem; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color: rgba(14, 116, 144, .18); border-radius: 18px; box-shadow: 0 14px 36px rgba(23, 32, 42, .06); }
        .stTabs [data-baseweb="tab-list"] { gap: .45rem; padding: .4rem; border: 1px solid rgba(14, 116, 144, .14); border-radius: 14px; background: rgba(255, 255, 255, .66); }
        .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: .65rem 1rem; transition: background .2s ease, color .2s ease; }
        .stTabs [aria-selected="true"] { background: #d7eef1; color: #075985; }
        .stButton > button, .stFormSubmitButton > button { position: relative; overflow: hidden; border-radius: 11px; transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease; }
        .stButton > button:after, .stFormSubmitButton > button:after { content: ""; position: absolute; top: -20%; left: 0; width: 28%; height: 140%; opacity: 0; background: rgba(255,255,255,.42); transform: translateX(-130%) skewX(-18deg); }
        .stButton > button:hover, .stFormSubmitButton > button:hover { transform: translateY(-2px); border-color: rgba(14, 116, 144, .5); box-shadow: 0 8px 18px rgba(14, 116, 144, .2); }
        .stButton > button:hover:after, .stFormSubmitButton > button:hover:after { opacity: 1; animation: button-sheen .65s ease-out; }
        .stButton > button:active, .stFormSubmitButton > button:active { transform: translateY(1px) scale(.98); box-shadow: 0 3px 8px rgba(14, 116, 144, .14); }
        .stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible { outline: 3px solid rgba(14, 116, 144, .28); outline-offset: 2px; }
        .hero { animation: hero-in .55s ease-out both; position: relative; overflow: hidden; padding: 2rem 2.25rem; margin-bottom: 1.5rem; border: 1px solid rgba(14, 116, 144, .2); border-radius: 22px; background: linear-gradient(115deg, rgba(255,255,255,.94), rgba(219,242,244,.88)); box-shadow: 0 18px 44px rgba(23, 32, 42, .08); }
        .hero:after { content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .45; background-image: linear-gradient(rgba(14,116,144,.07) 1px, transparent 1px), linear-gradient(90deg, rgba(14,116,144,.07) 1px, transparent 1px); background-size: 28px 28px; mask-image: linear-gradient(90deg, black, transparent 72%); }
        .hero-content { position: relative; z-index: 1; }
        .hero-kicker { display: flex; align-items: center; gap: .55rem; color: #0e7490; font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
        .hero-signal { width: .55rem; height: .55rem; border-radius: 50%; background: #0e7490; animation: signal-pulse 2s infinite; }
        .hero h1 { margin: .35rem 0 .4rem; color: #102a43; font-size: clamp(2rem, 4vw, 3.4rem); line-height: 1.05; letter-spacing: -.03em; }
        .hero p { max-width: 680px; margin: 0; color: #486581; font-size: 1.02rem; }
        @media (max-width: 700px) {
            .block-container { padding: 1rem .75rem 2rem; }
            .hero { padding: 1.2rem; border-radius: 16px; }
            [role="tab"] { min-width: 0; min-height: 44px; padding: .55rem .35rem; white-space: normal; }
            [role="tab"] img { width: 1rem; height: 1rem; flex-shrink: 0; }
            .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button { min-height: 44px; padding: .55rem .65rem; line-height: 1.2; white-space: normal; }
            .stButton > button img, .stButton > button svg, .stDownloadButton > button img, .stDownloadButton > button svg { flex-shrink: 0; }
            [data-testid="stFileUploaderDropzone"] button { min-height: 44px; }
            [data-testid="stHeader"] button { min-width: 44px; min-height: 44px; }
            [data-testid="stTextArea"] textarea { font-size: 16px; }
            [data-testid="stFileUploader"] { width: 100%; }
        }
        </style>
        <section class="hero" aria-label="AI Bug Finder">
            <div class="hero-content">
                <div class="hero-kicker"><span class="hero-signal"></span> Local code intelligence</div>
                <h1>AI Bug Finder</h1>
                <p>Find defects, understand their impact, and review fixes before they reach your codebase.</p>
            </div>
        </section>
        """
)

DEFAULT_CODE = '''def greet(name):
    return "Hello, " + name

print(greet(user_name))
'''


with st.sidebar:
    st.header("Your workspace", icon=":material/account_circle:")
    if st.session_state.get("role"):
        st.success(f"Logged in as {st.session_state['role']}", icon=":material/check_circle:")
    if auth_enabled:
        st.caption(account_email)
    else:
        account_email = st.text_input("Profile name", value="Developer", max_chars=40) or "Developer"
    st.caption("Analysis history is kept separate for each account.")
    st.divider()
    st.header("Reference", icon=":material/menu_book:")
    error_catalog = BugDatabase().load()
    error_names = [f"{item['category']} - {item['title']}" for item in error_catalog]
    selected_error = st.selectbox("Browse an error pattern", error_names)
    error_info = error_catalog[error_names.index(selected_error)]
    with st.container(border=True):
        st.write(error_info["description"])
        st.caption(f"Example: `{error_info['example']}`")
        st.info(error_info["solution"], icon=":material/lightbulb:")
    st.caption("Code analysis runs locally in this application.")

analysis_tab, history_tab = st.tabs([
    ":material/analytics: Analyze code",
    ":material/history: History",
])

offline_mode = os.getenv("BUGFINDER_OFFLINE", "false").lower() == "true"
ai_api_key = None if offline_mode else os.getenv("OPENAI_API_KEY")
if not offline_mode and not ai_api_key:
    try:
        ai_api_key = st.secrets.get("OPENAI_API_KEY")
    except FileNotFoundError:
        ai_api_key = None

with analysis_tab:
    st.header("Analyze Python code", icon=":material/analytics:")
    st.caption("Paste Python code, upload a file, or select a project folder to inspect and analyze its Python files.")

    uploaded_files = st.file_uploader(
        "Upload a Python file or folder",
        type=["py"],
        accept_multiple_files="directory",
        key="analysis_upload",
    )

    selected_upload = None
    if uploaded_files:
        if len(uploaded_files) > 1:
            selected_upload_name = st.selectbox(
                "File shown in the editor",
                [uploaded_file.name for uploaded_file in uploaded_files],
                key="selected_upload_file",
            )
            selected_upload = next(
                uploaded_file for uploaded_file in uploaded_files
                if uploaded_file.name == selected_upload_name
            )
        else:
            selected_upload = uploaded_files[0]
        initial_source = selected_upload.getvalue().decode("utf-8", errors="replace")
        editor_fingerprint = hashlib.sha256(
            selected_upload.name.encode("utf-8") + b"\0" + selected_upload.getvalue()
        ).hexdigest()[:16]
        editor_key = f"pasted_python_code_{editor_fingerprint}"
        st.caption(f"Showing {selected_upload.name}. Edit this code before analyzing if needed.")
    else:
        initial_source = DEFAULT_CODE
        editor_key = "pasted_python_code_manual"

    st.subheader("Paste Python code here", divider="gray")
    st.caption("Uploaded code appears here. Analyze code uses the text currently shown in this editor.")

    with st.container(border=True):
        with st.form("analysis_form"):
            source = st.text_area("Python code", value=initial_source, height=340, key=editor_key)
            control_col, action_col = st.columns([2, 1], vertical_alignment="center")
            run_code = control_col.checkbox("Run a runtime smoke test", value=False)
            request_ai_review = control_col.checkbox(
                "Request a full-code AI review",
                value=False,
                disabled=offline_mode or not ai_api_key or bool(uploaded_files),
            )
            if offline_mode:
                control_col.caption("Offline mode is enabled; all analysis stays local.")
            elif ai_api_key and not uploaded_files:
                control_col.caption("When enabled, pasted code is sent to your configured AI provider for review.")
            elif not ai_api_key:
                control_col.caption("For broader AI fixes, configure OPENAI_API_KEY in the environment or Streamlit secrets.")
            else:
                control_col.caption("Full-code AI review is available for pasted code; uploaded projects use local analysis.")
            control_col.caption("Runtime checks are disabled by default and skipped for security findings.")
            analyze = action_col.form_submit_button("Analyze code", type="primary", width="stretch", icon=":material/search:")

    if analyze:
        if uploaded_files:
            with st.spinner("Analyzing uploaded Python files..."):
                with tempfile.TemporaryDirectory(prefix="bugfinder-project-") as temp_dir:
                    extraction_dir = Path(temp_dir)
                    project_sources = []
                    for uploaded_file in uploaded_files:
                        relative_path = Path(uploaded_file.name.replace("\\", "/"))
                        if relative_path.is_absolute() or ".." in relative_path.parts:
                            st.error("The uploaded folder contains an invalid file path.")
                            st.stop()
                        target = extraction_dir / relative_path
                        target.parent.mkdir(parents=True, exist_ok=True)
                        file_content = (
                            source.encode("utf-8")
                            if uploaded_file.name == selected_upload.name
                            else uploaded_file.getvalue()
                        )
                        target.write_bytes(file_content)
                        project_sources.append(
                            f"# File: {uploaded_file.name}\n"
                            f"{file_content.decode('utf-8', errors='replace')}"
                        )
                    project_result = analyze_project_folder(extraction_dir, run_code=run_code)
                    corrected_zip = create_fixed_project_zip(extraction_dir, zip_name="uploaded_project")
                    history_result = {
                        "issues": project_result["issues"],
                        "summary": project_result["summary"],
                        "fixed_code": None,
                    }
                    history_store.add(
                        account_email,
                        "uploaded_project",
                        "\n\n".join(project_sources),
                        history_result,
                    )
                    st.session_state["analysis_result"] = {
                        "issues": project_result["issues"],
                        "summary": project_result["summary"],
                        "fixed_code": None,
                        "project_zip": corrected_zip,
                        "project_name": "uploaded_project",
                    }
                    st.session_state["analysis_source"] = source or ""
                    st.session_state["analysis_mode"] = "project"
                    st.session_state["analysis_project_files"] = project_result["fixed_files"]
        else:
            with st.spinner("Running analyzers..."):
                result = detect_bugs(source, run_code=run_code)
            if request_ai_review:
                with st.spinner("Reviewing the full pasted code with AI..."):
                    result = analyze_with_ai(
                        source,
                        "pasted-code.py",
                        "Review this Python code for bugs. Explain each error, suggest a specific fix, and return complete corrected code when confident.",
                        result,
                        api_key=ai_api_key,
                    )
            st.session_state["analysis_result"] = result
            st.session_state["analysis_source"] = source
            st.session_state["analysis_mode"] = "file"
            history_store.add(account_email, "pasted-code", source, result)
            st.toast("Analysis and suggestions saved to your account history.", icon=":material/check_circle:")

    result = st.session_state.get("analysis_result")
    analyzed_source = st.session_state.get("analysis_source", source)
    if result:
        summary = result["summary"]
        st.subheader("Analysis summary")
        if result.get("explanation"):
            st.info(result["explanation"], icon=":material/psychology:")
        metric_cols = st.columns(3)
        metric_cols[0].metric("Findings", summary["total"])
        metric_cols[1].metric("Errors", summary["errors"])
        metric_cols[2].metric("Warnings", summary["warnings"])
        if st.session_state.get("analysis_mode") == "project":
            fixed_files = st.session_state.get("analysis_project_files", [])
            if fixed_files:
                st.success(f"Corrected {len(fixed_files)} Python file(s) in the uploaded project.", icon=":material/check_circle:")
                st.code("\n".join(fixed_files), language="text")
            with st.expander("Project files updated", icon=":material/folder_open:"):
                st.code("\n".join(fixed_files) if fixed_files else "No files required changes.", language="text")
            if result.get("project_zip"):
                st.download_button(
                    "Download corrected project (.zip)",
                    result["project_zip"],
                    f"{result['project_name']}-fixed.zip",
                    "application/zip",
                    icon=":material/download:",
                    width="stretch",
                )
        elif not result["issues"]:
            st.success("No issues detected.", icon=":material/check_circle:")
        for issue in result["issues"]:
            icon = ":material/error:" if issue.get("severity") == "error" else ":material/warning:"
            issue_title = issue.get("title", "Code issue")
            line_number = issue.get("line")
            line_label = f"Line {line_number}" if isinstance(line_number, int) and not isinstance(line_number, bool) and line_number > 0 else "Line unavailable"
            label = f"{icon}  {issue.get('file', 'file')}: {line_label}: {issue_title}" if st.session_state.get("analysis_mode") == "project" else f"{icon}  {line_label}: {issue_title}"
            with st.expander(label):
                if issue.get("message"):
                    st.write(issue["message"])
                suggestion = issue.get("solution") or issue.get("suggestion")
                if suggestion:
                    st.info(f"Suggested fix: {suggestion}", icon=":material/build:")
                elif not result.get("explanation"):
                    st.caption("Review the corrected-code preview below before applying a change.")
                if issue.get("code_solution"):
                    st.code(issue["code_solution"], language="python")
        if not st.session_state.get("analysis_mode") == "project" and result.get("fixed_code"):
            with st.expander("Preview conservative fix", icon=":material/auto_fix:"):
                st.caption("Review this complete correction before using it; AI and local suggestions are not applied automatically.")
                st.code(result["fixed_code"], language="python")
                st.download_button("Download corrected code", result["fixed_code"], "corrected_code.py", "text/x-python", width="stretch", icon=":material/download:")
        if st.session_state.get("analysis_mode") != "project":
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                st.download_button("JSON report", create_json_report(analyzed_source, result), "bug-report.json", "application/json", icon=":material/data_object:")
                st.download_button("Markdown report", report_as_markdown(analyzed_source, result), "bug-report.md", "text/markdown", icon=":material/article:")
                st.download_button("PDF report", create_pdf_report(analyzed_source, result), "bug-report.pdf", "application/pdf", icon=":material/picture_as_pdf:")

with history_tab:
    st.header("Your analysis history", icon=":material/history:")
    st.caption("Only analyses saved under your signed-in email are shown here.")
    history_records = list(reversed(history_store.list_for_user(account_email)))
    if not history_records:
        st.info("No saved analyses yet. Run an analysis to create your first history item.", icon=":material/inbox:")
    else:
        if st.button("Delete my history", icon=":material/delete:"):
            history_store.delete_for_user(account_email)
            st.success("Your local analysis history was deleted.", icon=":material/check_circle:")
            st.rerun()
        history_labels = [
            f"{record['filename']} · {record['created_at'].replace('T', ' ')[:16]} · {record['result']['summary']['total']} finding(s)"
            for record in history_records
        ]
        selected_history = st.selectbox("Select a saved analysis", history_labels)
        history_record = history_records[history_labels.index(selected_history)]
        history_result = history_record["result"]
        history_source = history_record["source"]
        history_summary = history_result["summary"]
        metric_cols = st.columns(3)
        metric_cols[0].metric("Findings", history_summary["total"])
        metric_cols[1].metric("Errors", history_summary["errors"])
        metric_cols[2].metric("Warnings", history_summary["warnings"])
        with st.expander("View saved source", icon=":material/code:"):
            st.code(history_source, language="python")
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            st.download_button(
                "JSON report",
                create_json_report(history_source, history_result),
                f"{Path(history_record['filename']).stem}-bug-report.json",
                "application/json",
                key=f"history-json-{history_record['id']}",
                icon=":material/data_object:",
            )
            st.download_button(
                "Markdown report",
                report_as_markdown(history_source, history_result),
                f"{Path(history_record['filename']).stem}-bug-report.md",
                "text/markdown",
                key=f"history-md-{history_record['id']}",
                icon=":material/article:",
            )
            st.download_button(
                "PDF report",
                create_pdf_report(history_source, history_result),
                f"{Path(history_record['filename']).stem}-bug-report.pdf",
                "application/pdf",
                key=f"history-pdf-{history_record['id']}",
                icon=":material/picture_as_pdf:",
            )
