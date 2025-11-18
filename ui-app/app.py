import streamlit as st
import requests
import pandas as pd
import time
import os
import json

# --- Configuration ---
# We will pass the API URL in via Environment Variable
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# --- UI Layout ---
st.set_page_config(page_title="PromptFlow", page_icon="🧬", layout="wide")

st.title("PromptFlow: Evolutionary (Maybe) Prompt Optimizer")
st.markdown("Define a task, and let the AI evolve the perfect prompt for you.")

# --- Sidebar: Job Configuration ---
with st.sidebar:
    st.header("⚙️Configuration")
    base_prompt = st.text_area("Base Prompt Template", value="What is the capital of {input}?", height=100)
    eval_metric = st.text_input("Evaluation Metric (Expected Answer)", value="Paris")
    
    st.subheader("Test Data")
    test_data_input = st.text_area(
        "Enter test inputs (one per line)", 
        value="France\nSpain\nGermany",
        height=150
    )

    submit_btn = st.button("Launch Optimization Job", type="primary")

# --- Main Logic ---
if submit_btn:
    # 1. Parse the test data input
    # Split by newlines and remove empty lines
    inputs = [line.strip() for line in test_data_input.split('\n') if line.strip()]
    test_dataset = [{"input": i} for i in inputs]
    
    if not inputs:
        st.error("Please enter at least one test input.")
        st.stop()

    # 2. Construct the Payload
    payload = {
        "base_prompt": base_prompt,
        "evaluation_metric": eval_metric,
        "test_data": test_dataset
    }

    # 3. Send to API
    st.info("Submitting job to Orchestrator...")
    
    try:
        response = requests.post(f"{API_URL}/jobs", json=payload)
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data.get("job_id")
        
        st.success(f"Job Started! ID: {job_id}")
        
    except Exception as e:
        st.error(f"Failed to connect to API: {e}")
        st.stop()

    # 4. Polling Loop
    # We create a placeholder to update the status live
    status_container = st.empty()
    result_container = st.empty()
    
    with st.status("Optimizing...", expanded=True) as status_box:
        while True:
            try:
                # Check status
                status_res = requests.get(f"{API_URL}/jobs/{job_id}")
                status_res.raise_for_status()
                status_data = status_res.json()
                current_status = status_data.get("status")
                
                status_box.write(f"Current Status: **{current_status}**")
                
                if current_status == "COMPLETE":
                    status_box.update(label="Optimization Complete!", state="complete", expanded=False)
                    break
                elif current_status == "FAILED":
                    st.error("Job Failed inside Workflow.")
                    break
                
                # Wait before polling again
                time.sleep(2)
                
            except Exception as e:
                st.error(f"Error checking status: {e}")
                break

    # 5. Display Results
    if current_status == "COMPLETE":
        st.divider()
        st.header("Optimization Results")
        
        results = status_data.get("results", [])
        if results:
            # Convert to DataFrame for a nice table
            df = pd.DataFrame(results)
            
            # Reorder columns if they exist
            cols = ["score", "prompt", "output"]
            # Only keep columns that actually exist in the data
            cols = [c for c in cols if c in df.columns] 
            # Add remaining columns
            cols += [c for c in df.columns if c not in cols]
            
            df = df[cols]
            
            # Show the best prompt prominently
            best_row = df.iloc[df['score'].idxmax()]
            st.info(f"**Best Performing Prompt:**\n\n `{best_row['prompt']}`\n\n Score: {best_row['score']}")

            # Show full table
            st.dataframe(df, use_container_width=True)
            
            # JSON download button
            st.download_button(
                label="Download Results JSON",
                data=json.dumps(status_data, indent=2),
                file_name=f"results_{job_id}.json",
                mime="application/json"
            )
        else:
            st.warning("Job completed but returned no results.")
