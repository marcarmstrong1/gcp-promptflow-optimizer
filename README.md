PromptFlow: Serverless Evolutionary Prompt Optimization

PromptFlow is a cloud-native, distributed framework designed to automate the optimization of Large Language Model (LLM) prompts.

By leveraging Google Cloud Workflows and Cloud Functions, this system transforms the manual, linear process of prompt engineering into a parallel, evolutionary genetic algorithm. It uses an "LLM-as-a-Judge" architecture to autonomously score and evolve prompts, reducing optimization time by approximately 80% compared to sequential testing.

System Architecture

PromptFlow utilizes a strictly decoupled, event-driven microservices architecture to achieve "Scale-to-Zero" efficiency and massive burst parallelism.

graph LR
    User[User] --> UI[Streamlit UI]
    UI --> API[FastAPI Gateway]
    API --> DB[(Firestore)]
    API --> Workflow[Cloud Workflows]
    Workflow --> Gen[Generator Node]
    Workflow --> Eval[Evaluator Nodes xN]
    Gen --> Vertex[Vertex AI]
    Eval --> Vertex
    Eval --> DB


Core Components

Orchestrator (Cloud Workflows): The central state machine that manages the evolutionary loop, retries, and parallel branching.

Generator Node (Cloud Functions): Acts as the "Mutation Operator," using Gemini 1.5 Flash to create variations of prompts based on parent traits (Crossover).

Evaluator Node (Cloud Functions): A stateless worker that runs in parallel. It executes the prompt and then performs a secondary "Judge" inference to grade the output (0-10) with reasoning.

State Store (Firestore): NoSQL database acting as the single source of truth for job configurations and granular results.

Interface (Cloud Run): A containerized Streamlit dashboard for Human-in-the-Loop selection and monitoring.

Key Features

Evolutionary Optimization: Implements a genetic algorithm cycle (Genesis -> Evaluation -> Selection -> Breeding) to evolve prompts over generations.

LLM-as-a-Judge: Replaces brittle keyword matching with a semantic AI judge that scores outputs on nuance, tone, and accuracy, providing text-based reasoning.

Massive Parallelism: Tests 50+ prompt variations simultaneously using Cloud Workflows' parallel loops, reducing wall-clock latency from minutes to seconds.

Human-in-the-Loop (HITL): An interactive UI allows users to review the "Reasoning" of the AI Judge and manually select the best "Parent" prompts for the next generation.

Robust Error Handling: Handles stochastic AI failures, JSON parsing errors, and safety filter collisions gracefully without crashing the pipeline.

Deployment Guide

Prerequisites

Google Cloud Platform (GCP) Project with Billing Enabled.

gcloud CLI installed and authenticated.

Python 3.12+

1. Environment Setup

Clone the repository and set your project variables:

git clone [https://github.com/your-username/gcp-promptflow-optimizer.git](https://github.com/your-username/gcp-promptflow-optimizer.git)
cd gcp-promptflow-optimizer

export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
gcloud config set project $PROJECT_ID


2. Service Account Setup

Create dedicated identities for security (Principle of Least Privilege):

# Create API Service Account
gcloud iam service-accounts create promptflow-api-sa --display-name="PromptFlow API SA"

# Grant permissions (Simplified for setup; tighten for production)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:promptflow-api-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:promptflow-api-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/workflows.invoker"


3. Deploy Microservices

A. Deploy Cloud Functions (Worker & Generator)

# Deploy Evaluator (Worker)
gcloud functions deploy prompt-eval-worker \
    --gen2 --region=$REGION \
    --source=./worker-function --entry-point=prompt_eval_worker \
    --trigger-http --timeout=300s --memory=2048Mi --cpu=1 \
    --allow-unauthenticated \
    --set-env-vars=GCP_PROJECT=$PROJECT_ID

# Deploy Generator
gcloud functions deploy prompt-generator \
    --gen2 --region=$REGION \
    --source=./generator-function --entry-point=generate_prompts \
    --trigger-http --timeout=300s --memory=2048Mi --cpu=1 \
    --allow-unauthenticated


B. Deploy API Gateway

cd api-service
gcloud run deploy promptflow-api \
    --source=. --platform=managed --region=$REGION \
    --allow-unauthenticated \
    --service-account=promptflow-api-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars=GOOGLE_CLOUD_PROJECT=$PROJECT_ID
cd ..


C. Deploy Orchestrator
Edit orchestrator/workflow.yaml and update the worker_url and generator_url with the URLs from Step 3A.

cd orchestrator
gcloud workflows deploy promptflow-orchestrator \
    --source=workflow.yaml --location=$REGION
cd ..


D. Deploy User Interface

cd ui-app
# Get the API URL from Step 3B
export API_URL=$(gcloud run services describe promptflow-api --platform=managed --region=$REGION --format='value(status.url)')

gcloud run deploy promptflow-ui \
    --source=. --platform=managed --region=$REGION \
    --allow-unauthenticated \
    --set-env-vars=API_URL=$API_URL
cd ..


Usage

Open the Streamlit UI URL provided by the deployment command.

Configure the Task:

Base Prompt: e.g., "Translate to pirate style: {input}"

Test Data: e.g., "Hello my friend, I will return shortly."

Evaluation Criteria: e.g., "Must sound authentic 18th century, not cartoonish."

Click Launch Optimization Job.

Wait for the status to change from PENDING -> RUNNING -> COMPLETE.

Review Results: Check the "Score" and "Reasoning" columns.

Evolve: Select the best prompts using the checkboxes and click "Spawn Generation 2" to breed a better prompt.

Project Structure

gcp-promptflow-optimizer/
├── api-service/          # FastAPI Gateway (Cloud Run)
│   ├── main.py
│   └── Dockerfile
├── generator-function/   # Prompt Mutation Logic (Cloud Function)
│   └── main.py
├── worker-function/      # LLM Execution & Judging (Cloud Function)
│   └── main.py
├── orchestrator/         # State Machine Logic (Cloud Workflows)
│   └── workflow.yaml
├── ui-app/               # Dashboard (Streamlit on Cloud Run)
│   └── app.py
└── README.md


Engineering Challenges & Solutions

Thundering Herd (503 Errors): Initial parallelism caused cold-start exhaustion. Solved by vertically scaling workers to 2GB RAM / 1 vCPU to handle Vertex AI initialization.

Stochastic Output: The LLM Judge occasionally returned Markdown, breaking the pipeline. Solved via robust string cleaning and JSON parsing middleware in the worker.

Safety Filters: "Pirate Talk" triggered harassment filters. Solved by explicitly configuring SafetySettings to BLOCK_ONLY_HIGH.
