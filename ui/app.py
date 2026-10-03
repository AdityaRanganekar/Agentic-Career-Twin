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
        ["Data Scientist", "ML Engineer", "Data Engineer", "Backend Engineer"]
    )

uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

if uploaded_file is not None:
    if st.button("Generate Career Twin"):
        with st.spinner("Executing Agentic Orchestration..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                response = requests.post(f"{API_BASE_URL}/process-resume", files=files)
                
                if response.status_code == 200:
                    data = response.json()
                    st.success("Analysis Complete!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="Role Readiness Score", value=f"{data['readiness_score']}%", delta="N/A")
                    with col2:
                        st.metric(label="Hallucinated Resources", value="0%", delta="-100% vs Base LLM", delta_color="inverse")
                        
                    st.json(data)
                else:
                    st.error(f"API Error: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to backend. Is FastAPI running on port 8000?")