import os
import urllib.request
import json
import base64

def check_directory(directory_path="test_media"):
    # Create the directory if it doesn't exist
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created folder '{directory_path}'.")
        print(f"Please place your test images, videos, or GIFs inside '{directory_path}' and run this script again.")
        return

    files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
    
    if not files:
        print(f"The folder '{directory_path}' is empty!")
        print(f"Please place your test images, videos, or GIFs inside '{directory_path}' and run this script again.")
        return

    print(f"\nScanning {len(files)} files found in '{directory_path}'...\n")
    print("=" * 60)
    print(f"{'FILENAME':<25} | {'CLASSIFICATION':<15} | {'CONFIDENCE':<10}")
    print("=" * 60)

    url = "http://localhost:8000/analyze_media"

    for filename in files:
        file_path = os.path.join(directory_path, filename)
        
        # Determine media type for the API
        ext = filename.lower().split('.')[-1]
        media_type = "image"
        if ext in ['mp4', 'webm', 'mov', 'avi']:
            media_type = f"video/{ext}"
        elif ext == 'gif':
            media_type = "image/gif"
        elif ext in ['jpg', 'jpeg', 'png']:
            media_type = f"image/{ext}"

        # Read and encode to Base64
        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
                encoded_string = base64.b64encode(file_bytes).decode('utf-8')
        except Exception as e:
            print(f"{filename:<25} | ERROR: {str(e)[:15]}")
            continue

        payload = {
            "media_base64": encoded_string,
            "media_type": media_type
        }

        # Query API
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read())
                
                is_adult = res.get('is_adult', False)
                conf = res.get('confidence', 0.0)
                
                # Format output nicely
                classification = "🛑 NSFW (ADULT)" if is_adult else "✅ SAFE"
                print(f"{filename[:23]:<25} | {classification:<15} | {conf:.3f}")
                
        except Exception as e:
            print(f"{filename:<25} | API ERROR: {str(e)[:15]}")

    print("=" * 60)
    print("\nScan complete.")

if __name__ == "__main__":
    # Base directory of the project
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    test_dir = os.path.join(base_dir, "test_media")
    check_directory(test_dir)
