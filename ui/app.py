import os
import hashlib
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="Agentic Career Twin",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# Refined Modern CSS Design System (Strict Zero-Emoji Policy)
# -------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #E2E8F0;
}

.stTabs [data-baseweb="tab"] {
    font-size: 0.95rem;
    font-weight: 600;
    padding: 10px 18px;
    border-radius: 8px 8px 0 0;
    color: #475569;
}

.stTabs [aria-selected="true"] {
    color: #0F172A !important;
    border-bottom: 2px solid #2563EB !important;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1.1rem 1.25rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.metric-label {
    font-size: 0.8rem;
    font-weight: 600;
    color: #64748B;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 0.35rem;
}

.metric-value {
    font-size: 1.85rem;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.15;
}

.metric-caption {
    font-size: 0.8rem;
    color: #64748B;
    margin-top: 0.4rem;
    line-height: 1.35;
}

.metric-delta-pos {
    color: #16A34A;
    font-weight: 600;
    font-size: 0.85rem;
}

.metric-delta-neu {
    color: #64748B;
    font-weight: 500;
    font-size: 0.85rem;
}

.study-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1.25rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.study-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}

.gap-badge-market {
    display: inline-block;
    background-color: #FEF2F2;
    color: #991B1B;
    border: 1px solid #FECACA;
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0.2rem 0.3rem 0.2rem 0;
}

.gap-badge-jd {
    display: inline-block;
    background-color: #FFFBEB;
    color: #92400E;
    border: 1px solid #FDE68A;
    border-radius: 6px;
    padding: 0.2rem 0.55rem;
    font-size: 0.8rem;
    font-weight: 600;
    margin: 0.2rem 0.3rem 0.2rem 0;
}

.platform-btn-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 0.85rem;
}

.platform-btn {
    display: inline-flex;
    align-items: center;
    padding: 0.45rem 0.85rem;
    font-size: 0.82rem;
    font-weight: 600;
    border-radius: 6px;
    text-decoration: none !important;
    color: #FFFFFF !important;
    transition: transform 0.15s ease, opacity 0.15s ease;
}
.platform-btn:hover {
    transform: translateY(-2px);
    opacity: 0.92;
}

.btn-udemy { background-color: #6D28D9; }
.btn-coursera { background-color: #0056D2; }
.btn-edx { background-color: #02262B; }
.btn-youtube { background-color: #DC2626; }
.btn-docs { background-color: #334155; }

.auth-header {
    text-align: center;
    margin-bottom: 1.5rem;
}
.auth-title {
    font-size: 1.6rem;
    font-weight: 700;
    color: #0F172A;
}
.auth-subtitle {
    font-size: 0.9rem;
    color: #64748B;
    margin-top: 0.35rem;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# Session State Initialization
# -------------------------------------------------------------
if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}

if "latest_results" not in st.session_state:
    st.session_state["latest_results"] = None

POPULAR_ROLES = [
    "Data Scientist",
    "Machine Learning Engineer",
    "AI / LLM Engineer",
    "Data Engineer",
    "Data Analyst",
    "MLOps Engineer",
    "Backend Software Engineer",
    "Full-Stack Developer",
    "Cloud / DevOps Engineer",
    "Site Reliability Engineer",
    "Quantitative Researcher",
    "Custom Role (Search Any Discipline)"
]

# -------------------------------------------------------------
# Authentication Portal (Gate if not logged in)
# -------------------------------------------------------------
if st.session_state["auth_user"] is None:
    st.markdown("""
        <div class="auth-header">
            <div class="auth-title">Evidence-Grounded Career Twin</div>
            <div class="auth-subtitle">Sign in or create an account to access career assessments, historical progress, and study guides.</div>
        </div>
    """, unsafe_allow_html=True)

    auth_col1, auth_col2, auth_col3 = st.columns([1, 2, 1])
    with auth_col2:
        auth_tab_login, auth_tab_signup, auth_tab_google = st.tabs(["Sign In", "Create Account", "Google Account"])

        with auth_tab_login:
            st.markdown("##### Account Login")
            with st.form("login_form"):
                login_id = st.text_input("Username or Email", placeholder="e.g. aditya or aditya@example.com")
                login_pwd = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted_login = st.form_submit_button("Sign In", use_container_width=True)

                if submitted_login:
                    if not login_id or not login_pwd:
                        st.error("Please enter both username/email and password.")
                    else:
                        try:
                            resp = requests.post(
                                f"{API_BASE_URL}/auth/login",
                                json={"identifier": login_id.strip(), "password": login_pwd}
                            )
                            if resp.status_code == 200:
                                st.session_state["auth_user"] = resp.json()
                                st.success("Signed in successfully.")
                                st.rerun()
                            else:
                                err_detail = resp.json().get("detail", "Invalid credentials.")
                                st.error(err_detail)
                        except Exception as e:
                            st.error(f"Authentication service connection error: {e}")

        with auth_tab_signup:
            st.markdown("##### Register New Profile")
            with st.form("signup_form"):
                new_name = st.text_input("Full Name", placeholder="e.g. Aditya Ranganekar")
                new_username = st.text_input("Username", placeholder="e.g. aditya")
                new_email = st.text_input("Email Address", placeholder="e.g. aditya@example.com")
                new_pwd = st.text_input("Password", type="password", placeholder="Minimum 6 characters")
                submitted_signup = st.form_submit_button("Create Account", use_container_width=True)

                if submitted_signup:
                    if not new_email or not new_pwd or not new_username:
                        st.error("Please fill in all required fields.")
                    else:
                        try:
                            resp = requests.post(
                                f"{API_BASE_URL}/auth/signup",
                                json={
                                    "name": new_name.strip() or new_username.strip(),
                                    "username": new_username.strip(),
                                    "email": new_email.strip(),
                                    "password": new_pwd
                                }
                            )
                            if resp.status_code == 200:
                                st.session_state["auth_user"] = resp.json()
                                st.success("Account created successfully.")
                                st.rerun()
                            else:
                                err_detail = resp.json().get("detail", "Registration failed.")
                                st.error(err_detail)
                        except Exception as e:
                            st.error(f"Registration service connection error: {e}")

        with auth_tab_google:
            st.markdown("##### Continue with Google")
            try:
                url_resp = requests.get(f"{API_BASE_URL}/auth/google-url", timeout=3)
                oauth_cfg = url_resp.json() if url_resp.status_code == 200 else {"configured": False}
            except Exception:
                oauth_cfg = {"configured": False}

            if oauth_cfg.get("configured") and oauth_cfg.get("auth_url"):
                st.markdown(
                    f"""<a href="{oauth_cfg['auth_url']}" target="_self" style="display:block; text-align:center; padding:10px 16px; background:#FFFFFF; border:1px solid #CBD5E1; border-radius:8px; font-weight:600; color:#0F172A; text-decoration:none;">
                    Sign in with Google OAuth
                    </a>""",
                    unsafe_allow_html=True
                )
            else:
                st.caption("OAuth credentials not configured in environment. Use direct Google Profile sign-in below:")
                with st.form("google_direct_form"):
                    g_email = st.text_input("Google Email", placeholder="user@gmail.com")
                    g_name = st.text_input("Display Name (Optional)", placeholder="User Name")
                    g_submit = st.form_submit_button("Sign In with Google Account", use_container_width=True)

                    if g_submit:
                        if not g_email:
                            st.error("Please provide an email address.")
                        else:
                            try:
                                resp = requests.post(
                                    f"{API_BASE_URL}/auth/google",
                                    json={"email": g_email.strip(), "name": g_name.strip()}
                                )
                                if resp.status_code == 200:
                                    st.session_state["auth_user"] = resp.json()
                                    st.success("Signed in with Google.")
                                    st.rerun()
                                else:
                                    st.error(resp.text)
                            except Exception as e:
                                st.error(f"Google sign-in error: {e}")

    st.stop()

# -------------------------------------------------------------
# Authenticated User Session Active
# -------------------------------------------------------------
user = st.session_state["auth_user"]

with st.sidebar:
    st.markdown(f"**{user.get('name') or user.get('email')}**")
    st.caption(f"Account: {user.get('email')} ({user.get('auth_provider', 'local').title()})")
    if st.button("Sign Out", use_container_width=True):
        st.session_state["auth_user"] = None
        st.session_state["latest_results"] = None
        st.rerun()

    st.divider()
    st.header("Assessment Configuration")

    selected_role = st.selectbox("Target Career Family", POPULAR_ROLES)
    custom_role = st.text_input("Or Enter Any Target Role:", placeholder="e.g. Agentic AI Engineer, Frontend Engineer...")

    if custom_role and custom_role.strip():
        target_role = custom_role.strip()
    elif selected_role != "Custom Role (Search Any Discipline)":
        target_role = selected_role
    else:
        target_role = "Data Scientist"

    st.caption(f"Target Role: **{target_role}**")
    force_refresh = st.checkbox("Force Live Market Refresh", value=False, help="Bypasses database TTL to fetch new market listings.")

# -------------------------------------------------------------
# Main Application Header
# -------------------------------------------------------------
st.title("Evidence-Grounded Career Twin")
st.markdown("Evaluate real candidate readiness against dynamic industry standards, inspect verifiable engineering depth, and follow a structured multi-platform study guide.")

# Document Upload Section
upload_col1, upload_col2 = st.columns([1, 1])
with upload_col1:
    uploaded_file = st.file_uploader("Candidate Resume (PDF)", type=["pdf"])

with upload_col2:
    with st.expander("Target Job Description (Optional Dual-Scoring)", expanded=False):
        jd_uploaded_file = st.file_uploader("Job Posting Document (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])
        target_jd_text = st.text_area("Or Paste Job Description Text:", height=100, placeholder="Requirements, responsibilities, or technical specifications...")

# Execute Analysis Button
if uploaded_file is not None:
    pdf_bytes = uploaded_file.getvalue()
    pdf_hash = hashlib.md5(pdf_bytes).hexdigest()
    profile_cache_key = f"profile_{pdf_hash}"

    if st.button("Run Career Assessment", type="primary"):
        with st.spinner("Analyzing resume against industry benchmark and target job posting..."):
            try:
                payload = {
                    "target_role": target_role,
                    "target_jd_text": target_jd_text.strip() if target_jd_text else "",
                    "force_live_refresh": "true" if force_refresh else "false",
                    "authenticated_student_id": str(user.get("student_id", "")),
                    "authenticated_email": user.get("email", "")
                }

                cached_profile_str = st.session_state.get(profile_cache_key)
                files = {}

                if cached_profile_str:
                    payload["cached_profile_json"] = cached_profile_str
                else:
                    files["file"] = (uploaded_file.name, pdf_bytes, "application/pdf")

                if jd_uploaded_file is not None:
                    files["jd_file"] = (
                        jd_uploaded_file.name,
                        jd_uploaded_file.getvalue(),
                        jd_uploaded_file.type or "application/octet-stream"
                    )

                response = requests.post(
                    f"{API_BASE_URL}/process-resume",
                    files=files if files else None,
                    data=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("student_profile_json"):
                        st.session_state[profile_cache_key] = data["student_profile_json"]
                    st.session_state["latest_results"] = data
                    st.success("Assessment complete.")
                else:
                    st.error(f"Assessment error ({response.status_code}): {response.text}")
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to backend service. Ensure FastAPI server is running on port 8000.")

# -------------------------------------------------------------
# 3-Tab Workspace Navigation
# -------------------------------------------------------------
tab_overview, tab_roadmap, tab_history = st.tabs([
    "Assessment Overview",
    "Learning Roadmap",
    "Run History & Progress"
])

results = st.session_state.get("latest_results")

# =============================================================
# TAB 1: Assessment Overview
# =============================================================
with tab_overview:
    if results:
        readiness = results.get("readiness_score", 0.0)
        jd_score = results.get("jd_fit_score")
        pqs = results.get("project_quality_score", 0.0)
        delta = results.get("score_delta")
        rqb = results.get("resume_quality_breakdown") or {}
        market_gaps = results.get("missing_skills") or []
        jd_gaps = results.get("jd_missing_skills") or []

        # Top Metric Cards
        cols = st.columns(4 if jd_score is not None else 3)
        with cols[0]:
            delta_str = f"{delta:+.1f}% vs last assessment" if delta is not None else "Initial benchmark"
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Role Readiness Score</div>
                    <div class="metric-value">{readiness:.1f}%</div>
                    <div class="metric-caption">{delta_str}. Measures alignment of verified skills and outcomes against industry requirements.</div>
                </div>
            """, unsafe_allow_html=True)

        if jd_score is not None:
            with cols[1]:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">Job Description Fit</div>
                        <div class="metric-value">{jd_score:.1f}%</div>
                        <div class="metric-caption">Direct alignment against requirements in the uploaded job posting.</div>
                    </div>
                """, unsafe_allow_html=True)

        with cols[2 if jd_score is not None else 1]:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Project & Evidence Rigor</div>
                    <div class="metric-value">{pqs:.1f}%</div>
                    <div class="metric-caption">Evaluates quantitative impact metrics, architecture depth, and verifiable repository proof.</div>
                </div>
            """, unsafe_allow_html=True)

        with cols[3 if jd_score is not None else 2]:
            radar_dict = results.get("radar_dimensions") or {}
            cats = list(radar_dict.keys())
            matched_cats = sum(1 for v in radar_dict.values() if float(v) >= 70.0)
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Core Competencies Verified</div>
                    <div class="metric-value">{matched_cats} / {max(len(cats), 1)}</div>
                    <div class="metric-caption">Number of dynamic core competency dimensions meeting or exceeding professional thresholds.</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Radar Chart & Missing Skill Badges
        r_col1, r_col2 = st.columns([1.1, 0.9])
        with r_col1:
            st.markdown("##### Competency Footprint Analysis")
            radar_dims = results.get("radar_dimensions") or {}
            jd_radar_dims = results.get("jd_radar_dimensions")

            if radar_dims:
                categories = list(radar_dims.keys())
                cand_vals = [float(radar_dims.get(c, 0.0)) for c in categories]
                market_vals = [85.0] * len(categories)

                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=market_vals,
                    theta=categories,
                    fill='toself',
                    name=f'Market Standard ({target_role})',
                    line=dict(color='#94A3B8', dash='dash'),
                    fillcolor='rgba(148, 163, 184, 0.15)'
                ))
                fig.add_trace(go.Scatterpolar(
                    r=cand_vals,
                    theta=categories,
                    fill='toself',
                    name='Candidate Competency',
                    line=dict(color='#2563EB', width=2),
                    fillcolor='rgba(37, 99, 235, 0.25)'
                ))

                if jd_radar_dims:
                    jd_vals = [float(jd_radar_dims.get(c, 60.0)) for c in categories]
                    fig.add_trace(go.Scatterpolar(
                        r=jd_vals,
                        theta=categories,
                        fill='toself',
                        name='Target Job Posting Demand',
                        line=dict(color='#16A34A', width=2),
                        fillcolor='rgba(22, 163, 74, 0.15)'
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100], ticksuffix="%")),
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
                    margin=dict(l=40, r=40, t=20, b=50),
                    height=380
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Radar dimension analysis unavailable.")

        with r_col2:
            st.markdown("##### Priority Competency Gaps")
            if market_gaps:
                st.markdown("**Industry Benchmark Gaps:**")
                badges_m = "".join([f'<span class="gap-badge-market">{g}</span>' for g in market_gaps])
                st.markdown(badges_m, unsafe_allow_html=True)
            else:
                st.caption("No critical industry benchmark gaps detected.")

            if jd_score is not None:
                st.markdown("<br>**Target Job Posting Gaps:**", unsafe_allow_html=True)
                if jd_gaps:
                    badges_j = "".join([f'<span class="gap-badge-jd">{g}</span>' for g in jd_gaps])
                    st.markdown(badges_j, unsafe_allow_html=True)
                else:
                    st.caption("All requirements from the target job posting are satisfied.")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("##### Resume Evidence & Impact Breakdown")
            c_p1, c_p2, c_p3 = st.columns(3)
            with c_p1:
                st.metric("Quantitative Metrics", f"{rqb.get('quantitative_metrics_score', 0):.1f}%")
            with c_p2:
                st.metric("Production Stack", f"{rqb.get('production_proof_score', 0):.1f}%")
            with c_p3:
                st.metric("Role Alignment", f"{rqb.get('role_alignment_score', 0):.1f}%")

            with st.expander("Evidence Details & Advice", expanded=False):
                det_metrics = rqb.get("detected_metrics", [])
                det_proof = rqb.get("detected_proof_links", [])
                det_stack = rqb.get("detected_production_stack", [])

                st.markdown("**Detected Impact Metrics:** " + (", ".join([f"`{m}`" for m in det_metrics]) if det_metrics else "None detected."))
                st.markdown("**Detected Proof Links:** " + (", ".join([f"`{p}`" for p in det_proof]) if det_proof else "No GitHub/paper links found."))
                st.markdown("**Verified Competencies in Context:** " + (", ".join([f"`{s}`" for s in det_stack]) if det_stack else "None."))

                if rqb.get("quantitative_metrics_score", 0) < 80:
                    st.info("Tip: Add measurable metrics to project bullets (e.g. latency reduced by 35%, 88% precision, 10k daily users).")
                if rqb.get("production_proof_score", 0) < 80:
                    st.info("Tip: Include live URLs, public GitHub repositories, or technical documentation links to strengthen proof-of-work.")
    else:
        st.info("Upload a candidate resume and click 'Run Career Assessment' to view the assessment overview.")

# =============================================================
# TAB 2: Learning Roadmap (Multi-Platform Study Hub)
# =============================================================
with tab_roadmap:
    if results:
        recommendations = results.get("recommendations") or []
        st.markdown(f"#### Structured Study Hub for {target_role}")
        st.markdown("Curated multi-platform search links and targeted sub-topics to close identified skill gaps directly.")

        if recommendations:
            for rec in recommendations:
                skill_name = rec.get("skill", "Core Competency")
                justification = rec.get("justification", "")
                topics = rec.get("key_topics") or []
                links = rec.get("platform_links") or []

                btn_html_items = []
                for lnk in links:
                    p_name = lnk.get("platform", "")
                    p_url = lnk.get("url", "#")
                    css_class = "btn-udemy"
                    if "coursera" in p_name.lower():
                        css_class = "btn-coursera"
                    elif "edx" in p_name.lower():
                        css_class = "btn-edx"
                    elif "youtube" in p_name.lower():
                        css_class = "btn-youtube"
                    elif "doc" in p_name.lower():
                        css_class = "btn-docs"

                    btn_html_items.append(
                        f'<a href="{p_url}" target="_blank" class="platform-btn {css_class}">{p_name}</a>'
                    )

                btn_row_html = "".join(btn_html_items)
                topics_html = "".join([f"<li>{t}</li>" for t in topics])

                st.markdown(f"""
                    <div class="study-card">
                        <div style="font-size:1.15rem; font-weight:700; color:#0F172A; margin-bottom:0.35rem;">
                            {skill_name}
                        </div>
                        <div style="font-size:0.9rem; color:#475569; margin-bottom:0.75rem; line-height:1.45;">
                            {justification}
                        </div>
                        <div style="font-size:0.85rem; font-weight:600; color:#1E293B; margin-bottom:0.25rem;">
                            Key Focus Areas to Master:
                        </div>
                        <ul style="font-size:0.85rem; color:#475569; margin-top:0.2rem; margin-bottom:0.6rem; padding-left:1.2rem;">
                            {topics_html}
                        </ul>
                        <div style="font-size:0.8rem; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.04em;">
                            Explore Targeted Courses & Documentation:
                        </div>
                        <div class="platform-btn-row">
                            {btn_row_html}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No skill gaps detected. Candidate profile satisfies all industry standards.")
    else:
        st.info("Run an assessment from the main screen to generate your structured learning roadmap.")

# =============================================================
# TAB 3: Run History & Progress Tracker
# =============================================================
with tab_history:
    st.markdown("#### Historical Assessment Timeline")
    st.markdown("Track candidate score progression across target roles over time and access saved study guides.")

    student_ident = user.get("student_id") or user.get("email")
    try:
        hist_resp = requests.get(f"{API_BASE_URL}/history/{student_ident}", timeout=5)
        history_runs = hist_resp.json() if hist_resp.status_code == 200 else []
    except Exception as e:
        history_runs = []
        st.error(f"Could not load run history: {e}")

    if history_runs:
        # Progression Chart
        plot_data = []
        for r in history_runs:
            ts_str = r.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                formatted_date = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                formatted_date = ts_str[:16]

            plot_data.append({
                "Date": formatted_date,
                "Role Readiness (%)": float(r.get("readiness_score", 0.0)),
                "JD Fit (%)": float(r.get("jd_fit_score")) if r.get("jd_fit_score") is not None else None,
                "Target Role": r.get("target_role", "Unknown"),
                "Resume": r.get("resume_filename") or "Assessment"
            })

        # Reverse so chronological order left-to-right
        plot_data_sorted = list(reversed(plot_data))

        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=[d["Date"] for d in plot_data_sorted],
            y=[d["Role Readiness (%)"] for d in plot_data_sorted],
            mode='lines+markers',
            name='Role Readiness Score',
            line=dict(color='#2563EB', width=2),
            marker=dict(size=7)
        ))

        jd_points = [d for d in plot_data_sorted if d["JD Fit (%)"] is not None]
        if jd_points:
            fig_hist.add_trace(go.Scatter(
                x=[d["Date"] for d in jd_points],
                y=[d["JD Fit (%)"] for d in jd_points],
                mode='lines+markers',
                name='Job Description Fit',
                line=dict(color='#16A34A', width=2, dash='dot'),
                marker=dict(size=7)
            ))

        fig_hist.update_layout(
            yaxis=dict(range=[0, 105], ticksuffix="%"),
            xaxis=dict(title="Assessment Date"),
            margin=dict(l=40, r=40, t=30, b=40),
            height=320,
            showlegend=True
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.markdown("##### Assessment Archive")
        for idx, run in enumerate(history_runs):
            ts = run.get("timestamp", "")[:19].replace("T", " ")
            r_role = run.get("target_role", "Unknown")
            r_score = run.get("readiness_score", 0.0)
            r_jd = run.get("jd_fit_score")
            r_file = run.get("resume_filename") or "Resume"
            r_gaps = run.get("missing_skills") or []
            r_resources = run.get("recommended_resources") or []

            label = f"{ts} — {r_role} (Readiness: {r_score:.1f}%"
            if r_jd is not None:
                label += f" | JD Fit: {r_jd:.1f}%"
            label += f") [{r_file}]"

            with st.expander(label, expanded=(idx == 0)):
                col_h1, col_h2 = st.columns([1, 1])
                with col_h1:
                    st.markdown(f"**Target Role:** {r_role}")
                    st.markdown(f"**Readiness Score:** {r_score:.1f}%")
                    if r_jd is not None:
                        st.markdown(f"**Target JD Fit:** {r_jd:.1f}%")
                    st.markdown(f"**Assessed File:** `{r_file}`")

                    if r_gaps:
                        st.markdown("**Identified Gaps:**")
                        gap_badges = "".join([f'<span class="gap-badge-market">{g}</span>' for g in r_gaps])
                        st.markdown(gap_badges, unsafe_allow_html=True)

                with col_h2:
                    if r_resources:
                        st.markdown("**Saved Multi-Platform Resources:**")
                        for item in r_resources[:4]:
                            s_name = item.get("skill", "Skill")
                            links = item.get("platform_links") or []
                            btn_htmls = []
                            for lnk in links:
                                p_name = lnk.get("platform", "")
                                p_url = lnk.get("url", "#")
                                css_c = "btn-udemy"
                                if "coursera" in p_name.lower():
                                    css_c = "btn-coursera"
                                elif "youtube" in p_name.lower():
                                    css_c = "btn-youtube"
                                elif "doc" in p_name.lower():
                                    css_c = "btn-docs"
                                btn_htmls.append(f'<a href="{p_url}" target="_blank" class="platform-btn {css_c}" style="padding:0.25rem 0.5rem; font-size:0.75rem;">{p_name}</a>')
                            
                            st.markdown(f"<div style='margin-bottom:0.5rem;'><b>{s_name}:</b> " + " ".join(btn_htmls) + "</div>", unsafe_allow_html=True)
                    else:
                        st.caption("No specific resources archived for this run.")
    else:
        st.info("No prior assessments found for this profile. Run your first assessment above to begin tracking progress.")
