import gradio as gr
import json
from .prompts import CUSTOMER_BEHAVIOUR_PROMPT
from model_utils.existing_generation import generate_content_existing
from model_utils.new_generation import generate_content_new
import pandas as pd
from .prompt_templates import PROMPT_TEMPLATES
import re

def create_ui():
    output_textboxes = {} # Dictionary to store the Textbox components

    with gr.Column(): # Use a Column or Row to group elements within the tab
        gr.Markdown("## Customer Behaviour Analysis")

        output_keys = PROMPT_TEMPLATES["customer_behaviour"]["output_keys"] # Using customer_behaviour as discussed

        for key in output_keys:
            with gr.Group():
                gr.Markdown((f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}"))
                output_textboxes[key] = gr.Textbox(label=f"Generated Output for {key.replace('_', ' ').title()}", interactive=False, lines=5, autoscroll=True, elem_id=f"customer_behaviour_{key}")

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
    for chunk in generate_content_existing(video_path, CUSTOMER_BEHAVIOUR_PROMPT):
        full_response += chunk
    
    # Clean the full_response before attempting to parse JSON
    cleaned_response = _clean_json_string(full_response)

    try:
        json_data = json.loads(cleaned_response)
        return json_data # Return parsed JSON object
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {cleaned_response}")
        return {"error": "Invalid JSON response from model.", "raw_response": cleaned_response}
