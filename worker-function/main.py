import functions_framework
import vertexai
import vertexai.generative_models as gen_models
from vertexai.generative_models import GenerativeModel, GenerationConfig
import os
import json
import re

# Configuration
PROJECT_ID = os.environ.get("GCP_PROJECT") 
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash" 

# Initialization
model = None

def init_model():
    global model
    if model is None:
        print(f"🔄 Initializing Vertex AI for project: {PROJECT_ID}")
        vertexai.init(project=PROJECT_ID, location=LOCATION)
        
        # PERMISSIVE SAFETY SETTINGS
        safety_config = {
            gen_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: gen_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            gen_models.HarmCategory.HARM_CATEGORY_HARASSMENT: gen_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            gen_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: gen_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            gen_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: gen_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        
        model = GenerativeModel(MODEL_NAME, safety_settings=safety_config)
        print("Worker: Vertex AI client initialized.")

def clean_json_string(json_str):
    """Removes markdown code blocks if present."""
    if "```json" in json_str:
        json_str = json_str.replace("```json", "").replace("```", "")
    elif "```" in json_str:
        json_str = json_str.replace("```", "")
    return json_str.strip()

@functions_framework.http
def prompt_eval_worker(request):
    try:
        init_model()
    except Exception as e:
        return (f"Init Failed: {e}", 500)

    try:
        data = request.get_json()
        prompt_to_test = data.get('prompt')
        test_input = data.get('test_input')
        eval_criteria = data.get('eval_metric')
    except Exception as e:
        return (f"Parse Error: {e}", 400)

    # GENERATE
    try:
        final_prompt = prompt_to_test.format(input=test_input)
        response = model.generate_content(final_prompt)
        llm_output = response.text
    except Exception as e:
        print(f"Gen Error: {e}")
        llm_output = "Error: Content Blocked or Failed."

    # JUDGE
    judge_reasoning = "N/A"
    score = 0.0
    
    try:
        judge_prompt = f"""
        You are an impartial AI Judge.
        
        Task: Grade the GENERATED OUTPUT on a scale of 0 to 10 based on the CRITERIA.
        
        CRITERIA: {eval_criteria}
        
        USER INPUT: \"\"\"{test_input}\"\"\"
        GENERATED OUTPUT: \"\"\"{llm_output}\"\"\"
        
        Instructions:
        - Return a JSON object with two fields:
          1. "score": integer 0-10.
          2. "reasoning": short explanation.
        """
        
        judge_res = model.generate_content(
            judge_prompt,
            generation_config=GenerationConfig(response_mime_type="application/json")
        )
        
        # CLEAN THE JSON BEFORE PARSING
        clean_text = clean_json_string(judge_res.text)
        result_json = json.loads(clean_text)
        
        raw_score = result_json.get("score", 0)
        judge_reasoning = result_json.get("reasoning", "No reasoning provided")
        score = float(raw_score) / 10.0
        
    except Exception as e:
        print(f"Scoring Error: {e}")
        judge_reasoning = f"Judge Failed: {str(e)}"
        score = 0.0

    # LOGGING TO PROVE IT RAN
    print(f"Returning result with reasoning: {judge_reasoning}")

    return {
        "prompt": prompt_to_test,
        "output": llm_output,
        "score": score,
        "reasoning": judge_reasoning 
    }, 200
