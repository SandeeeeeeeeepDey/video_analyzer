# app.py
import gradio as gr
import importlib
import os
import shutil
import logging
import torch
from functools import partial

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

                        print("json_data", json_data, type(json_data))
                        print("key", key)
                        
                        if key in json_data:
                            updates.append(gr.update(value=str(json_data[key])))
                            print("single", json_data[key])
                            print("if", updates)
                            print(updates[0].values())
                            updates 
                        else:
                            updates.append(gr.update(value=str(json_data)))
                            print("else", updates.values())
                    else: # For multi-component modules
                        for key, comp in output_components.items():
                            if key in json_data:
                                updates.append(gr.update(value=str(json_data[key])))
                            else:
                                updates.append(gr.update(value=f"Key '{key}' not found."))
                        print("multi", updates)
                else:
                    err_msg = f"Analysis function '{analyze_func_name}' not found."
                    updates = [gr.update(value=err_msg) for _ in component_list]

            except Exception as e:
                err_msg = f"Error analyzing {module_name}: {e}"
                print(err_msg)
                updates = [gr.update(value=err_msg) for _ in component_list]
            
            # print("Tuple check", list(tuple(updates).values()))

            return tuple(updates)


        with gr.Row():
            with gr.Column(scale=1, min_width=300, visible=True) as left_panel:
                with gr.Accordion("Video Library", open=True):
                    video_files = gr.File(file_count="multiple", label="Upload Videos")
                    initial_video_dropdown_value = get_video_files()[0] if get_video_files() else None
                    video_dropdown = gr.Dropdown(label="Select a video", choices=get_video_files(), value=initial_video_dropdown_value)

                selected_video_display = gr.Textbox(label="Selected Video", interactive=False, value=initial_video_dropdown_value)
                initial_video_player_value = os.path.join(UPLOADS_DIR, get_video_files()[0]) if get_video_files() else None
                video_player = gr.Video(label="Video Player", value=initial_video_player_value)

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
                                # Face recognition special case (you already had this)
                                if module_name == "face_recognition":
                                    module = importlib.import_module(f"analytics.{module_name}")
                                    output_comp = module.create_tab()
                                    output_textboxes_for_tab = {"output": output_comp}
                                    all_output_textboxes[f"{module_name}_output"] = output_comp
                                # Add this case in your tab creation loop, after the queue_length case:

                                elif module_name == "following_cooking_steps":
                                        analytics_module = importlib.import_module("analytics.following_cooking_steps")
                                        analytics_module.create_tab(video_player)
                                        continue
                                    # analytics_module = importlib.import_module("analytics.following_cooking_steps")
                                    
                                    # # Create the UI components directly in the tab
                                    # with gr.Column():
                                    #     # Add SOP input textbox at the top
                                        
                                        
                                    #     # Create the output textboxes using the module's create_ui function
                                    #     following_cooking_steps_ui = analytics_module.create_ui()

                                    # # Capture the analyzer function now (avoid late binding)
                                    # analyzer = getattr(analytics_module, "analyze_followingcookingsteps_video", None)
                                    # if analyzer is None:
                                    #     # try a couple of plausible alternate names
                                    #     for alt in ("analyze", "analyze_video", "process_video", "run"):
                                    #         analyzer = getattr(analytics_module, alt, None)
                                    #         if analyzer:
                                    #             break
                                    # if analyzer is None:
                                    #     available = [n for n in dir(analytics_module) if not n.startswith("_")]
                                    #     raise AttributeError(
                                    #         "No analyzer found in analytics.following_cooking_steps. Expected 'analyze_followingcookingsteps_video' or similar. "
                                    #         f"Available: {available}"
                                    #     )

                                    # # register textboxes globally
                                    # for key, comp in following_cooking_steps_ui.items():
                                    #     all_output_textboxes[f"{module_name}_{key}"] = comp

                                    # # keep local reference so later generic code won't try to create another Analyze button
                                    # output_textboxes_for_tab = following_cooking_steps_ui

                                    # # prepare outputs in exact order the handler will return them
                                    # outputs_list = list(following_cooking_steps_ui.values())

                                    # # handler closes over analyzer (a concrete function object)
                                    # def following_cooking_steps_handler(video_path, sop_input, ui_components=following_cooking_steps_ui, analyzer=analyzer):
                                    #     if not video_path:
                                    #         empty_texts = [""] * len(ui_components)
                                    #         return empty_texts

                                    #     # call the captured analyzer with SOP input
                                    #     result_data = analyzer(video_path, sop_input)

                                    #     # prepare textbox values in same order as ui_components.keys()
                                    #     text_values = []
                                    #     for key in ui_components.keys():
                                    #         if isinstance(result_data, dict):
                                    #             val = result_data.get(key, "")
                                    #         else:
                                    #             val = ""
                                    #         text_values.append("" if val is None else str(val))

                                    #     return text_values

                                    # # Bind the analyze button
                                    # local_analyze_button.click(
                                    #     fn=following_cooking_steps_handler, 
                                    #     inputs=[video_player, sop_textbox],  # Include SOP textbox as input
                                    #     outputs=outputs_list
                                    # )

                                    # # skip the generic Analyze button creation below for this tab
                                    # continue
                                # Occupancy special case (fixed)
                                elif module_name == "occupancy":
                                    analytics_module = importlib.import_module("analytics.occupancy")
                                    occupancy_ui = analytics_module.create_ui()  # dict: json_output, video_output, text_outputs(dict)

                                    # Capture the analyzer function now (avoid late binding)
                                    analyzer = getattr(analytics_module, "analyze_occupancy_video", None)
                                    if analyzer is None:
                                        # try a couple of plausible alternate names
                                        for alt in ("analyze", "analyze_video", "process_video", "run"):
                                            analyzer = getattr(analytics_module, alt, None)
                                            if analyzer:
                                                break
                                    if analyzer is None:
                                        available = [n for n in dir(analytics_module) if not n.startswith("_")]
                                        raise AttributeError(
                                            "No analyzer found in analytics.occupancy. Expected 'analyze_occupancy_video' or similar. "
                                            f"Available: {available}"
                                        )

                                    # attach the concrete function (optional convenience)
                                    occupancy_ui["analyze_fn"] = analyzer

                                    # register textboxes globally
                                    for key, comp in occupancy_ui["text_outputs"].items():
                                        all_output_textboxes[f"{module_name}_{key}"] = comp

                                    # keep local reference so later generic code won't try to create another Analyze button
                                    output_textboxes_for_tab = occupancy_ui["text_outputs"]

                                    # prepare outputs in exact order the handler will return them
                                    outputs_list = [occupancy_ui["video_output"]] + list(occupancy_ui["text_outputs"].values())# [occupancy_ui["json_output"], occupancy_ui["video_output"]] + list(occupancy_ui["text_outputs"].values())

                                    # handler closes over analyzer (a concrete function object)
                                    def occupancy_handler(video_path, ui_components=occupancy_ui, analyzer=analyzer):
                                        if not video_path:
                                            empty_texts = [""] * len(ui_components["text_outputs"])
                                            return None, *empty_texts

                                        # call the captured analyzer
                                        json_data, enriched_video_path = analyzer(video_path)

                                        # prepare textbox values in same order as ui_components["text_outputs"].keys()
                                        text_values = []
                                        for key in ui_components["text_outputs"].keys():
                                            if isinstance(json_data, dict):
                                                val = json_data.get(key, "")
                                            else:
                                                val = ""
                                            text_values.append("" if val is None else str(val))

                                        return enriched_video_path, *text_values

                                    # create and bind the analyze button (only once for occupancy)
                                    local_analyze_button = gr.Button("Analyze", variant="secondary")
                                    local_analyze_button.click(fn=occupancy_handler, inputs=[video_player], outputs=outputs_list)

                                    # skip the generic Analyze button creation below for this tab
                                    continue

                                # Default case: module provides its own UI function
                                # Queue Length special case (exactly like occupancy)
                                elif module_name == "queue_length":
                                    analytics_module = importlib.import_module("analytics.queue_length")
                                    queue_length_ui = analytics_module.create_ui()  # dict: video_output, text_outputs(dict)

                                    # Capture the analyzer function now (avoid late binding)
                                    analyzer = getattr(analytics_module, "analyze_queue_length_video", None)
                                    if analyzer is None:
                                        # try a couple of plausible alternate names
                                        for alt in ("analyze", "analyze_video", "process_video", "run"):
                                            analyzer = getattr(analytics_module, alt, None)
                                            if analyzer:
                                                break
                                    if analyzer is None:
                                        available = [n for n in dir(analytics_module) if not n.startswith("_")]
                                        raise AttributeError(
                                            "No analyzer found in analytics.queue_length. Expected 'analyze_queue_length_video' or similar. "
                                            f"Available: {available}"
                                        )

                                    # attach the concrete function (optional convenience)
                                    queue_length_ui["analyze_fn"] = analyzer

                                    # register textboxes globally
                                    for key, comp in queue_length_ui["text_outputs"].items():
                                        all_output_textboxes[f"{module_name}_{key}"] = comp

                                    # keep local reference so later generic code won't try to create another Analyze button
                                    output_textboxes_for_tab = queue_length_ui["text_outputs"]

                                    # prepare outputs in exact order the handler will return them
                                    outputs_list = [queue_length_ui["video_output"]] + list(queue_length_ui["text_outputs"].values())

                                    # handler closes over analyzer (a concrete function object)
                                    def queue_length_handler(video_path, ui_components=queue_length_ui, analyzer=analyzer):
                                        if not video_path:
                                            empty_texts = [""] * len(ui_components["text_outputs"])
                                            return None, *empty_texts

                                        # call the captured analyzer
                                        json_data, enriched_video_path = analyzer(video_path)

                                        # prepare textbox values in same order as ui_components["text_outputs"].keys()
                                        text_values = []
                                        for key in ui_components["text_outputs"].keys():
                                            if isinstance(json_data, dict):
                                                val = json_data.get(key, "")
                                            else:
                                                val = ""
                                            text_values.append("" if val is None else str(val))

                                        return enriched_video_path, *text_values

                                    # create and bind the analyze button (only once for queue_length)
                                    local_analyze_button = gr.Button("Analyze", variant="secondary")
                                    local_analyze_button.click(fn=queue_length_handler, inputs=[video_player], outputs=outputs_list)

                                    # skip the generic Analyze button creation below for this tab
                                    continue
                                else:
                                    analytics_module = importlib.import_module(f"analytics.{module_name}")
                                    output_textboxes_for_tab = analytics_module.create_ui()
                                    # register returned components
                                    # print(tab_name, "************")
                                    for key, textbox_comp in output_textboxes_for_tab.items():
                                        # print("type",type(textbox_comp), "iwbdf", textbox_comp)
                                        all_output_textboxes[f"{module_name}_{key}"] = textbox_comp
                                if module_name == "face_recognition":
                                    continue
                                else:
                                    # Generic Analyze button for modules that returned simple textboxes dict
                                    local_analyze_button = gr.Button("Analyze", variant="secondary")
                                    # Capture loop variables into lambda defaults to avoid late-binding there as well
                                    local_analyze_button.click(
                                        fn=lambda vp, mn=module_name, comps=output_textboxes_for_tab: run_local_analysis(vp, mn, comps),
                                        inputs=[video_player],
                                        outputs=list(output_textboxes_for_tab.values())
                                    )

                            except (ImportError, AttributeError) as e:
                                gr.Markdown(f"Error loading module for {tab_name}: {e}")




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