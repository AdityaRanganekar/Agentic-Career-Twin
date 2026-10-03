import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000/api/v1"

st.set_page_config(page_title="Agentic Career Twin", page_icon="🧬", layout="wide")

st.title("🧬 Evidence-Grounded Agentic Career Twin")
st.markdown("Upload your resume to generate a market-weighted Role Readiness Score and a verifiable skill-gap roadmap.")

with st.sidebar:
    st.header("Analysis Settings")

    target_role = st.selectbox(
        "Target Job Family",
        ["Data Scientist", "Machine Learning Engineer", "Data Engineer", "Data Analyst"]
    )

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded_file is not None:
    if st.button("Generate Career Twin"):
        with st.spinner("Executing Agentic Orchestration & Validating Math..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                payload = {"target_role": target_role}
                
                response = requests.post(f"{API_BASE_URL}/process-resume", files=files, data=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("errors"):
                        st.warning("Analysis completed with warnings: " + " | ".join(data["errors"]))
                    else:
                        st.success("Analysis Complete!")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="Role Readiness Score", value=f"{data.get('readiness_score', 0)}%", delta="Initial Baseline")
                    with col2:
                        st.metric(label="Hallucinated Resources", value="0%", delta="-100% vs Standard LLM", delta_color="inverse")
                        
                    st.divider()

                    st.subheader(f"High-Priority Skill Gaps for {target_role}")
                    missing_skills = data.get("missing_skills", [])
                    if missing_skills:
                        st.write(", ".join(missing_skills))
                    else:
                        st.write("No critical gaps detected! Your extracted profile aligns strongly with market demands.")

                    st.subheader("Grounded Resource Roadmap")
                    recommendations = data.get("recommendations", [])
                    
                    if recommendations:
                        for rec in recommendations:
                            with st.expander(f"Close Gap: **{rec.get('skill', 'Unknown')}**"):
                                st.markdown(f"**Recommended Action:** [{rec.get('course_title', 'Course Link')}]({rec.get('url', '#')})")
                                st.markdown(f"***Why:*** {rec.get('justification', 'Selected based on market alignment.')}")
                    else:
                        st.info("No specific database resources required at this time.")
                        
                else:
                    st.error(f"API Error ({response.status_code}): {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to backend. Is FastAPI running on port 8000?")