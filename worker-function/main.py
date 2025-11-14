import functions_framework
import vertexai
from vertexai.generative_models import GenerativeModel
import os

# --- Configuration ---
PROJECT_ID = os.environ.get("GCP_PROJECT", "promptflow-project-xyz")  # Will be set by GCP
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash" 

# --- Initialization ---
# This is done globally to reuse the client across function invocations
try:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(MODEL_NAME)
    print("Vertex AI client initialized.")
except Exception as e:
    print(f"Error initializing Vertex AI: {e}")
    model = None

@functions_framework.http
def prompt_eval_worker(request):
    """
    An HTTP-triggered Cloud Function that evaluates a single prompt.
    
    Receives JSON body:
    {
        "prompt": "The prompt template, e.g., 'Summarize: {input}'",
        "test_input": "The text to insert into the prompt.",
        "eval_metric": "The simple string to check for, e.g., 'Summary:'"
    }
    
    Returns JSON body:
    {
        "prompt": "The tested prompt",
        "output": "The LLM's full response",
        "score": 1.0 or 0.0
    }
    """
    
    # 1. Check if the model initialized correctly
    if model is None:
        return ("Internal Server Error: Model client not initialized.", 500)

    # 2. Get data from the request body
    try:
        data = request.get_json()
        prompt_to_test = data['prompt']
        test_input = data['test_input']
        eval_metric = data['eval_metric']
    except Exception as e:
        print(f"Error parsing request: {e}")
        return (f"Bad Request: Missing or invalid JSON body. {e}", 400)

    # 3. Format the final prompt
    try:
        final_prompt = prompt_to_test.format(input=test_input)
    except KeyError:
        return (f"Bad Request: The 'prompt' is missing an '{{input}}' placeholder.", 400)

    # 4. Call the LLM (Gemini)
    try:
        print(f"Evaluating prompt: {final_prompt[:100]}...") # Log for debugging
        response = model.generate_content(final_prompt)
        llm_output = response.text
    except Exception as e:
        print(f"Error calling Vertex AI: {e}")
        return (f"Error from LLM: {e}", 500)

    # 5. Evaluate the output (your simple metric)
    score = 0.0
    if eval_metric.lower() in llm_output.lower():
        score = 1.0

    print(f"Evaluation complete. Score: {score}")

    # 6. Return the result
    result = {
        "prompt": prompt_to_test,
        "output": llm_output,
        "score": score
    }
    
    return (result, 200)
