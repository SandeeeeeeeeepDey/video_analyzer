import gradio as gr
import importlib
import os
import shutil
import logging
import torch

# Set logging levels for various libraries to reduce verbosity
logging.getLogger('tensorflow').setLevel(logging.ERROR)
logging.getLogger('gradio').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('google.generativeai').setLevel(logging.WARNING)

# --- Local Storage Configuration ---
UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Correctly determine DATA_DIR relative to the script's location
try:
    script_dir = os.path.dirname(__file__)
except NameError:  # __file__ is not defined in some environments (e.g., notebooks)
    script_dir = os.getcwd()
DATA_DIR = os.path.join(script_dir, "data")
os.makedirs(DATA_DIR, exist_ok=True)

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Torch device: {torch.device('cuda' if torch.cuda.is_available() else 'cpu')}")

def get_video_files():
    return [f for f in os.listdir(UPLOADS_DIR) if f.endswith(('.mp4', '.avi', '.mov'))]

def copy_project_videos_to_uploads():
    # Correctly reference the script's directory for source files
    source_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else '.'
    for file in os.listdir(source_dir):
        if file.endswith(('.mp4', '.avi', '.mov')):
            dest_path = os.path.join(UPLOADS_DIR, file)
            if not os.path.exists(dest_path):
                shutil.copy(os.path.join(source_dir, file), dest_path)

# --- Gradio UI ---
def create_ui():
    copy_project_videos_to_uploads()  # Copy videos on startup

    with gr.Blocks(theme='earneleh/paris') as demo:
        # To store the full paths of the uploaded files
        initial_videos = [os.path.join(UPLOADS_DIR, f) for f in get_video_files()]
        uploaded_file_paths = gr.State(initial_videos)

        # ---- Analysis Functions ----

        # This function runs analysis for a SINGLE module (for the local buttons)
        def run_local_analysis(video_path, module_name, output_components):
            """
            Runs analysis for a single module and returns updates for its components.
            output_components is a dictionary of {key: component}.
            """
            updates = []
            component_list = list(output_components.values())
            try:
                if not video_path:
                    err_msg = "Please select a video first."
                    return [gr.update(value=err_msg) for _ in component_list]

                analytics_module = importlib.import_module(f"analytics.{module_name}")
                analyze_func_name = f"analyze_{module_name.replace('_', '')}_video"

                if hasattr(analytics_module, analyze_func_name):
                    json_data = getattr(analytics_module, analyze_func_name)(video_path)
                    
                    # Special case for single-component modules like face_recognition
                    if len(output_components) == 1:
                        key = list(output_components.keys())[0]
                        # If analysis returns a dict, try to find the key, otherwise use the whole result
                        if isinstance(json_data, dict) and key in json_data:
                            updates.append(gr.update(value=str(json_data[key])))
                        else:
                            updates.append(gr.update(value=str(json_data)))
                    else: # For multi-component modules
                        for key, comp in output_components.items():
                            if key in json_data:
                                updates.append(gr.update(value=str(json_data[key])))
                            else:
                                updates.append(gr.update(value=f"Key '{key}' not found."))
                else:
                    err_msg = f"Analysis function '{analyze_func_name}' not found."
                    updates = [gr.update(value=err_msg) for _ in component_list]

            except Exception as e:
                err_msg = f"Error analyzing {module_name}: {e}"
                print(err_msg)
                updates = [gr.update(value=err_msg) for _ in component_list]

            return tuple(updates)

        # This function runs analysis for ALL modules (for the main button)
        def run_all_analysis(video_path, all_outputs_dict):
            updates = {} # Use a dictionary to store updates with keys
            
            if not video_path:
                return tuple([gr.update(value="Please select a video first.") for _ in all_outputs_dict.values()])

            for module_name_key, textbox_comp in all_outputs_dict.items():
                # Skip face recognition as per original logic
                if "face_recognition" in module_name_key:
                    updates[module_name_key] = gr.update(value="Skipped by Analyze All.")
                    continue
                    
                try:
                    # Reconstruct module name and output key
                    parts = module_name_key.split('_', 1)
                    module_name = parts[0]
                    output_key = parts[1] if len(parts) > 1 else None
                    
                    analytics_module = importlib.import_module(f"analytics.{module_name}")
                    analyze_func_name = f"analyze_{module_name.replace('_', '')}_video"

                    if hasattr(analytics_module, analyze_func_name):
                        json_data = getattr(analytics_module, analyze_func_name)(video_path)
                        
                        # Check for single-component vs. multi-component
                        if output_key and isinstance(json_data, dict):
                            if output_key in json_data:
                                updates[module_name_key] = gr.update(value=str(json_data[output_key]))
                            else:
                                updates[module_name_key] = gr.update(value=f"Key '{output_key}' not found.")
                        else:
                            # Single component or key wasn't specified
                            updates[module_name_key] = gr.update(value=str(json_data))
                    else:
                        updates[module_name_key] = gr.update(value=f"Analysis function not found.")
                except Exception as e:
                    print(f"Error analyzing {module_name_key}: {e}")
                    updates[module_name_key] = gr.update(value=f"Error: {e}")
            
            # Return updates in the correct order based on the keys of all_outputs_dict
            ordered_updates = [updates[key] for key in all_outputs_dict.keys()]
            return tuple(ordered_updates)

        with gr.Row():
            with gr.Column(scale=1, min_width=300, visible=True) as left_panel:
                with gr.Accordion("Video Library", open=True):
                    video_files = gr.File(file_count="multiple", label="Upload Videos")
                    initial_video_dropdown_value = get_video_files()[0] if get_video_files() else None
                    video_dropdown = gr.Dropdown(label="Select a video", choices=get_video_files(), value=initial_video_dropdown_value)

                selected_video_display = gr.Textbox(label="Selected Video", interactive=False, value=initial_video_dropdown_value)
                initial_video_player_value = os.path.join(UPLOADS_DIR, get_video_files()[0]) if get_video_files() else None
                video_player = gr.Video(label="Video Player", value=initial_video_player_value)

                # --- CHANGE 1: Analyze All button is now in the left panel ---
                # analyze_all_button = gr.Button("Analyze All (Except Face Recognition)", variant="primary")

            with gr.Column(scale=4) as right_panel:
                # --- CHANGE 2: Collapse button is now in the right panel and small ---
                toggle_button = gr.Button("<<", size="sm")

                with gr.Tabs() as tabs:
                    tab_names = [
                        "Face Recognition", "Customer Behaviour", "Staff Behaviour", "Hygiene",
                        "Safety", "Time Monitering", "Customer Requirements",
                        "Following Cooking Steps", "Occupancy", "Queue Length", "Operational Efficiency"
                    ]
                    all_output_textboxes = {}

                    for tab_name in tab_names:
                        with gr.Tab(tab_name):
                            output_textboxes_for_tab = {}
                            module_name = tab_name.lower().replace(" ", "_")
                            try:
                                if module_name == "face_recognition":
                                    module = importlib.import_module(f"analytics.{module_name}")
                                    output_comp = module.create_tab()
                                    # Standardize to a dictionary for consistent handling
                                    output_textboxes_for_tab = {"output": output_comp}
                                    all_output_textboxes[f"{module_name}_output"] = output_comp
                                else:
                                    # Now UI creation is within the analytics module itself
                                    print(f"analytics.{module_name}")
                                    analytics_module = importlib.import_module(f"analytics.{module_name}")
                                    print("analytics_module", analytics_module)
                                    output_textboxes_for_tab = analytics_module.create_ui()
                                    print("output_textboxes_for_tab", output_textboxes_for_tab)
                                    for key, textbox_comp in output_textboxes_for_tab.items():
                                        
                                        all_output_textboxes[f"{module_name}_{key}"] = textbox_comp

                                # --- CHANGE 3: Add a local "Analyze" button to the bottom of each tab ---
                                local_analyze_button = gr.Button("Analyze", variant="secondary")

                                # Use a lambda with default arguments to capture loop variables correctly
                                local_analyze_button.click(
                                    fn=lambda vp, mn=module_name, comps=output_textboxes_for_tab: run_local_analysis(vp, mn, comps),
                                    inputs=[video_player],
                                    outputs=list(output_textboxes_for_tab.values())
                                )

                            except (ImportError, AttributeError) as e:
                                gr.Markdown(f"Error loading module for {tab_name}: {e}")

        # --- Event Handlers ---

        # # "Analyze All" button wiring
        # analyze_all_button.click(
        #     fn=lambda vp: run_all_analysis(vp, all_output_textboxes),
        #     inputs=[video_player],
        #     outputs=list(all_output_textboxes.values())
        # )

        # File handling and UI interaction wiring
        def update_video_list_and_upload(files, current_paths):
            if files:
                new_paths = current_paths
                for file in files:
                    filename = os.path.basename(file.name)
                    dest_path = os.path.join(UPLOADS_DIR, filename)
                    shutil.copy(file.name, dest_path)
                    if hasattr(file, 'name') and os.path.exists(file.name):
                         os.remove(file.name) # clean up temp file if it exists
                    if dest_path not in new_paths:
                        new_paths.append(dest_path)
                filenames = sorted([os.path.basename(p) for p in new_paths])
                return gr.update(choices=filenames), new_paths
            return gr.update(), current_paths

        def play_video(selected_filename, all_paths):
            if selected_filename:
                for path in all_paths:
                    if os.path.basename(path) == selected_filename:
                        return gr.update(value=path), gr.update(value=selected_filename)
            return gr.update(value=None), gr.update(value=None)

        def toggle_left_panel(is_visible):
            is_visible = not is_visible
            return gr.update(visible=is_visible), gr.update(value=">>" if not is_visible else "<<"), is_visible

        video_files.upload(update_video_list_and_upload, inputs=[video_files, uploaded_file_paths], outputs=[video_dropdown, uploaded_file_paths])
        video_dropdown.change(play_video, inputs=[video_dropdown, uploaded_file_paths], outputs=[video_player, selected_video_display])

        left_panel_visible = gr.State(True)
        toggle_button.click(toggle_left_panel, inputs=[left_panel_visible], outputs=[left_panel, toggle_button, left_panel_visible])

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch()