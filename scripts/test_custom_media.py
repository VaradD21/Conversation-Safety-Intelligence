import urllib.request
import json
import base64
import sys
import os

def test_custom_media(file_path):
    print(f"--- Analyzing: {file_path} ---")
    url = "http://localhost:8000/analyze_media"
    
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return
        
    # Determine basic media type
    ext = file_path.lower().split('.')[-1]
    media_type = "image"
    if ext in ['mp4', 'webm', 'mov', 'avi']:
        media_type = f"video/{ext}"
    elif ext == 'gif':
        media_type = "image/gif"
    elif ext in ['jpg', 'jpeg', 'png']:
        media_type = f"image/{ext}"
        
    # Read file and convert to Base64
    print("Reading and encoding file...")
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            encoded_string = base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    payload = {
        "media_base64": encoded_string,
        "media_type": media_type
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        print("Sending to API for AI Evaluation...")
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
            
            print("\n✅ API Response received:")
            print("-------------------------")
            print(f"Is Adult Content? : {res.get('is_adult')}")
            print(f"Confidence Score  : {res.get('confidence')}")
            print(f"Frames Scanned    : {res.get('analyzed_frames')}")
            print(f"Media Type Handled: {res.get('media_type_processed')}")
            print("-------------------------")
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: py scripts/test_custom_media.py <path_to_your_file>")
        print("Example: py scripts/test_custom_media.py my_video.mp4")
    else:
        test_custom_media(sys.argv[1])
