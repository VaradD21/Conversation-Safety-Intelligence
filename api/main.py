from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List
import os
import uuid

from model.pipeline import analyze_conversation

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
    text: str

class ConversationMetadata(BaseModel):
    sender_id: str = Field(default="unknown_sender", description="Unique ID for the sender.")
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique ID for the conversation.")
    friendship_duration_days: int = Field(default=0, description="How long the users have been connected.")
    sender_age: int = Field(default=25, description="Actual profile age of the sender.")
    receiver_age: int = Field(default=25, description="Actual profile age of the receiver.")

class ConversationRequest(BaseModel):
    conversation: List[MessageInput] = Field(..., description="List of messages in chronological order.")
    metadata: ConversationMetadata = Field(default_factory=ConversationMetadata, description="Profile and relationship context.")

class AnalysisResponse(BaseModel):
    risk_level: str
    confidence: float
    reason: str
    flagged_messages: List[int] = Field(default_factory=list)
    behavioral_flags: List[str] = Field(default_factory=list)
    detected_phase: str = Field(default="Normal")
    user_risk_score: int = Field(default=0)
    repeat_offender: bool = Field(default=False)

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(request: ConversationRequest):
    if not request.conversation:
        raise HTTPException(status_code=400, detail="Conversation cannot be empty.")
    
    # Convert Pydantic models to dicts
    convo_dicts = [{"sender": msg.sender, "text": msg.text} for msg in request.conversation]
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
            user_risk_score=result.get("user_risk_score", 0),
            repeat_offender=result.get("repeat_offender", False)
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

