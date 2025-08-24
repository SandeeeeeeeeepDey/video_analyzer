# analytics/face_recognition.py
import os
from uuid import uuid4
from typing import Any, Dict, List, Optional

import gradio as gr
import chromadb
from PIL import Image
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1
from mtcnn import MTCNN
import cv2
import re

# --- Configuration ---
EMBEDDING_MODEL = "FaceNet"
DETECTOR_BACKEND = "mtcnn"
IMAGE_SIZE = (160, 160)
# Correctly define the path relative to this script's location
VECTOR_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "face_vector_db")
IDENTITY_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registered_faces")

# --- Device & Model Initialization ---
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Running on device: {device}")

# InceptionResnetV1 from facenet-pytorch outputs 512-d vectors
identity_detector = InceptionResnetV1(pretrained="vggface2").eval().to(device)

# MTCNN from `mtcnn` package (detect_faces)
face_detector = MTCNN()

# --- Embedding Function ---
class FaceNetEmbeddingFunction:
    def __init__(self, model: InceptionResnetV1, face_detector: MTCNN, device: torch.device):
        self.model = model
        self.face_detector = face_detector
        self.device = device

    def extract_face(self, img_path: str) -> (Optional[torch.Tensor], Optional[Dict[str, Any]]):
        try:
            img = Image.open(img_path).convert("RGB")
            img_array = np.array(img)
        except Exception as e:
            print(f"Error opening image {img_path}: {e}")
            return None, None

        faces = self.face_detector.detect_faces(img_array)
        if not faces:
            return None, None

        box = faces[0].get("box")
        if not box:
            return None, faces[0]

        x, y, w, h = box
        # Crop face, ensuring coordinates are valid
        face_img = Image.fromarray(img_array).crop((x, y, x + w, y + h))
        face_img = face_img.resize(IMAGE_SIZE)
        
        # Preprocess for FaceNet model
        face_tensor = torch.tensor(np.array(face_img)).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        face_tensor = face_tensor.to(self.device)
        
        meta = {"box": (x, y, w, h), **faces[0]}
        return face_tensor, meta

    def get_embedding_with_metadata(self, inputs: List[str]) -> List[Dict[str, Any]]:
        out = []
        for img_path in inputs:
            face_tensor, meta = self.extract_face(img_path)
            if face_tensor is None:
                continue
            with torch.no_grad():
                emb = self.model(face_tensor).cpu().numpy().flatten().tolist()
            out.append({
                "embedding": emb,
                "facial_area": meta.get("box") if meta else None,
                "face_confidence": float(meta.get("confidence", 1.0)) if meta else 1.0,
            })
        return out

# --- Database wrapper ---
class Database:
    def __init__(self, db_path: str):
        os.makedirs(db_path, exist_ok=True)
        
        # FIX 1: Use PersistentClient to save the database to disk
        self.client = chromadb.PersistentClient(path=db_path)
        
        # The embedding function is used outside of Chroma, so no need to pass it here
        self.collection = self.client.get_or_create_collection(name="face-database-facenet")
        
        self.embedding_func = FaceNetEmbeddingFunction(model=identity_detector, face_detector=face_detector, device=device)
        self._load_registered_faces_to_db()

    def _load_registered_faces_to_db(self):
        os.makedirs(IDENTITY_FOLDER, exist_ok=True)
        for filename in os.listdir(IDENTITY_FOLDER):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                img_path = os.path.join(IDENTITY_FOLDER, filename)
                name = os.path.splitext(filename)[0].split("_")[0]

                # FIX 2: Correctly check if a record with this name already exists
                existing = self.collection.get(where={"name": name})
                if existing and existing['ids']:
                    print(f"Face '{name}' already in database. Skipping.")
                    continue

                embs = self.embedding_func.get_embedding_with_metadata([img_path])
                if not embs:
                    print(f"No face detected in {filename}. Skipping.")
                    continue

                emb_data = embs[0]
                new_id = str(uuid4())
                self.collection.add(
                    ids=[new_id],
                    embeddings=[emb_data["embedding"]],
                    metadatas=[{"name": name, "facial_area": str(emb_data["facial_area"]), "face_confidence": emb_data["face_confidence"]}],
                )
                print(f"Loaded face '{name}' from {filename} into database with id={new_id}")

    def add_to_collection(self, img_path: str, metadata: Dict[str, Any]) -> str:
        try:
            embs = self.embedding_func.get_embedding_with_metadata([img_path])
            if not embs:
                return "❌ No face detected in the image."

            emb_data = embs[0]
            new_id = str(uuid4())
            self.collection.add(
                ids=[new_id],
                embeddings=[emb_data["embedding"]],
                metadatas=[{**metadata, "facial_area": str(emb_data["facial_area"]), "face_confidence": emb_data["face_confidence"]}],
            )
            return f"✅ User '{metadata.get('name', 'Unknown')}' registered successfully! id={new_id}"
        except Exception as e:
            return f"❌ Failed to register user: {e}"

    def verify(self, img_path: str) -> Dict[str, Any]:
        input_emb_data = self.embedding_func.get_embedding_with_metadata([img_path])
        if not input_emb_data:
            return {"verified": False, "message": "No face detected in the input image."}
        
        input_emb = input_emb_data[0]["embedding"]

        try:
            # FIX 3: Simplified query and result parsing
            result = self.collection.query(
                query_embeddings=[input_emb],
                n_results=1,
                include=["metadatas", "distances"],
            )
        except Exception as e:
            return {"verified": False, "message": f"Database query failed: {e}"}

        if not result or not result.get('ids') or not result['ids'][0]:
            return {"verified": False, "message": "No similar faces found in the database."}
        
        distance = result['distances'][0][0]
        metadata = result['metadatas'][0][0]
        record_id = result['ids'][0][0]

        # Cosine distance is used by default. Lower is better. 0 = identical.
        threshold = 0.4  # Common threshold for FaceNet with VGGFace2
        verified = distance <= threshold

        return {
            # "verified": verified,
            "name": metadata.get('name'),
            "confidence": 1 - float(f"{distance:.4f}"),
            # "threshold": threshold,
            "id": record_id,
        }

    def delete_record(self, record_id: str) -> str:
        try:
            self.collection.delete(ids=[record_id])
            return f"✅ Record '{record_id}' deleted successfully."
        except Exception as e:
            return f"❌ Failed to delete record '{record_id}': {e}"

# --- Gradio Handlers & UI ---
face_db = Database(db_path=VECTOR_DB_PATH)

def save_temp_image(image: Image.Image) -> str:
    temp_dir = "/tmp/gradio_face_rec"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{uuid4()}.jpg")
    image.save(temp_path)
    return temp_path

def register_user(name: str, image: Optional[Image.Image]):
    if image is None or not name:
        return "❌ Name and image are required."
    
    # Check if user already exists
    if face_db.collection.get(where={"name": name})['ids']:
        return f"❌ User '{name}' is already registered."
        
    temp_path = save_temp_image(image)
    try:
        # Save permanent copy in registered_faces/ first
        safe_name = name.replace(" ", "_").lower()
        permanent_path = os.path.join(IDENTITY_FOLDER, f"{safe_name}_{uuid4().hex[:8]}.jpg")
        image.save(permanent_path)
        
        # Add to ChromaDB using the permanent path
        result = face_db.add_to_collection(permanent_path, {"name": name})
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def verify_user_image(image_input: Any):
    if image_input is None:
        return {"error": "Image is required."}

    if isinstance(image_input, str):  # Video file path
        cap = cv2.VideoCapture(image_input)
        ret, frame = cap.read()
        cap.release()
        if not ret: return {"error": "Could not read frame from video."}
        image_to_process = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    else:  # PIL Image
        image_to_process = image_input

    temp_path = save_temp_image(image_to_process)
    try:
        result = face_db.verify(temp_path)
        return result
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def delete_user(record_id: str):
    if not record_id:
        return "❌ Record ID is required."
    return face_db.delete_record(record_id)

def create_tab():
    with gr.Blocks() as face_rec_app:
        gr.Markdown("## Face Recognition System")
        with gr.Tab("Verify Identity"):
            with gr.Row():
                with gr.Column():
                    verify_image = gr.Image(sources=["webcam", "upload"], type="pil", label="Upload or Capture Image for Verification")
                    verify_button = gr.Button("Verify", variant="primary")
                with gr.Column():
                    verify_output = gr.JSON(label="Verification Result")
            verify_button.click(fn=verify_user_image, inputs=[verify_image], outputs=[verify_output])

        with gr.Tab("Register New User"):
            with gr.Row():
                with gr.Column():
                    register_name = gr.Textbox(label="Enter Name")
                    register_image = gr.Image(sources=["webcam", "upload"], type="pil", label="Upload or Capture Image")
                    register_button = gr.Button("Register", variant="primary")
                with gr.Column():
                    register_output = gr.Textbox(label="Registration Status", interactive=False)
            register_button.click(fn=register_user, inputs=[register_name, register_image], outputs=[register_output])

        with gr.Tab("Manage Database"):
            with gr.Row():
                with gr.Column():
                    delete_id = gr.Textbox(label="Enter Record ID to Delete")
                    delete_button = gr.Button("Delete Record", variant="stop")
                with gr.Column():
                    delete_output = gr.Textbox(label="Deletion Status", interactive=False)
            delete_button.click(fn=delete_user, inputs=[delete_id], outputs=[delete_output])

    return face_rec_app