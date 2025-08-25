import gradio as gr
import json
from .prompts import QUEUE_LENGTH_PROMPT
from model_utils.existing_generation import generate_content_existing
from model_utils.new_generation import generate_content_new
import pandas as pd
from .prompt_templates import PROMPT_TEMPLATES
import re
from model_utils.yolo_model import get_yolo_model
import os
import subprocess
import shutil
from pathlib import Path

# Same video enricher as occupancy
model_bbox = get_yolo_model()

def video_enricher(video_path, overwrite=False, delete_avi=False):
    """
    Run YOLO to create annotated AVI → convert to MP4 → return MP4 path.
    If the MP4 already exists and overwrite is False, returns immediately.
    Uses a .processing marker file to avoid races with concurrent runs.
    """
    project_dir = Path("analytics/queue_length_outputs")  # Different output folder
    run_name = "person"
    project_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(video_path).stem
    avi_output = project_dir / run_name / f"{base_name}.avi"
    mp4_output = avi_output.with_suffix(".mp4")
    processing_marker = mp4_output.with_suffix(mp4_output.suffix + ".processing")

    # If final mp4 exists and user doesn't want overwrite -> return it
    if mp4_output.exists() and not overwrite:
        # Optional: check size to avoid zero-byte files
        if mp4_output.stat().st_size > 1024:   # 1 KB threshold, tweak as needed
            return str(mp4_output)
        # if file is suspiciously small, we'll re-generate it (fall through)

    # If another run is in progress, raise or bail out
    if processing_marker.exists():
        raise RuntimeError(f"Processing already in progress for: {mp4_output}")

    try:
        # create marker so other processes know work is ongoing
        processing_marker.parent.mkdir(parents=True, exist_ok=True)
        processing_marker.write_text("processing")

        # Run YOLO (same as your pipeline) — this should create the .avi
        results_generator = model_bbox.track(
            source=video_path,
            classes=0,
            persist=True,
            save=True,
            project=str(project_dir),
            name=run_name,
            exist_ok=True,
            verbose=False,
            stream=True,
            show_labels=False,  # if you want no labels
            show_conf=False
        )
        for _ in results_generator:
            pass

        if not avi_output.exists():
            raise FileNotFoundError(f"Expected output .avi not found: {avi_output}")

        # find ffmpeg (or fall back to imageio-ffmpeg)
        ffmpeg_exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if ffmpeg_exe is None:
            try:
                import imageio_ffmpeg
                ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except Exception:
                ffmpeg_exe = None

        if ffmpeg_exe is None:
            raise EnvironmentError("ffmpeg not found. Install ffmpeg or imageio-ffmpeg.")

        # Convert AVI -> MP4
        cmd = [ffmpeg_exe, "-y", "-i", str(avi_output), 
               "-c:v", "libx264", "-preset", "fast", 
               "-crf", "23", str(mp4_output)]
        subprocess.run(cmd, check=True)

        print(f"enriched: {mp4_output}")
        # optional cleanup
        if delete_avi:
            try:
                avi_output.unlink()
            except OSError:
                pass

        # final sanity check
        if not mp4_output.exists() or mp4_output.stat().st_size == 0:
            raise RuntimeError("Conversion produced invalid mp4 file.")

        return str(mp4_output)

    finally:
        # always remove marker (so failures don't block future runs)
        try:
            if processing_marker.exists():
                processing_marker.unlink()
        except OSError:
            pass

def create_ui():
    """Create UI components for queue length analysis and return them as a dictionary.

    Returns:
        dict with keys:
            - "video_output": gr.Video component
            - "text_outputs": dict mapping output_key -> gr.Textbox component
    """
    # Primary components
    gr.Markdown("## Queue Length Analysis")
    
    
    # Side-by-side layout for description and video
    with gr.Row():
        with gr.Column(scale=1):
            # Description on the left
            gr.Markdown(QUEUE_LENGTH_PROMPT.split("## ")[0].split("with consistent timestamp accuracy.\n\nQueue Length Scopes")[-1])
        
        with gr.Column(scale=1):
            # Video on the right
            video_output = gr.Video(
                label="Enriched video",
                width=640,   # set width in pixels
                height=360   # set height in pixels
            )
    
    gr.Markdown("## Analysis Result")

    # Dynamic textboxes block (keeps your original layout & headings)
    output_textboxes = {}  # dictionary to store Textbox components

    with gr.Column():
        # gr.Markdown("## Queue Length Analysis")
        # fetch keys from your prompt templates
        output_keys = PROMPT_TEMPLATES["queue_length"]["output_keys"]

        for key in output_keys:
            with gr.Group():
                # convert CamelCase or camelCase to spaced words for the heading
                heading = re.sub(r'(?<!^)(?=[A-Z])', ' ', key)
                gr.Markdown(f"### {heading}")
                output_textboxes[key] = gr.Textbox(
                    label=f"",
                    interactive=False,
                    lines=5,
                    autoscroll=True,
                    elem_id=f"queue_length_{key}"
                )

    # Return the components that will be updated by the backend
    return {
        "video_output": video_output,
        "text_outputs": output_textboxes
    }

def analyze_queue_length_video(video_path):
    """Analyze queue length video and return both JSON data and enriched video path"""
    print(video_path, type(video_path))
    enriched_video_path = video_enricher(video_path)
    video_path = enriched_video_path
    print("Enriched video path:", enriched_video_path)
    
    if not video_path:
        return None, None  # Return None for both outputs if no video path

    def _clean_json_string(text):
        if text.startswith("Error decoding JSON: "):
            text = text[len("Error decoding JSON: "):].strip()
        
        json_start = text.find("```json")
        json_end = text.rfind("```")
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            text = text[json_start + len("```json"):json_end].strip()
            
        return text

    full_response = ""
    for chunk in generate_content_existing(video_path, QUEUE_LENGTH_PROMPT, "queue_length"):
        full_response += chunk
    
    # Clean the full_response before attempting to parse JSON
    cleaned_response = _clean_json_string(full_response)

    try:
        json_data = json.loads(cleaned_response)
        print("Full JSON structure:", json.dumps(json_data, indent=2))
        
        # Find the main data section
        data = None
        possible_keys = ["QueueLength", "queue_length", "Queue", "QueueAnalysis", "analysis", "results"]
        
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
                        if "queue_length" in item:
                            parts.append(f"queue_length: {item['queue_length']}")
                        if "wait_time" in item:
                            parts.append(f"wait_time: '{item['wait_time']}'")
                        if "peak_time" in item:
                            parts.append(f"peak_time: '{item['peak_time']}'")
                        if "customer_count" in item:
                            parts.append(f"customer_count: {item['customer_count']}")
                        if parts:  # Only add if we have content
                            output_strings.append("\n".join(parts))
            
            # Use the exact category names as keys
            result[category_name] = "\n\n".join(output_strings) if output_strings else "No data found"
        
        print("Returning result with keys:", list(result.keys()))
        return result, enriched_video_path
        
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {cleaned_response}")
        return {"error": "Invalid JSON response from model.", "raw_response": cleaned_response}, enriched_video_path

# Legacy function for backward compatibility
def create_tab(video_player):
    """Legacy function - now redirects to create_ui()"""
    with gr.Blocks() as queue_length_tab:
        with gr.Row():
            analyze_button = gr.Button("Analyze Queue Length", variant="primary")
            # show final video here
            video_output = gr.Video(label="Enriched video") 

        gr.Markdown("## Queue Length Analysis")
        gr.Markdown(QUEUE_LENGTH_PROMPT)

        gr.Markdown("## Analysis Result")
        queue_length_json = gr.JSON(label="Queue Length JSON (parsed)")

        analyze_button.click(
            analyze_queue_length_video,
            inputs=[video_player],
            outputs=[queue_length_json, video_output],   # return (result_dict, enriched_video_path)
        )
    return queue_length_tab

# import gradio as gr
# import json
# from .prompts import QUEUE_LENGTH_PROMPT
# from model_utils.existing_generation import generate_content_existing
# from model_utils.new_generation import generate_content_new
# import pandas as pd
# from .prompt_templates import PROMPT_TEMPLATES
# import re

# def create_ui():
#     output_textboxes = {} # Dictionary to store the Textbox components

#     with gr.Column(): # Use a Column or Row to group elements within the tab
#         gr.Markdown("## Queue Length Analysis")

#         output_keys = PROMPT_TEMPLATES["queue_length"]["output_keys"]

#         for key in output_keys:
#             with gr.Group():
#                 gr.Markdown((f"### {re.sub(r'(?<!^)(?=[A-Z])', ' ', key)}"))
#                 output_textboxes[key] = gr.Textbox(label=f"Generated Output for {key.replace('_', ' ').title()}", interactive=False, lines=5, autoscroll=True, elem_id=f"queue_length_{key}")

#     return output_textboxes

# def analyze_queuelength_video(video_path):
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
#     for chunk in generate_content_existing(video_path, QUEUE_LENGTH_PROMPT, "queue_length"):
#         full_response += chunk
    
#     # Clean the full_response before attempting to parse JSON
#     cleaned_response = _clean_json_string(full_response)

#     try:
#         json_data = json.loads(cleaned_response)
#         print("Full JSON structure:", json.dumps(json_data, indent=2))
        
#         # Find the main data section
#         data = None
#         possible_keys = ["QueueLength", "queue_length", "Queue", "QueueAnalysis", "analysis", "results"]
        
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
#                         if "queue_length" in item:
#                             parts.append(f"queue_length: {item['queue_length']}")
#                         if "wait_time" in item:
#                             parts.append(f"wait_time: '{item['wait_time']}'")
#                         if "peak_time" in item:
#                             parts.append(f"peak_time: '{item['peak_time']}'")
#                         if "customer_count" in item:
#                             parts.append(f"customer_count: {item['customer_count']}")
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
#     with gr.Blocks() as queue_length_tab:
#         with gr.Row():
#             analyze_button = gr.Button("Analyze Queue Length", variant="primary")
        
#         gr.Markdown("## Queue Length Analysis Scopes")
#         gr.Markdown(QUEUE_LENGTH_PROMPT) # Display the fixed prompt content

#         gr.Markdown("## Analysis Result")
#         with gr.Box():
#             # This will hold the structured UI from queue_length_ui.py
#             queue_length_output_display = gr.Blocks() # Use gr.Blocks to hold the dynamic UI

#         analyze_button.click(
#             analyze_queuelength_video,
#             inputs=[video_player],
#             outputs=queue_length_output_display,
#             postprocess=create_ui # Pass the parsed JSON to create_ui
#         )
#     return queue_length_tab