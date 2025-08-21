import google.generativeai as genai
from google.genai import types
import time
from secret import GEMINI_API_KEY
from config import config
import logging

def _normalize_state(file_status):
    state = None
    if isinstance(file_status, dict):
        state = file_status.get("state") or file_status.get("status")
    else:
        state = getattr(file_status, "state", None) or getattr(file_status, "status", None)

    if isinstance(state, (int,)):
        return state
    if isinstance(state, str):
        s = state.strip().upper()
        try:
            return int(s)
        except Exception:
            return s
    return repr(state)

def wait_for_file_active(file_obj, gemini_api_key=None, timeout=60, poll_interval=2):
    start = time.time()
    last_state = None

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
        logging.debug("Warning: couldn't find file identifier. Inspecting file_obj: %s", file_obj)

    while time.time() - start < timeout:
        try:
            file_status = None
            if fid and hasattr(genai, "get_file"):
                try:
                    file_status = genai.get_file(fid)
                except Exception as e:
                    logging.debug("Error getting file status: %s. Falling back to original file_obj.", e)
                    file_status = file_obj
            else:
                file_status = file_obj

            norm = _normalize_state(file_status)
            last_state = norm
            logging.debug("DEBUG file state: %s (type: %s)", norm, type(norm).__name__)

            if norm == "ACTIVE" or norm == 2 or norm == "2":
                return file_status

        except Exception as e:
            logging.error("Error while checking file state: %s", e)

        time.sleep(poll_interval)

    raise RuntimeError(f"Timed out waiting for file to become ACTIVE. Last observed state: {last_state}")

def upload_to_gemini(path, mime_type=None):
    logging.debug("Configuring genai with API key and endpoint.")
    genai.configure(api_key=GEMINI_API_KEY, transport="rest", client_options={"api_endpoint": "generativelanguage.googleapis.com"})
    logging.debug("Uploading file: %s with mime_type: %s", path, mime_type)
    file = genai.upload_file(path, mime_type=mime_type)
    logging.debug("Uploaded file '%s' as: %s", file.display_name, file.uri)
    return file

def generate_content_existing(video_path, prompt):
    logging.debug("Starting generate_content_existing for video: %s with prompt: %s", video_path, prompt)
    if not video_path:
        logging.warning("No video path provided to generate_content_existing.")
        return "Please upload a video to analyze."

    video_file = upload_to_gemini(video_path, mime_type="video/mp4")
    try:
        active_file = wait_for_file_active(video_file, GEMINI_API_KEY, timeout=90, poll_interval=2)
        logging.debug("File became active: %s", active_file.uri)
    except RuntimeError as e:
        logging.error("File upload failed or timed out: %s", e)
        return f"Upload processed but never became ACTIVE: {e}"

    model = genai.GenerativeModel(model_name="gemini-2.5-flash", generation_config=config)
    logging.debug("Generating content with model: %s", model.model_name)
    response = model.generate_content([prompt, active_file])
    response_text = getattr(response, "text", str(response))
    logging.debug("Raw model response: %s", response_text)
    return response_text
