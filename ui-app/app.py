import streamlit as st
import requests
import pandas as pd
import time
import os
import json

# Configuration
# Pass the API URL in via Environment Variable
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# UI Layout
st.set_page_config(page_title="PromptFlow", page_icon="🧬", layout="wide")

st.title("PromptFlow: Evolutionary Prompt Optimizer")
st.markdown("Define a task, and let the AI evolve the perfect prompt for you.")

# Sidebar: Job Configuration
with st.sidebar:
    st.header("Configuration")
    base_prompt = st.text_area("Base Prompt Template", value="Translate to pirate style: {input}", height=100)
    eval_metric = st.text_input("Evaluation Criteria", value="Must sound like an authentic 18th century pirate.")
    
    st.subheader("Test Data")
    test_data_input = st.text_area(
        "Enter test inputs (one per line)", 
        value="I will be back in 10 minutes.\nHello friend.",
        height=150
    )

    submit_btn = st.button("Launch Optimization Job", type="primary")

# Helper to Polling
def poll_job(job_id):
    status_container = st.empty()
    with st.status("Optimizing...", expanded=True) as status_box:
        while True:
            try:
                status_res = requests.get(f"{API_URL}/jobs/{job_id}")
                status_res.raise_for_status()
                status_data = status_res.json()
                current_status = status_data.get("status")
                
                status_box.write(f"Current Status: **{current_status}**")
                
                if current_status == "COMPLETE":
                    status_box.update(label="Optimization Complete!", state="complete", expanded=False)
                    return status_data
                elif current_status == "FAILED" or current_status == "FAILED_TO_START":
                    st.error("Job Failed.")
                    return None
                
                time.sleep(2)
            except Exception as e:
                st.error(f"Error checking status: {e}")
                return None

# Main
if submit_btn:
    inputs = [line.strip() for line in test_data_input.split('\n') if line.strip()]
    test_dataset = [{"input": i} for i in inputs]
    
    payload = {
        "base_prompt": base_prompt,
        "evaluation_metric": eval_metric,
        "test_data": test_dataset
    }

    try:
        response = requests.post(f"{API_URL}/jobs", json=payload)
        response.raise_for_status()
        job_data = response.json()
        st.session_state.current_job_id = job_data.get("job_id")
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")

if 'current_job_id' in st.session_state:
    job_id = st.session_state.current_job_id
    final_data = poll_job(job_id)

    if final_data:
        st.divider()
        st.header("🏆 Optimization Results")
        
        results = final_data.get("results", [])
        if results:
            df = pd.DataFrame(results)
            
            # FORCE COLUMN ORDER FOR VISIBILITY
            # Explicitly want to see these columns
            target_cols = ["score", "prompt", "output", "reasoning"]
            
            # Filter for columns that actually exist in the dataframe
            final_cols = [c for c in target_cols if c in df.columns]
            
            # Add any other columns that might be there
            final_cols += [c for c in df.columns if c not in final_cols]
            
            df = df[final_cols]

            if 'score' in df.columns:
                best_row = df.iloc[df['score'].idxmax()]
                st.info(f"**Best Performing Prompt:**\n\n `{best_row['prompt']}`\n\n Score: {best_row['score']}/1.0")

            st.dataframe(df, use_container_width=True)
            
            # EVOLUTION SECTION
            st.divider()
            st.subheader("Evolve Next Generation")
            with st.form("evolution_form"):
                parents = st.multiselect("Select Parents:", df['prompt'].unique())
                evolve = st.form_submit_button("Spawn Generation 2")
                
            if evolve and parents:
                inputs = [line.strip() for line in test_data_input.split('\n') if line.strip()]
                test_dataset = [{"input": i} for i in inputs]
                new_payload = {
                    "base_prompt": base_prompt,
                    "evaluation_metric": eval_metric,
                    "test_data": test_dataset,
                    "parent_prompts": parents
                }
                res = requests.post(f"{API_URL}/jobs", json=new_payload)
                st.session_state.current_job_id = res.json().get("job_id")
                st.rerun()
