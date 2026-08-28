from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, List
import asyncio
import os
import uuid

from model.pipeline import analyze_conversation
from model.message_analyzer import analyze_message
from model.image_analyzer import analyze_media
from model import database

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize resources at startup, clean up on shutdown."""
    database.init_db()
    yield


app = FastAPI(
    title="Conversation Safety Analyzer API",
    description="Analyzes multi-turn conversations for hazardous or toxic patterns.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "chrome-extension://*",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

class MessageInput(BaseModel):
    sender: str
    text: str = ""
    image_base64: str = Field(default=None, description="Optional base64 encoded image string (e.g. data:image/png;base64,iVBO...)")


class ConversationMetadata(BaseModel):
    child_id: str = Field(default="unknown", description="ID of the child account.")
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
    child_id: str = Field(default="unknown", description="ID of the child account.")
    texts: List[str] = Field(..., description="Array of text node strings extracted from the DOM")

class MediaRequest(BaseModel):
    media_base64: str = Field(..., description="Base64 encoded string of the media (image, gif, video)")
    media_type: str = Field(default="image", description="Type of media: 'image', 'gif', 'video/mp4', etc.")

@app.post("/analyze_media")
async def analyze_media_endpoint(request: MediaRequest):
    if not request.media_base64:
        raise HTTPException(status_code=400, detail="media_base64 cannot be empty.")
    
    try:
        is_adult, confidence, frames_scanned = await asyncio.to_thread(
            analyze_media, request.media_base64, request.media_type
        )
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

from fastapi import FastAPI, HTTPException, BackgroundTasks
import time

# Store background tasks state (In production this would be Redis/Postgres)
BACKGROUND_ESCALATIONS: Dict[str, Dict] = {}

# Rate Limiting Configuration
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 30  # Sane default: 30 requests per minute per child
RATE_LIMITS: Dict[str, List[float]] = {}

def check_rate_limit(child_id: str) -> bool:
    """
    Sliding window rate limiter.
    Returns True if request is allowed, False if limit exceeded.
    """
    if not child_id:
        child_id = "unknown"
        
    try:
        now = time.time()
        if child_id not in RATE_LIMITS:
            RATE_LIMITS[child_id] = []
            
        # Prune requests outside the sliding window
        RATE_LIMITS[child_id] = [t for t in RATE_LIMITS[child_id] if now - t < RATE_LIMIT_WINDOW_SECONDS]
        
        if len(RATE_LIMITS[child_id]) >= RATE_LIMIT_MAX_REQUESTS:
            return False
            
        # Record this request
        RATE_LIMITS[child_id].append(now)
        return True
    except Exception as e:
        # FAIL CLOSED: If the rate limiter encounters an error (e.g. OOM), we fail closed
        # by returning False. For a safety product, if we fail open, an attacker could 
        # intentionally trigger the error condition to bypass limits.
        print(f"Rate Limiter Exception: {e}")
        return False

async def run_background_judge(req_id: str, convo: list, base_risk: str, flags: list, phase: str):
    from model.ai_judge import get_ai_judgment
    try:
        # Pass empty age_profiles for now since they are less critical for quick DOM alerts
        ai_result = await asyncio.to_thread(get_ai_judgment, convo, base_risk, flags, phase, {})
        
        ai_final_risk = ai_result.get("final_risk", base_risk)
        risk_order = {"safe": 0, "warning": 1, "hazardous": 2}
        
        if risk_order.get(ai_final_risk, 0) > risk_order.get(base_risk, 0):
            BACKGROUND_ESCALATIONS[req_id] = {
                "status": "completed",
                "escalated": True,
                "new_risk_level": ai_final_risk,
                "reason": ai_result.get("reason", "")
            }
        else:
            BACKGROUND_ESCALATIONS[req_id] = {
                "status": "completed",
                "escalated": False
            }
    except Exception as e:
        BACKGROUND_ESCALATIONS[req_id] = {
            "status": "error",
            "error": str(e)
        }

@app.get("/analyze_dom/status/{request_id}")
async def get_dom_status(request_id: str):
    if request_id not in BACKGROUND_ESCALATIONS:
        raise HTTPException(status_code=404, detail="Request ID not found")
    return BACKGROUND_ESCALATIONS[request_id]

@app.post("/analyze_dom")
async def analyze_dom_endpoint(request: DOMBatchRequest, background_tasks: BackgroundTasks):
    from model.pipeline import analyze_conversation_core
    
    # Rate Limiting Check
    if not check_rate_limit(request.child_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for this child account.")
        
    if not request.texts:
        return {"results": []}
    
    results = []
    for text in request.texts:
        try:
            convo = [{"sender": "DOM_Node", "text": text}]
            # We skip AI Judge for raw DOM speed, but reuse Tier 0 & 1
            result_obj = await asyncio.to_thread(analyze_conversation_core, convo, None, skip_ai_judge=True)
            
            is_hazardous = result_obj.risk_level in ["hazardous", "warning"]
            reason = result_obj.reason
            
            # Check if it was ambiguous (escalated to Tier 2, didn't short circuit in T0/T1)
            did_short_circuit = any("short_circuit" in t for t in result_obj.decision_trace)
            
            if not did_short_circuit and result_obj.risk_level != "hazardous":
                # Schedule background AI judge (only if it wasn't already hard hazardous!)
                req_id = str(uuid.uuid4())
                BACKGROUND_ESCALATIONS[req_id] = {"status": "pending"}
                background_tasks.add_task(
                    run_background_judge, 
                    req_id, 
                    convo, 
                    result_obj.risk_level, 
                    result_obj.behavioral_flags, 
                    result_obj.detected_phase
                )
                
                results.append({
                    "is_hazardous": is_hazardous,
                    "reason": reason,
                    "escalation_id": req_id
                })
            else:
                results.append({
                    "is_hazardous": is_hazardous,
                    "reason": reason
                })
        except Exception as e:
            results.append({"is_hazardous": False, "reason": "error"})
            
    return {"results": results}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(request: ConversationRequest):
    # Rate Limiting Check
    if not check_rate_limit(request.metadata.child_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for this child account.")
        
    if not request.conversation:
        raise HTTPException(status_code=400, detail="Conversation cannot be empty.")
    
    # Convert Pydantic models to dicts
    convo_dicts = [{"sender": msg.sender, "text": msg.text, "image_base64": msg.image_base64} for msg in request.conversation]
    meta_dict = request.metadata.model_dump()
    
    try:
        result = await asyncio.to_thread(analyze_conversation, convo_dicts, meta_dict)
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
