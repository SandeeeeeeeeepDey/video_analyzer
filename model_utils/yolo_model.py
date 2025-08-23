from ultralytics import YOLO

_yolo_model = None

def get_yolo_model():
    """
    Loads the YOLO model, caching it for future use.
    """
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO('yolov8n.pt')
    return _yolo_model

