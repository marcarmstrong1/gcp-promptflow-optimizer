import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import firestore
from google.cloud import workflows_v1
from google.cloud.workflows import executions_v1
from google.cloud.workflows.executions_v1.types import Execution

app = FastAPI(title="PromptFlow API", version="1.0.0")

# --- Configuration ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") # Cloud Run sets this automatically
LOCATION = "us-central1"
WORKFLOW_NAME = "promptflow-orchestrator" # We will build this in Step 4

# --- Clients ---
# Initialize these outside the route handlers for efficiency
db = firestore.Client(database="promptflow")
execution_client = executions_v1.ExecutionsClient()

# --- Data Models (Pydantic) ---
class JobConfig(BaseModel):
    base_prompt: str
    evaluation_metric: str
    test_data: list[dict] # e.g., [{"input": "..."}]

# --- Routes ---

@app.get("/")
def root():
    return {"message": "PromptFlow API is running"}

@app.post("/jobs")
async def create_job(config: JobConfig):
    """
    Creates a new optimization job and triggers the Cloud Workflow.
    """
    if not PROJECT_ID:
        raise HTTPException(status_code=500, detail="GOOGLE_CLOUD_PROJECT env var not set.")

    # 1. Create a new Job Document in Firestore
    # We set the initial status to PENDING
    new_job_ref = db.collection('jobs').document()
    job_id = new_job_ref.id
    
    job_data = {
        "status": "PENDING",
        "created_at": firestore.SERVER_TIMESTAMP,
        "config": {
            "basePrompt": config.base_prompt,
            "evaluationMetric": config.evaluation_metric
        },
        "testDataset": config.test_data,
        "bestScore": 0.0,
        "generationCount": 0
    }
    new_job_ref.set(job_data)

    # 2. Trigger the Cloud Workflow
    # The workflow needs to know WHICH job to work on, so we pass the job_id.
    workflow_parent = f"projects/{PROJECT_ID}/locations/{LOCATION}/workflows/{WORKFLOW_NAME}"
    
    execution_args = {"job_id": job_id}
    
    try:
        # Create the execution
        response = execution_client.create_execution(
            request=executions_v1.CreateExecutionRequest(
                parent=workflow_parent,
                execution=Execution(argument=json.dumps(execution_args))
            )
        )
        print(f"Started workflow execution: {response.name}")
        
    except Exception as e:
        print(f"Failed to start workflow: {e}")
        # If workflow fails to start, mark job as FAILED so user knows
        new_job_ref.update({"status": "FAILED_TO_START"})
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "job_id": job_id, 
        "status": "PENDING",
        "workflow_execution_id": response.name
    }

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Retrieves the current status and results of a job.
    """
    doc_ref = db.collection('jobs').document(job_id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="Job not found")

    return doc.to_dict()
