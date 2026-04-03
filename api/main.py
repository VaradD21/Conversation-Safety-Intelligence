from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, List
import os
import uuid

from model.pipeline import analyze_conversation
from model.message_analyzer import analyze_message
from model.image_analyzer import analyze_media

app = FastAPI(
    title="Conversation Safety Analyzer API",
    description="Analyzes multi-turn conversations for hazardous or toxic patterns.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageInput(BaseModel):
    sender: str
    text: str = ""
    image_base64: str = Field(default=None, description="Optional base64 encoded image string (e.g. data:image/png;base64,iVBO...)")


class ConversationMetadata(BaseModel):
    sender_id: str = Field(default="unknown_sender", description="Unique ID for the sender.")
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the conversation.")
    friendship_duration_days: int = Field(default=0, description="How long the users have been connected.")
    sender_age: int = Field(default=25, description="Profile age of sender. Use 25 to let the model infer it.")
    receiver_age: int = Field(default=25, description="Profile age of receiver. Use 25 to let the model infer it.")

class ConversationRequest(BaseModel):
    conversation: List[MessageInput] = Field(..., description="List of messages in chronological order.")
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata, description="Profile and relationship context.")

class EvidenceItem(BaseModel):
    flag: str
    message_indices: List[int] = Field(default_factory=list)
    matched_text: List[str] = Field(default_factory=list)
    detail: str = ""
    weight: float = 0.0


class AnalysisResponse(BaseModel):
    risk_level: str
    confidence: float
    reason: str
    flagged_messages: List[int] = Field(default_factory=list)
    behavioral_flags: List[str] = Field(default_factory=list)
    detected_phase: str = Field(default="Normal")
    evidence: List[EvidenceItem] = Field(default_factory=list)
    category_scores: Dict[str, float] = Field(default_factory=dict)
    decision_trace: List[str] = Field(default_factory=list)
    user_risk_score: int = Field(default=0)
    repeat_offender: bool = Field(default=False)
    ai_judgment: str = Field(default="")
    threat_category: str = Field(default="unknown")
    action_recommended: str = Field(default="")

class DOMBatchRequest(BaseModel):
    texts: List[str] = Field(..., description="Array of text node strings extracted from the DOM")

class MediaRequest(BaseModel):
    media_base64: str = Field(..., description="Base64 encoded string of the media (image, gif, video)")
    media_type: str = Field(default="image", description="Type of media: 'image', 'gif', 'video/mp4', etc.")

@app.post("/analyze_media")
async def analyze_media_endpoint(request: MediaRequest):
    if not request.media_base64:
        raise HTTPException(status_code=400, detail="media_base64 cannot be empty.")
    
    try:
        is_adult, confidence, frames_scanned = analyze_media(request.media_base64, request.media_type)
        return {
            "is_adult": is_adult,
            "confidence": round(confidence, 3),
            "analyzed_frames": frames_scanned,
            "media_type_processed": request.media_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Media analysis failed: {str(e)}")

@app.get("/blocklist")
async def get_blocklist():
    # In a full app, this connects to the AI database to fetch dynamic bad domains.
    # For now, we return a static block list of demo risky domains.
    return {
        "domains": [
            "pornhub.com",
            "xvideos.com",
            "livegore.com",
            "bestgore.com",
            "omegle.com",
            "chatroulette.com"
        ]
    }

@app.post("/analyze_dom")
async def analyze_dom_endpoint(request: DOMBatchRequest):
    if not request.texts:
        return {"results": []}
    
    # We run the text through our high-speed NLP toxicity & sentiment models
    results = []
    for text in request.texts:
        try:
            # We skip AI Judge and complex context for raw DOM speed
            analysis = analyze_message(text, "DOM_Node")
            
            # Simple thresholding for real-time DOM blurring
            # If toxicity is high or highly negative sentiment indicating cyberbullying
            is_hazardous = analysis["toxicity"] > 0.75 or (analysis["sentiment_score"] < -0.8 and analysis["toxicity"] > 0.5)
            
            reason = "High Toxicity/Bullying" if is_hazardous else "Safe"
            
            results.append({
                "is_hazardous": is_hazardous,
                "reason": reason
            })
        except Exception as e:
            results.append({"is_hazardous": False, "reason": "error"})
            
    return {"results": results}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(request: ConversationRequest):
    if not request.conversation:
        raise HTTPException(status_code=400, detail="Conversation cannot be empty.")
    
    # Convert Pydantic models to dicts
    convo_dicts = [{"sender": msg.sender, "text": msg.text, "image_base64": msg.image_base64} for msg in request.conversation]
    meta_dict = request.metadata.dict()
    
    try:
        result = analyze_conversation(convo_dicts, meta_dict)
        return AnalysisResponse(
            risk_level=result["risk_level"],
            confidence=result["confidence"],
            reason=result["reason"],
            flagged_messages=result.get("flagged_messages", []),
            behavioral_flags=result.get("behavioral_flags", []),
            detected_phase=result.get("detected_phase", "Normal"),
            evidence=result.get("evidence", []),
            category_scores=result.get("category_scores", {}),
            decision_trace=result.get("decision_trace", []),
            user_risk_score=result.get("user_risk_score", 0),
            repeat_offender=result.get("repeat_offender", False),
            ai_judgment=result.get("ai_judgment", ""),
            threat_category=result.get("threat_category", "unknown"),
            action_recommended=result.get("action_recommended", "")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal analysis error: {str(e)}")

from fastapi.responses import FileResponse

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
os.makedirs(frontend_path, exist_ok=True)

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Mount the rest of the directory at /static
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

if __name__ == "__main__":
    import uvicorn
    # To run locally: python -m api.main
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
