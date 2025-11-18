import functions_framework
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import os

# --- Configuration ---
LOCATION = "us-central1"
MODEL_NAME = "gemini-2.5-flash" 

# --- Initialization ---
try:
    vertexai.init(location=LOCATION)
    model = GenerativeModel(MODEL_NAME)
    print("Generator: Vertex AI client initialized.")
except Exception as e:
    print(f"Generator: Error initializing Vertex AI: {e}")
    model = None

@functions_framework.http
def generate_prompts(request):
    """
    Generates a population of prompt variations.
    
    Input JSON:
    {
        "base_prompt": "Summarize {input}",
        "generation": 1,
        "count": 5
    }
    
    Output JSON:
    {
        "prompts": ["Summarize {input}", "TL;DR {input}", ...]
    }
    """
    if model is None:
        return ("Internal Server Error: Model not initialized.", 500)

    try:
        data = request.get_json()
        base_prompt = data.get('base_prompt')
        generation = data.get('generation', 1)
        count = data.get('count', 4)
    except Exception as e:
        return (f"Bad Request: {e}", 400)

    print(f"Generaton {generation}: Creating {count} variations for: {base_prompt}")

    # --- The Meta-Prompt ---
    # We ask Gemini to write prompts for us.
    meta_prompt = f"""
    You are an expert Prompt Engineer. Your goal is to optimize the following prompt:
    "{base_prompt}"

    Please generate {count} distinct variations of this prompt. 
    - Some should be more concise.
    - Some should use a different persona or tone.
    - Some should use "Chain of Thought" (e.g. "Think step by step").
    - CRITICAL: All prompts MUST retain the {{input}} placeholder.
    
    Return ONLY a JSON array of strings. Example: ["Prompt variant 1 {input}", "Prompt variant 2 {input}"]
    Do not include markdown formatting like ```json.
    """

    try:
        # We force JSON output for easier parsing
        response = model.generate_content(
            meta_prompt,
            generation_config=GenerationConfig(response_mime_type="application/json")
        )
        
        # Parse the result
        prompts_list = json.loads(response.text)
        
        # Always ensure the original base prompt is included in the first generation
        if generation == 1 and base_prompt not in prompts_list:
            prompts_list.insert(0, base_prompt)

        return {"prompts": prompts_list}, 200

    except Exception as e:
        print(f"Generator Error: {e}")
        # Fallback: if AI fails, just return the base prompt so the workflow doesn't crash
        return {"prompts": [base_prompt]}, 200
