import uuid
from typing import List, Dict, Any

from model.message_analyzer import analyze_message
from model.feature_extractor import extract_features
from model.pattern_matcher import match_patterns
from model.decision_engine import classify
from model.explainer import generate_explanation
from model import database

# Initialize the database when pipeline is loaded
try:
    database.init_db()
except Exception as e:
    print(f"Warning: Failed to initialize memory DB: {e}")

def analyze_conversation(conversation: List[Dict[str, str]], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Connect everything.
    Flow:
    - For each message -> call analyze_message
    - Pass results to feature_extractor
    - Pass features to pattern_matcher
    - Pass everything to decision_engine
    - Save to DB and return final result
    """
    if metadata is None:
        metadata = {"friendship_duration_days": 0, "sender_age": 25, "receiver_age": 25}

    sender_id = metadata.get("sender_id", "unknown_sender")
    conversation_id = metadata.get("conversation_id", str(uuid.uuid4()))

    if not conversation:
        return {
            "risk_level": "safe",
            "confidence": 1.0,
            "reason": "Empty conversation.",
            "behavioral_flags": [],
            "detected_phase": "Normal",
            "user_risk_score": 0,
            "repeat_offender": False
        }
        
    analyzed_messages = []
    for msg in conversation:
        analysis = analyze_message(msg.get("text", ""))
        analysis["sender"] = msg.get("sender", "unknown")
        analyzed_messages.append(analysis)
        
    # Get initial user record to pass down
    try:
        user_record = database.get_user(sender_id)
        user_risk_score = user_record.get("risk_score", 0)
    except Exception:
        user_risk_score = 0
        
    features = extract_features(analyzed_messages, metadata)
    patterns = match_patterns(analyzed_messages, metadata)
    decision = classify(features, patterns, metadata)
    
    reason = generate_explanation(features, patterns, decision)
    
    flagged_messages = []
    for i, msg in enumerate(analyzed_messages):
        if msg.get("toxicity", 0.0) > 0.7:
            flagged_messages.append(i)
            
    # Step 3: log memory and state
    risk_level = decision["risk_level"]
    confidence = decision["confidence"]
    try:
        database.update_user_risk(sender_id, risk_level)
        database.log_interaction(conversation_id, sender_id, risk_level, confidence)
        
        # update current risk after applying rules for output
        user_record = database.get_user(sender_id)
        user_risk_score = user_record.get("risk_score", 0)
    except Exception as e:
        print(f"Warning: Database error: {e}")
    
    return {
        "risk_level": risk_level,
        "confidence": confidence,
        "reason": reason,
        "flagged_messages": flagged_messages,
        "behavioral_flags": patterns.get("flags", []),
        "detected_phase": patterns.get("detected_phase", "Normal"),
        "user_risk_score": user_risk_score,
        "repeat_offender": decision.get("repeat_offender", False)
    }
