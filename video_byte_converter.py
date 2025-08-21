import base64
import sys

def video_to_base64(video_path):
    try:
        with open(video_path, "rb") as video_file:
            encoded_string = base64.b64encode(video_file.read()).decode('utf-8')
        return encoded_string
    except FileNotFoundError:
        return f"Error: Video file not found at {video_path}"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python video_byte_converter.py <path_to_video_file>")
    else:
        video_file_path = sys.argv[1]
        base64_data = video_to_base64(video_file_path)
        print(base64_data)