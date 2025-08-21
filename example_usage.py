import gradio as gr
from model_utils.new_generation import generate_content_new
from model_utils.existing_generation import generate_content_existing
from analytics.prompts import SAFETY_PROMPT, TIME_MONITORING_PROMPT # Example prompts

# --- 1. New Generation (hardcoded FPS) ---
def new_generation_demo(video_path, prompt):
    if not video_path:
        return "Please upload a video."
    # Hardcode FPS to 2 as per user's request
    for chunk in generate_content_new(video_path, prompt, 2):
        yield chunk

with gr.Blocks() as new_gen_app:
    gr.Markdown("# New Generation Demo (FPS hardcoded to 2)")
    with gr.Row():
        video_input = gr.Video(label="Upload Video")
        text_prompt = gr.Textbox(label="Prompt", value=SAFETY_PROMPT)
    output_text = gr.Textbox(label="Generated Content", interactive=False)
    analyze_btn = gr.Button("Analyze Video")
    analyze_btn.click(
        new_generation_demo,
        inputs=[video_input, text_prompt],
        outputs=output_text
    )

# --- 2. Existing Generation ---
def existing_generation_demo(video_path, prompt):
    if not video_path:
        return "Please upload a video."
    return generate_content_existing(video_path, prompt)

with gr.Blocks() as existing_gen_app:
    gr.Markdown("# Existing Generation Demo")
    with gr.Row():
        video_input = gr.Video(label="Upload Video")
        text_prompt = gr.Textbox(label="Prompt", value=TIME_MONITORING_PROMPT)
    output_text = gr.Textbox(label="Generated Content", interactive=False)
    analyze_btn = gr.Button("Analyze Video")
    analyze_btn.click(
        existing_generation_demo,
        inputs=[video_input, text_prompt],
        outputs=output_text
    )

# --- 3. Combined Gradio App ---
def combined_analysis(video_path, prompt, analysis_type):
    if not video_path:
        return "Please upload a video."
    
    if analysis_type == "New Generation (FPS=2)":
        for chunk in generate_content_new(video_path, prompt, 2):
            yield chunk
    elif analysis_type == "Existing Generation":
        yield generate_content_existing(video_path, prompt)

with gr.Blocks() as combined_app:
    gr.Markdown("# Combined Analysis App")
    with gr.Row():
        video_input = gr.Video(label="Upload Video")
        text_prompt = gr.Textbox(label="Prompt", value=SAFETY_PROMPT)
        analysis_type_dropdown = gr.Dropdown(
            choices=["New Generation (FPS=2)", "Existing Generation"],
            label="Analysis Type",
            value="New Generation (FPS=2)"
        )
    output_text = gr.Textbox(label="Generated Content", interactive=False)
    analyze_btn = gr.Button("Run Analysis")
    analyze_btn.click(
        combined_analysis,
        inputs=[video_input, text_prompt, analysis_type_dropdown],
        outputs=output_text
    )

if __name__ == "__main__":
    print("Launching New Generation Demo...")
    new_gen_app.launch(share=True)
    print("Launching Existing Generation Demo...")
    existing_gen_app.launch(share=True)
    print("Launching Combined Analysis App...")
    combined_app.launch(share=True)
