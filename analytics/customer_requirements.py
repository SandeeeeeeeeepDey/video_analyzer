import gradio as gr
import json
from .prompts import CUSTOMER_REQUIREMENTS_PROMPT
from model_utils.existing_generation import generate_content_existing
from model_utils.new_generation import generate_content_new
import pandas as pd
from .prompt_templates import PROMPT_TEMPLATES
import re
from .prompts import CUSTOMER_REQUIREMENTS_PROMPT

def create_ui():
    output_textboxes = {} # Dictionary to store the Textbox components

    with gr.Column(): # Use a Column or Row to group elements within the tab
        gr.Markdown("## Customer Requirements Analysis")
        gr.Markdown(CUSTOMER_REQUIREMENTS_PROMPT.split("## ")[0].split("\n\nCustomer Requirement Scopes")[-1])
        gr.Markdown("## Analysis Result")

        output_keys = PROMPT_TEMPLATES["customer_requirements"]["output_keys"]

        for key in output_keys:
            with gr.Group():
                gr.Markdown((f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}"))
                # Store the Textbox component in the dictionary
                output_textboxes[key] = gr.Textbox(label=f"Generated Output for {key.replace('_', ' ').title()}", interactive=False, lines=5, autoscroll=True, elem_id=f"customer_requirements_{key}")

    # Return the dictionary of Textbox components
    return output_textboxes

def analyze_customerrequirements_video(video_path):
    # The list of keys defines the order of outputs
    output_keys = PROMPT_TEMPLATES["customer_requirements"]["output_keys"]

    if not video_path:
        # Return a list of empty strings to clear the textboxes
        return [""] * len(output_keys)

    def _clean_json_string(text):
        # ... (your _clean_json_string function is fine, no changes needed) ...
        if text.startswith("Error decoding JSON: "):
            text = text[len("Error decoding JSON: "):].strip()
        
        json_start = text.find("```json")
        json_end = text.rfind("```")
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start + len("```json"):json_end].strip()
            
        return text

    full_response = ""
    try:
        for chunk in generate_content_existing(video_path, CUSTOMER_REQUIREMENTS_PROMPT, "customer_requirements"):
            full_response += chunk
        
        cleaned_response = _clean_json_string(full_response)
        json_data = json.loads(cleaned_response)
        print(json_data)
        # Find the main data section
        data = None
        possible_keys = ["CustomerRequirements", "customer_requirements", "analysis", "results"]
        for key in possible_keys:
            if key in json_data:
                data = json_data[key]
                break
        
        if data is None:
            data = json_data

        # This dictionary will hold the processed text for each category
        processed_results = {}
        for category_name, items in data.items():
            output_strings = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        parts = []
                        # Your logic is good. Let's make it slightly more robust.
                        desc = item.get("description", "N/A")
                        ts = item.get("timestamp", "N/A")
                        obs = item.get("observation") # Handle optional 'observation'
                        
                        parts.append(f"Description: '{desc}'")
                        if obs:
                           parts.append(f"Observation: '{obs}'")
                        parts.append(f"Timestamp: {ts}")
                        
                        output_strings.append("\n".join(parts))
            
            processed_results[category_name] = "\n\n".join(output_strings) if output_strings else "No relevant information found in the video for this category."

        print("processed_results", processed_results)
        return processed_results

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}\nRaw response was: {cleaned_response}")
        error_message = f"Error: The model returned an invalid JSON response.\n\nRaw Text:\n{cleaned_response}"
        # Return the same error message for all textboxes
        return [error_message] * len(output_keys)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        error_message = f"An unexpected error occurred: {e}"
        return [error_message] * len(output_keys)