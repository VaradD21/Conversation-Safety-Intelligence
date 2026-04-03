import base64
import io
import os
import tempfile
from typing import Dict, Any, Tuple, List
from PIL import Image, ImageSequence

_models_loaded = False
_nsfw_model = None
_anime_model = None

def _load_image_models():
    """Lazy load the huggingface pipelines to save memory."""
    global _models_loaded, _nsfw_model, _anime_model
    if _models_loaded:
        return
    _models_loaded = True

    try:
        from transformers import pipeline
        # Falconsai is excellent for photorealistic / general explicit content detection
        # It's an efficient ViT model.
        _nsfw_model = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
        print("✅ Image Engine: Falconsai/nsfw_image_detection model loaded.")
        
        # deepghs/anime_classification detects general anime features but we can use its probability distribution
        # if the user wants NSFW specifically for anime, deepghs has 'deepghs/anime_rating' but for right now
        # Falconsai captures almost everything explicit. We'll load deepghs just for specific edge-cases if requested,
        # but for this iteration, Falconsai is the primary.
    except Exception as e:
        print(f"⚠️ Image Engine: Could not load image model ({e}). Image scoring disabled.")

def decode_image(base64_string: str) -> Image.Image:
    """Decodes a base64 string to a PIL Image."""
    # Remove header if present (e.g. data:image/png;base64,...)
    if "," in base64_string:
         base64_string = base64_string.split(",")[1]
    
    try:
        decoded_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(decoded_data))
        return image
    except Exception as e:
        print(f"Warning: Failed to decode image: {e}")
        return None

def _score_pil_image(image: Image.Image) -> Tuple[bool, float, str]:
    if image.mode != "RGB":
        image = image.convert("RGB")
    try:
        results = _nsfw_model(image)
        top_label = max(results, key=lambda x: x["score"])
        is_nsfw = (top_label["label"] == "nsfw" and top_label["score"] > 0.6)
        return is_nsfw, top_label["score"], top_label["label"]
    except Exception as e:
        print(f"Warning: Image classification failed: {e}")
        return False, 0.0, "error"

def analyze_image(image_base64: str) -> Tuple[bool, float, str]:
    """Analyzes a static image."""
    if not image_base64:
        return False, 0.0, "safe"
    
    _load_image_models()
    if _nsfw_model is None:
        return False, 0.0, "safe"

    image = decode_image(image_base64)
    if not image:
        return False, 0.0, "safe"
        
    return _score_pil_image(image)

def _extract_video_frames(video_bytes: bytes, num_frames=5) -> List[Image.Image]:
    """Helper to extract frames using OpenCV cleanly via a temporary file."""
    import cv2
    frames = []
    
    # Needs a temp file because cv2.VideoCapture requires a path or fd on most platforms
    fd, path = tempfile.mkstemp(suffix=".mp4")
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(video_bytes)
            
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return []
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            return []
            
        step = max(1, total_frames // num_frames)
        
        for i in range(num_frames):
            frame_idx = i * step
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            # Convert BGR (cv2) to RGB (PIL)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            frames.append(pil_img)
            
        cap.release()
    finally:
        # Secure cleanup
        if os.path.exists(path):
            os.remove(path)
            
    return frames

def analyze_media(media_base64: str, media_type: str = "image") -> Tuple[bool, float, int]:
    """
    Analyzes static images, GIFs, and videos. 
    Returns: (is_adult: bool, highest_confidence: float, frames_scanned: int)
    """
    if not media_base64:
        return False, 0.0, 0
        
    _load_image_models()
    if _nsfw_model is None:
        return False, 0.0, 0
        
    # Standardize base64
    if "," in media_base64:
        media_base64 = media_base64.split(",")[1]
        
    try:
        decoded_data = base64.b64decode(media_base64)
    except Exception:
        return False, 0.0, 0

    highest_score = 0.0
    frames_scanned = 0

    # Handle Videos
    if "video" in media_type.lower():
        frames = _extract_video_frames(decoded_data, num_frames=6)
        if not frames:
            return False, 0.0, 0
            
        for frame in frames:
            is_nsfw, score, _ = _score_pil_image(frame)
            if score > highest_score:
                highest_score = score
            if is_nsfw:
                return True, highest_score, len(frames)
                
        return False, highest_score, len(frames)

    # Handle Images and GIFs
    image = Image.open(io.BytesIO(decoded_data))
    
    # Check if GIF/Animated
    if getattr(image, "is_animated", False):
        try:
           import numpy as np
           # We will sample up to 6 frames from the GIF
           # A simple way to sample is convert Sequence to list
           iterator = ImageSequence.Iterator(image)
           gif_frames = []
           for idx, frame in enumerate(iterator):
               gif_frames.append(frame.copy())
               if len(gif_frames) > 50: # safety cap
                   break
           
           step = max(1, len(gif_frames) // 6)
           sample_frames = gif_frames[::step][:6]
           
           for f in sample_frames:
               is_nsfw, score, _ = _score_pil_image(f)
               if score > highest_score:
                   highest_score = score
               if is_nsfw:
                   return True, highest_score, len(sample_frames)
           return False, highest_score, len(sample_frames)
        except Exception as e:
            print("GIF extraction failed", e)
            return False, 0.0, 0

    # Static Image fallback
    is_nsfw, score, _ = _score_pil_image(image)
    return is_nsfw, score, 1

