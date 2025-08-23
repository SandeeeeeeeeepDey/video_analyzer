import gradio as gr
import json
from .prompts import FOLLOWING_COOKING_STEPS_PROMPT
from model_utils.existing_generation import generate_content_existing
from model_utils.new_generation import generate_content_new
import pandas as pd
from .prompt_templates import PROMPT_TEMPLATES
import re
from .prompts import FOLLOWING_COOKING_STEPS_PROMPT

def create_ui():
    output_textboxes = {} # Dictionary to store the Textbox components

    with gr.Column(): # Use a Column or Row to group elements within the tab
        gr.Markdown("## Following Cooking Steps Analysis")
        gr.Markdown(FOLLOWING_COOKING_STEPS_PROMPT.split("## ")[0].split("\n\nCooking Step Scopes")[-1])
        gr.Markdown("## Analysis Result")

        output_keys = PROMPT_TEMPLATES["following_cooking_steps"]["output_keys"]

        for key in output_keys:
            with gr.Group():
                gr.Markdown((f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}"))
                output_textboxes[key] = gr.Textbox(label=f"Generated Output for {key.replace('_', ' ').title()}", interactive=False, lines=5, autoscroll=True, elem_id=f"following_cooking_steps_{key}")

        # Add SOP textbox and button at the bottom, side by side
        with gr.Row():
            with gr.Column(scale=3):
                sop_textbox = gr.Textbox(
                    label="Standard Operating Procedure (SOP)", 
                    placeholder="Enter any specific cooking standards, procedures, or guidelines to consider during analysis...",
                    lines=4,
                    interactive=True
                )
            with gr.Column(scale=1):
                analyze_button = gr.Button("Analyze Following Cooking Steps", variant="primary", size="lg")

    # Return both output textboxes and the new components
    return output_textboxes, sop_textbox, analyze_button

def analyze_followingcookingsteps_video(video_path, sop_input):
    if not video_path:
        return None # Return None if no video path

    # Modify the prompt to include SOP if provided
    prompt = FOLLOWING_COOKING_STEPS_PROMPT
    if sop_input and sop_input.strip():
        prompt += f"\n\n## Standard Operating Procedure (SOP)\n{sop_input.strip()}\n\nPlease consider the above SOP when analyzing the cooking steps."

    def _clean_json_string(text):
        if text.startswith("Error decoding JSON: "):
            text = text[len("Error decoding JSON: "):].strip()
        
        json_start = text.find("```json")
        json_end = text.rfind("```")
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start + len("```json"):json_end].strip()
            
        return text

    full_response = ""
    # Use the modified prompt with SOP
    for chunk in generate_content_existing(video_path, prompt, "following_cooking_steps"):
        full_response += chunk
    
    # Clean the full_response before attempting to parse JSON
    cleaned_response = _clean_json_string(full_response)

    try:
        json_data = json.loads(cleaned_response)
        print("Full JSON structure:", json.dumps(json_data, indent=2))
        
        # Find the main data section
        data = None
        possible_keys = ["FollowingCookingSteps", "following_cooking_steps", "CookingSteps", "analysis", "results"]
        
        for key in possible_keys:
            if key in json_data:
                data = json_data[key]
                print(f"Found data under key: {key}")
                break
        
        if data is None:
            # If no expected key found, use the entire json_data
            data = json_data
            print("Using entire JSON data")
        
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
                        if "step" in item:
                            parts.append(f"step: '{item['step']}'")
                        if "status" in item:
                            parts.append(f"status: '{item['status']}'")
                        if parts:  # Only add if we have content
                            output_strings.append("\n".join(parts))
            
            # Use the exact category names as keys
            result[category_name] = "\n\n".join(output_strings) if output_strings else "No data found"
        
        print("Returning result with keys:", list(result.keys()))
        return result
        
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {cleaned_response}")
        return {"error": "Invalid JSON response from model.", "raw_response": cleaned_response}

# analytics/following_cooking_steps.py

import gradio as gr
import json
import re
from .prompts import FOLLOWING_COOKING_STEPS_PROMPT
from model_utils.existing_generation import generate_content_existing
from .prompt_templates import PROMPT_TEMPLATES

# WE NO LONGER NEED THE create_ui() FUNCTION. DELETE IT.

def analyze_followingcookingsteps_video(video_path, sop_input):
    if not video_path:
        # Return a dictionary with keys matching the output textboxes to clear them
        output_keys = PROMPT_TEMPLATES["following_cooking_steps"]["output_keys"]
        return {key: "" for key in output_keys}

    prompt = FOLLOWING_COOKING_STEPS_PROMPT
    if sop_input and sop_input.strip():
        prompt += f"\n\n## Standard Operating Procedure (SOP)\n{sop_input.strip()}\n\nPlease consider the above SOP when analyzing the cooking steps."

    def _clean_json_string(text):
        if text.startswith("Error decoding JSON: "):
            text = text[len("Error decoding JSON: "):].strip()
        json_start = text.find("```json")
        json_end = text.rfind("```")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start + len("```json"):json_end].strip()
        return text

    full_response = ""
    for chunk in generate_content_existing(video_path, prompt, "following_cooking_steps"):
        full_response += chunk
    
    cleaned_response = _clean_json_string(full_response)

    try:
        json_data = json.loads(cleaned_response)
        data = json_data.get("FollowingCookingSteps", json_data) # Simplified data extraction
        
        result = {}
        for category_name, items in data.items():
            output_strings = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        parts = [f"{k}: '{v}'" for k, v in item.items()]
                        if parts:
                            output_strings.append("\n".join(parts))
            result[category_name] = "\n\n".join(output_strings) if output_strings else "No data found"
        
        return result
        
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {cleaned_response}")
        return {"error": "Invalid JSON response from model.", "raw_response": cleaned_response}

# THIS IS THE ONLY UI FUNCTION YOU NEED FROM THIS FILE
def create_tab(video_player):
    """Creates a self-contained, fully functional Gradio tab."""
    with gr.Blocks() as following_cooking_steps_tab:
        # Display information at the top
        gr.Markdown("## Following Cooking Steps Analysis")
        gr.Markdown(FOLLOWING_COOKING_STEPS_PROMPT.split("## ")[0].split("\n\nCooking Step Scopes")[-1])
        gr.Markdown("## Analysis Result")
        
        output_textboxes = {}
        output_keys = PROMPT_TEMPLATES["following_cooking_steps"]["output_keys"]

        for key in output_keys:
            with gr.Group():
                gr.Markdown(f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}")
                output_textboxes[key] = gr.Textbox(
                    label=f"Generated Output for {key.replace('_', ' ').title()}", 
                    interactive=False, 
                    lines=5, 
                    autoscroll=True
                )

        # SOP input and button at the very bottom, side by side
        with gr.Row():
            with gr.Column(scale=3):
                sop_textbox = gr.Textbox(
                    label="Standard Operating Procedure (SOP)", 
                    placeholder="Enter any specific cooking standards...",
                    lines=4,
                    interactive=True
                )
            with gr.Column(scale=1):
                analyze_button = gr.Button("Analyze Following Cooking Steps", variant="primary", size="lg")

        # This handler function now correctly processes the dictionary output
        def handle_analysis(video_path, sop_input):
            result = analyze_followingcookingsteps_video(video_path, sop_input)
            # Return values in the same order as the textboxes were created
            return [result.get(key, f"Error: No data for {key}") for key in output_keys]

        # THE CRITICAL PART: The .click event is wired up HERE
        analyze_button.click(
            fn=handle_analysis,
            inputs=[video_player, sop_textbox],
            outputs=list(output_textboxes.values())
        )
    return following_cooking_steps_tab

# import gradio as gr
# import json
# from .prompts import FOLLOWING_COOKING_STEPS_PROMPT
# from model_utils.existing_generation import generate_content_existing
# from model_utils.new_generation import generate_content_new
# import pandas as pd
# from .prompt_templates import PROMPT_TEMPLATES
# import re
# from .prompts import FOLLOWING_COOKING_STEPS_PROMPT

# def create_ui():
#     output_textboxes = {} # Dictionary to store the Textbox components

#     with gr.Column(): # Use a Column or Row to group elements within the tab
#         gr.Markdown("## Following Cooking Steps Analysis")
#         gr.Markdown(FOLLOWING_COOKING_STEPS_PROMPT.split("## ")[0].split("\n\nCooking Step Scopes")[-1])
#         gr.Markdown("## Analysis Result")

#         output_keys = PROMPT_TEMPLATES["following_cooking_steps"]["output_keys"]

#         for key in output_keys:
#             with gr.Group():
#                 gr.Markdown((f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}"))
#                 output_textboxes[key] = gr.Textbox(label=f"Generated Output for {key.replace('_', ' ').title()}", interactive=False, lines=5, autoscroll=True, elem_id=f"following_cooking_steps_{key}")

#     return output_textboxes

# def analyze_followingcookingsteps_video(video_path):
#     if not video_path:
#         return None # Return None if no video path

#     def _clean_json_string(text):
#         if text.startswith("Error decoding JSON: "):
#             text = text[len("Error decoding JSON: "):].strip()
        
#         json_start = text.find("```json")
#         json_end = text.rfind("```")
        
#         if json_start != -1 and json_end != -1 and json_end > json_start:
#             text = text[json_start + len("```json"):json_end].strip()
            
#         return text

#     full_response = ""
#     for chunk in generate_content_existing(video_path, FOLLOWING_COOKING_STEPS_PROMPT, "following_cooking_steps"):
#         full_response += chunk
    
#     # Clean the full_response before attempting to parse JSON
#     cleaned_response = _clean_json_string(full_response)

#     try:
#         json_data = json.loads(cleaned_response)
#         print("Full JSON structure:", json.dumps(json_data, indent=2))
        
#         # Find the main data section
#         data = None
#         possible_keys = ["FollowingCookingSteps", "following_cooking_steps", "CookingSteps", "analysis", "results"]
        
#         for key in possible_keys:
#             if key in json_data:
#                 data = json_data[key]
#                 print(f"Found data under key: {key}")
#                 break
        
#         if data is None:
#             # If no expected key found, use the entire json_data
#             data = json_data
#             print("Using entire JSON data")
        
#         # Create a dictionary to return with the exact keys the UI expects
#         result = {}
        
#         # Process each category and format the output
#         for category_name, items in data.items():
#             output_strings = []
#             if isinstance(items, list):
#                 for item in items:
#                     if isinstance(item, dict):
#                         parts = []
#                         if "description" in item:
#                             parts.append(f"description: '{item['description']}'")
#                         if "observation" in item:
#                             parts.append(f"observation: '{item['observation']}'")
#                         if "timestamp" in item:
#                             parts.append(f"timestamp: {item['timestamp']}")
#                         if "step" in item:
#                             parts.append(f"step: '{item['step']}'")
#                         if "status" in item:
#                             parts.append(f"status: '{item['status']}'")
#                         if parts:  # Only add if we have content
#                             output_strings.append("\n".join(parts))
            
#             # Use the exact category names as keys
#             result[category_name] = "\n\n".join(output_strings) if output_strings else "No data found"
        
#         print("Returning result with keys:", list(result.keys()))
#         return result
        
#     except json.JSONDecodeError:
#         print(f"Error decoding JSON: {cleaned_response}")
#         return {"error": "Invalid JSON response from model.", "raw_response": cleaned_response}

# def create_tab(video_player):
#     with gr.Blocks() as following_cooking_steps_tab:
#         with gr.Row():
#             analyze_button = gr.Button("Analyze Following Cooking Steps", variant="primary")
        
#         gr.Markdown("## Following Cooking Steps Analysis Scopes")
#         gr.Markdown(FOLLOWING_COOKING_STEPS_PROMPT) # Display the fixed prompt content

#         gr.Markdown("## Analysis Result")
#         with gr.Box():
#             # This will hold the structured UI from following_cooking_steps_ui.py
#             following_cooking_steps_output_display = gr.Blocks() # Use gr.Blocks to hold the dynamic UI

#         analyze_button.click(
#             analyze_followingcookingsteps_video,
#             inputs=[video_player],
#             outputs=following_cooking_steps_output_display,
#             postprocess=create_ui # Pass the parsed JSON to create_ui
#         )
#     return following_cooking_steps_tab