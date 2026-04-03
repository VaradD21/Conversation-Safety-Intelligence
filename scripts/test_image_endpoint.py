import urllib.request
import json
import base64
from PIL import Image
import io
import uuid

def create_test_image():
    # Create a simple red square image
    img = Image.new('RGB', (100, 100), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    return base64.b64encode(img_byte_arr).decode('utf-8')

def test_api():
    print(f"\n--- Testing Image Endpoint ---")
    url = "http://localhost:8000/analyze"
    base64_image = create_test_image()
    
    payload = {
        "conversation": [
            {"sender": "Stranger", "text": "hey look at this picture"},
            {"sender": "Stranger", "text": "", "image_base64": base64_image}
        ],
        "metadata": {
            "sender_id": f"test_sender_{uuid.uuid4().hex[:4]}",
            "sender_age": 30
        }
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read())
            print(f"Risk Level : {res.get('risk_level')}")
            print(f"Category   : {res.get('threat_category')}")
            print(f"Flags      : {res.get('behavioral_flags')}")
            print(f"AI Judgment: {res.get('ai_judgment')}")
            print("\nEvidence Items:")
            for item in res.get('evidence', []):
                print(f" - {item['flag']}: {item['detail']}")
            return res
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    test_api()
