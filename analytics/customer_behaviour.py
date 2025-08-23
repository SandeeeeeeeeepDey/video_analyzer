import gradio as gr
import json
from .prompts import CUSTOMER_BEHAVIOUR_PROMPT
from model_utils.existing_generation import generate_content_existing
from model_utils.new_generation import generate_content_new
import pandas as pd
from .prompt_templates import PROMPT_TEMPLATES
import re
from .prompts import CUSTOMER_BEHAVIOUR_PROMPT

def create_ui():
    output_textboxes = {} # Dictionary to store the Textbox components

    with gr.Column(): # Use a Column or Row to group elements within the tab
        gr.Markdown("## Customer Behaviour Analysis")
        gr.Markdown(CUSTOMER_BEHAVIOUR_PROMPT.split("## ")[0].split("\n\nCustomer Behaviour Scopes")[-1])
        gr.Markdown("## Analysis Result")

        output_keys = PROMPT_TEMPLATES["customer_behaviour"]["output_keys"]

        for key in output_keys:
            with gr.Group():
                gr.Markdown(f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}")
                output_textboxes[key] = gr.Textbox(label=f"", interactive=False, lines=5, autoscroll=True, elem_id=f"customer_behaviour_{key}")

    return output_textboxes

def analyze_customerbehaviour_video(video_path):
    if not video_path:
        return None # Return None if no video path

    def _clean_json_string(text):
        if text.startswith("Error decoding JSON: "):
            text = text[len("Error decoding JSON: "):].strip()
        
        json_start = text.find("```json")
        json_end = text.rfind("```")
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start + len("```json"):json_end].strip()
            
        return text

    full_response = ""
    for chunk in generate_content_existing(video_path, CUSTOMER_BEHAVIOUR_PROMPT, "customer_behaviour"):
        full_response += chunk
    
    # Clean the full_response before attempting to parse JSON
    cleaned_response = _clean_json_string(full_response)

    try:
        json_data = json.loads(cleaned_response)
        print("Full JSON structure:", json.dumps(json_data, indent=2))
        
        # Assumes the top-level key is "CustomerBehaviour", similar to "HygieneAndFoodSafety" in the perfect code
        data = json_data["CustomerBehaviour"]
        
        # Create a dictionary to return with the exact keys the UI expects
        result = {}
        
        # Process each category and format the output
        for category_name, items in data.items():
            output_strings = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        parts = []
                        if "description" in item:
                            parts.append(f"description: '{item['description']}'")
                        if "observation" in item:
                            parts.append(f"observation: '{item['observation']}'")
                        if "timestamp" in item:
                            parts.append(f"timestamp: {item['timestamp']}")
                        if parts:  # Only add if we have content
                            output_strings.append("\n".join(parts))
            
            # Use the exact category names as keys (PascalCase as they appear in JSON)
            result[category_name] = "\n\n".join(output_strings) if output_strings else "No data found"
        
        print("Returning result with keys:", list(result.keys()))
        return result
        
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {cleaned_response}")
        return {"error": "Invalid JSON response from model.", "raw_response": cleaned_response}