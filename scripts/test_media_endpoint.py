import urllib.request
import json
import base64
import os
import tempfile
import cv2
import numpy as np

def create_test_video():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    
    # Create a simple 1 second video (red frames)
    # Using 'mp4v' or 'avc1'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(path, fourcc, 10.0, (100, 100))
    for _ in range(10):
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:] = (0, 0, 255) # Red frame in BGR
        out.write(frame)
    out.release()
    
    with open(path, "rb") as f:
        video_bytes = f.read()
        
    os.remove(path)
    return base64.b64encode(video_bytes).decode('utf-8')

def test_analyze_media():
    print(f"\n--- Testing Dedicated Media Analyzer ---")
    url = "http://localhost:8000/analyze_media"
    
    print("Generating simulated video...")
    video_b64 = create_test_video()
    
    payload = {
        "media_base64": video_b64,
        "media_type": "video/mp4"
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        print("Sending to API...")
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
            print(f"Is Adult Content? : {res.get('is_adult')}")
            print(f"Confidence Score  : {res.get('confidence')}")
            print(f"Frames Scanned    : {res.get('analyzed_frames')}")
            return res
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_analyze_media()
