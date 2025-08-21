import os
import base64
import google.genai as genai
from google.genai import types
from secret import GEMINI_API_KEY
import subprocess
from config import config



def generate_content_new(video_path, prompt, fps):
    client = genai.Client(
        api_key=GEMINI_API_KEY,
    )

    model = "gemini-2.5-pro"

    # Load video bytes from given path
    # video_bytes = subprocess.check_output(["python", "../video_byte_converter.py", video_path])
    with open(video_path, "rb") as f:
        video_bytes = f.read()
    

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                inline_data=types.Blob(
                    mime_type="video/mp4",
                    data=video_bytes
                ),
                video_metadata=types.VideoMetadata(fps=fps),
            ),
                types.Part.from_text(text=prompt),
            ],
        ),
    ]

    # generate_content_config = types.GenerateContentConfig(
    #     thinking_config=types.ThinkingConfig(thinking_budget=-1),
    # )

    # Stream responses
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    ):
        if chunk.text:
            yield chunk.text


