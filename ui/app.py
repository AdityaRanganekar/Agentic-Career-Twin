import hashlib
import requests
import streamlit as st
import plotly.graph_objects as go

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Agentic Career Twin", page_icon="🧬", layout="wide")

st.title("🧬 Evidence-Grounded Agentic Career Twin")
st.markdown("Upload your resume to generate a market-weighted Role Readiness Score, custom Job Description alignment, and a verifiable skill-gap roadmap.")

# Initialize session state cache for PDF analysis
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}

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
    "Quantitative Researcher",
    "🔍 Custom Role (Search Any Role)"
]

with st.sidebar:
    st.header("Analysis Settings")

    selected_role = st.selectbox(
        "Target Job Family",
        POPULAR_ROLES
    )

    custom_role = st.text_input(
        "Or Enter Any Custom Target Role:",
        placeholder="e.g., Computer Vision Engineer, Agentic AI Engineer..."
    )

    if custom_role and custom_role.strip():
        target_role = custom_role.strip()
    elif selected_role != "🔍 Custom Role (Search Any Role)":
        target_role = selected_role
    else:
        target_role = "Data Scientist"

    st.caption(f"Active Analysis Target: **{target_role}**")
    
    force_refresh = st.checkbox(
        "🔄 Force Live Internet Refresh (Bypass 1-Yr DB Cache)", 
        value=False,
        help="When checked, forces the Web Role Discovery Agent to scrape live job listings and bypass PostgreSQL TTL."
    )

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

# Upgraded Job Description Input: PDF, DOCX, or Text Area
with st.expander("🎯 Target a Specific Job Description (Optional Dual-Scoring)", expanded=False):
    st.markdown("Upload a target job posting file **or** paste the description text below:")
    jd_uploaded_file = st.file_uploader("Upload Job Description File (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
    target_jd_text = st.text_area(
        "Or paste Job Description text here:",
        height=140,
        placeholder="e.g. Machine Learning Engineer at Acme Corp...\nRequirements: PyTorch, Docker, Kubernetes, AWS, MLOps, CI/CD..."
    )

def render_competency_radar(radar_dimensions: dict = None, jd_radar_dimensions: dict = None, readiness_score: float = 0.0):
    """Renders a true radar chart plotting actual computed dimension scores across 5 competency axes."""
    categories = [
        'Core Programming', 
        'ML / Deep Learning', 
        'Cloud Infrastructure', 
        'Data Engineering', 
        'Databases & Storage'
    ]

    # Baseline market expects high competency across critical dimensions
    market_benchmark = [90, 85, 80, 85, 85]
    
    # Use real computed dimensions from backend
    if radar_dimensions:
        candidate_profile = [float(radar_dimensions.get(cat, 0.0)) for cat in categories]
    else:
        factor = min(readiness_score / 100.0, 1.0)
        candidate_profile = [min(round(val * factor, 1), 100) for val in [80, 80, 70, 75, 75]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=market_benchmark,
        theta=categories,
        fill='toself',
        name='Market Benchmark (100%)',
        line=dict(color='#A0AEC0', dash='dash')
    ))

    fig.add_trace(go.Scatterpolar(
        r=candidate_profile,
        theta=categories,
        fill='toself',
        name='Candidate Competency',
        line=dict(color='#3182CE')
    ))

    # Dual-Scoring Target JD Fit Trace
    if jd_radar_dimensions:
        jd_profile = [float(jd_radar_dimensions.get(cat, 0.0)) for cat in categories]
        fig.add_trace(go.Scatterpolar(
            r=jd_profile,
            theta=categories,
            fill='toself',
            name='Target JD Fit',
            line=dict(color='#38A169')
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                ticksuffix="%"
            )
        ),
        showlegend=True,
        title="🧬 Candidate Skill Coverage Radar",
        margin=dict(l=40, r=40, t=40, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

if uploaded_file is not None:
    pdf_bytes = uploaded_file.getvalue()
    pdf_hash = hashlib.md5(pdf_bytes).hexdigest()
    profile_cache_key = f"profile_{pdf_hash}"

    if st.button("Generate Career Twin"):
        with st.spinner("Executing Agentic Orchestration & Validating Math..."):
            try:
                payload = {
                    "target_role": target_role,
                    "target_jd_text": target_jd_text.strip() if target_jd_text else "",
                    "force_live_refresh": "true" if force_refresh else "false"
                }

                cached_profile_str = st.session_state.get(profile_cache_key)
                files = {}

                if cached_profile_str:
                    payload["cached_profile_json"] = cached_profile_str
                    st.caption("⚡ Using cached PDF extraction profile for fast scoring.")
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
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")
                    st.stop()
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to backend. Is FastAPI running on port 8000?")
                st.stop()

        if data:
            if data.get("errors"):
                st.warning("Analysis completed with warnings: " + " | ".join(data["errors"]))
            else:
                st.success("Analysis Complete!")

            jd_score = data.get("jd_fit_score")
            corpus_version = data.get("market_corpus_version", "PostgreSQL Cache")

            # Metrics display: Dual vs Single
            if jd_score is not None:
                col1, col2, col3 = st.columns(3)
                with col1:
                    score = data.get("readiness_score", 0.0)
                    delta = data.get("score_delta")
                    delta_str = f"{delta:+.2f}%" if delta is not None else "Initial Baseline"
                    st.metric(label="Broad Market Readiness", value=f"{score}%", delta=delta_str)
                with col2:
                    st.metric(label="Target JD Fit Score", value=f"{jd_score}%", delta="Custom Job Posting")
                with col3:
                    st.metric(label="Role Intelligence Source", value=corpus_version.split("(")[0].strip()[:24], delta=corpus_version)
            else:
                col1, col2 = st.columns(2)
                with col1:
                    score = data.get("readiness_score", 0.0)
                    delta = data.get("score_delta")
                    delta_str = f"{delta:+.2f}%" if delta is not None else "Initial Baseline"
                    st.metric(label="Role Readiness Score", value=f"{score}%", delta=delta_str)
                with col2:
                    st.metric(label="Role Intelligence Source", value=corpus_version.split("(")[0].strip()[:24], delta=corpus_version)

            if data.get("student_name") and data.get("student_name") != "Anonymous Student":
                st.caption(f"Profile: **{data.get('student_name')}** ({data.get('student_email')})")
                
            st.divider()

            # Radar Chart Visualization
            render_competency_radar(
                radar_dimensions=data.get("radar_dimensions"),
                jd_radar_dimensions=data.get("jd_radar_dimensions"),
                readiness_score=data.get("readiness_score", 0.0)
            )

            st.divider()

            # Side-by-Side Skill Gaps (Market vs JD)
            if jd_score is not None:
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.subheader(f"🌐 Industry Market Gaps ({target_role})")
                    market_gaps = data.get("missing_skills", [])
                    if market_gaps:
                        for g in market_gaps:
                            st.markdown(f"- 🔴 **{g}**")
                    else:
                        st.write("No critical industry gaps detected!")
                with col_g2:
                    st.subheader("🎯 Specific Target JD Gaps")
                    jd_gaps = data.get("jd_missing_skills", [])
                    if jd_gaps:
                        for g in jd_gaps:
                            st.markdown(f"- 🟠 **{g}**")
                    else:
                        st.write("Full match on extracted job requirements!")
            else:
                st.subheader(f"High-Priority Skill Gaps for {target_role}")
                missing_skills = data.get("missing_skills", [])
                if missing_skills:
                    for g in missing_skills:
                        st.markdown(f"- 🔴 **{g}**")
                else:
                    st.write("No critical gaps detected! Your extracted profile aligns strongly with market demands.")

            st.divider()

            st.subheader("Grounded Resource Roadmap")
            recommendations = data.get("recommendations", [])
            
            if recommendations:
                for rec in recommendations:
                    with st.expander(f"Close Gap: **{rec.get('skill', 'Unknown')}**"):
                        st.markdown(f"**Recommended Action:** [{rec.get('course_title', 'Course Link')}]({rec.get('url', '#')})")
                        st.markdown(f"***Why:*** {rec.get('justification', 'Selected based on market alignment.')}")
            else:
                st.info("No specific database resources required at this time.")
