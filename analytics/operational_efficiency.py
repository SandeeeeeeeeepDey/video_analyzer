import gradio as gr
import os
from google.genai import types
# from google import genai
import google.generativeai as genai
from .prompts import OPERATIONAL_EFFICIENCY_PROMPT
import time
from secret import GEMINI_API_KEY
from config import config

def _normalize_state(file_status):
    """Return a normalized state value that's easy to compare."""
    # try dict-like first
    state = None
    if isinstance(file_status, dict):
        state = file_status.get("state") or file_status.get("status")
    else:
        # try attributes
        state = getattr(file_status, "state", None) or getattr(file_status, "status", None)

    # If it's bytes-like or proto enum, try to convert to int
    if isinstance(state, (int,)):
        return state
    if isinstance(state, str):
        # strip and uppercase for safety
        s = state.strip().upper()
        # try numeric string -> int
        try:
            return int(s)
        except Exception:
            return s
    # fallback: return repr
    return repr(state)

def wait_for_file_active(file_obj, gemini_api_key=None, timeout=60, poll_interval=2):
    """Poll until file is ACTIVE. Accepts string 'ACTIVE' or numeric enum 2.
    Returns final file_status object when active, else raises RuntimeError.
    """
    start = time.time()
    last_state = None

    # get an identifier used by genai.get_file
    fid = None
    if hasattr(file_obj, "name"):
        fid = getattr(file_obj, "name")
    elif isinstance(file_obj, dict) and "name" in file_obj:
        fid = file_obj["name"]
    elif hasattr(file_obj, "resource_name"):
        fid = getattr(file_obj, "resource_name")
    elif hasattr(file_obj, "uri"):
        fid = getattr(file_obj, "uri")

    if not fid:
        # we still can continue, but print file_obj for debugging
        print("Warning: couldn't find file identifier. Inspecting file_obj:", file_obj)

    while time.time() - start < timeout:
        try:
            # Prefer genai.get_file if available
            file_status = None
            if fid and hasattr(genai, "get_file"):
                try:
                    file_status = genai.get_file(fid)
                except Exception as e:
                    # some clients expect the resource name without 'files/' etc.
                    # If get_file fails, fall back to using the original object
                    file_status = file_obj
            else:
                file_status = file_obj

            norm = _normalize_state(file_status)
            last_state = norm
            # DEBUG: show exactly what we got (type + value)
            print("DEBUG file state:", norm, " (type:", type(norm).__name__, ")")

            # Accept either string "ACTIVE" or numeric 2
            if norm == "ACTIVE" or norm == 2 or norm == "2":
                return file_status

        except Exception as e:
            print("Error while checking file state:", e)

        time.sleep(poll_interval)

    raise RuntimeError(f"Timed out waiting for file to become ACTIVE. Last observed state: {last_state}")

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini.

    See https://ai.google.dev/gemini-api/docs/prompting_with_media
    """
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def analyze_operational_efficiency_video(video_path):
    genai.configure(api_key=GEMINI_API_KEY, transport="rest", client_options={"api_endpoint": "generativelanguage.googleapis.com"})

    video_file = upload_to_gemini(video_path, mime_type="video/mp4")
    # wait (but this will immediately return if already ACTIVE)
    try:
        active_file = wait_for_file_active(video_file, GEMINI_API_KEY, timeout=90, poll_interval=2)
    except RuntimeError as e:
        return f"Upload processed but never became ACTIVE: {e}"

    # now safe to call the model

    model = genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=config)
    # response = model.generate_content(
    #     contents=[
    #             types.Part(
    #                 file_data=types.FileData(file_uri=active_file.uri),
    #                 video_metadata=types.VideoMetadata(fps=2)
    #             ),
    #             types.Part(text=OPERATIONAL_EFFICIENCY_PROMPT)
    #         ]
    #     )
    response = model.generate_content([OPERATIONAL_EFFICIENCY_PROMPT, active_file])
    return getattr(response, "text", str(response))

def create_tab(video_player):
    with gr.Blocks() as operational_efficiency_tab:
        gr.Markdown("## Operational Efficiency Analysis")
        
        with gr.Row():
            analysis_output = gr.Textbox(label="Analysis Result", interactive=False, scale=2)

        
        
        analyze_button = gr.Button("Analyze Operational Efficiency")

        analyze_button.click(
            analyze_operational_efficiency_video,
            inputs=[video_player],
            outputs=analysis_output
        )
    return operational_efficiency_tab