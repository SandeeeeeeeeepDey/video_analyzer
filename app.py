import gradio as gr
import importlib
import os
import shutil

import torch

# --- Local Storage Configuration ---
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Torch device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")

def get_video_files():
    return [f for f in os.listdir(UPLOADS_DIR) if f.endswith(('.mp4', '.avi', '.mov'))]

def copy_project_videos_to_uploads():
    for file in os.listdir('.'):
        if file.endswith(('.mp4', '.avi', '.mov')):
            dest_path = os.path.join(UPLOADS_DIR, file)
            if not os.path.exists(dest_path):
                shutil.copy(file, dest_path)

# --- Gradio UI ---
def create_ui():
    copy_project_videos_to_uploads()  # Copy videos on startup
    
    with gr.Blocks(theme='earneleh/paris') as demo:
        # To store the full paths of the uploaded files
        initial_videos = [os.path.join(UPLOADS_DIR, f) for f in get_video_files()]
        uploaded_file_paths = gr.State(initial_videos)

        with gr.Row():
            with gr.Column(scale=1, min_width=300, visible=True) as left_panel:
                with gr.Accordion("Video Library", open=True):
                    video_files = gr.File(file_count="multiple", label="Upload Videos")
                    initial_video_dropdown_value = get_video_files()[0] if get_video_files() else None
                    video_dropdown = gr.Dropdown(label="Select a video", choices=get_video_files(), value=initial_video_dropdown_value)

                selected_video_display = gr.Textbox(label="Selected Video", interactive=False, value=initial_video_dropdown_value)
                initial_video_player_value = os.path.join(UPLOADS_DIR, get_video_files()[0]) if get_video_files() else None
                video_player = gr.Video(label="Video Player", value=initial_video_player_value)

                analyze_button = gr.Button("Analyze", variant="secondary")
            
            with gr.Column(scale=0, min_width=25):
                toggle_button = gr.Button("<<")

            with gr.Column(scale=4) as right_panel:
                with gr.Tabs() as tabs:
                    tab_names = [
                        "Face Recognition", "People Behaviour", "Staff Behaviour", "Hygiene",
                        "Safety", "Time Monitering", "Customer Requirements",
                        "Following Cooking Steps", "Occupancy", "Queue Length", "Operational Efficiency"
                    ]
                    for tab_name in tab_names:
                        with gr.Tab(tab_name):
                            module_name = tab_name.lower().replace(" ", "_")
                            try:
                                module = importlib.import_module(f"analytics.{module_name}")
                                # Pass analyze_button and video_player to create_tab
                                if tab_name == "Face Recognition":
                                    module.create_tab(analyze_button, video_player)
                                else:
                                    module.create_tab(video_player)
                            except (ImportError, AttributeError) as e:
                                gr.Markdown(f"Error loading module for {tab_name}: {e}")

        def update_video_list_and_upload(files, current_paths):
            if files:
                new_paths = current_paths
                for file in files:
                    filename = os.path.basename(file.name)
                    dest_path = os.path.join(UPLOADS_DIR, filename)
                    shutil.move(file.name, dest_path)
                    if dest_path not in new_paths:
                        new_paths.append(dest_path)
                
                filenames = [os.path.basename(p) for p in new_paths]
                return gr.update(choices=filenames), new_paths
            return gr.update(), current_paths

        def play_video(selected_filename, all_paths):
            for path in all_paths:
                if os.path.basename(path) == selected_filename:
                    return gr.update(value=path), gr.update(variant="primary"), gr.update(value=selected_filename)
            return gr.update(), gr.update(), gr.update()

        def toggle_left_panel(is_visible):
            is_visible = not is_visible
            return gr.update(visible=is_visible), gr.update(value=">>" if not is_visible else "<<"), is_visible

        video_files.upload(update_video_list_and_upload, inputs=[video_files, uploaded_file_paths], outputs=[video_dropdown, uploaded_file_paths])
        
        video_dropdown.change(play_video, inputs=[video_dropdown, uploaded_file_paths], outputs=[video_player, analyze_button, selected_video_display])

        left_panel_visible = gr.State(True)
        toggle_button.click(toggle_left_panel, inputs=[left_panel_visible], outputs=[left_panel, toggle_button, left_panel_visible])

    return demo

if __name__ == "__main__":
    demo = create_ui()
    demo.launch()