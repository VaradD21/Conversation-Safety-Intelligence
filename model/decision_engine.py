import os
import pickle
import numpy as np
from typing import Dict, Any

from model import database

# Dynamically load the trained Random Forest model if the training script was run
clf = None
model_path = os.path.join(os.path.dirname(__file__), "..", "models", "classifier.pkl")
if os.path.exists(model_path):
    try:
        with open(model_path, "rb") as f:
            clf = pickle.load(f)
    except Exception:
        pass

def classify(features: Dict[str, Any], patterns: Dict[str, Any], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Final classification logic using Multi-Layered Defense and Historical Risk.
    """
    result = {
        "risk_level": "safe",
        "confidence": 0.0,
        "repeat_offender": False
    }
    
    if metadata is None:
        metadata = {"friendship_duration_days": 100, "sender_age": 25, "receiver_age": 25}

    sender_id = metadata.get("sender_id", "unknown_sender")
    
    # 1. Fetch user memory
    try:
        user_record = database.get_user(sender_id)
        user_risk_score = user_record.get("risk_score", 0)
        
        # Adjust Thresholds
        hazard_threshold = 0.9
        if user_risk_score > 10:
            hazard_threshold = 0.7
            result["repeat_offender"] = True
            patterns["flags"] = patterns.get("flags", []) + ["repeat_offender"]
        if user_risk_score > 20:
            hazard_threshold = 0.5
            
        # Multi-Target Detection (Predatory Pattern)
        stats = database.get_user_interaction_stats(sender_id)
        if stats["unique_conversations"] >= 3 and stats["total_hazardous"] >= 2:
            patterns["flags"] = patterns.get("flags", []) + ["predatory_pattern"]
            result["risk_level"] = "hazardous"
            result["confidence"] = 0.99
            return result
            
    except Exception:
        hazard_threshold = 0.9

    flags = patterns.get("flags", [])
    max_tox = features.get("max_toxicity", 0.0)
    avg_tox = features.get("avg_toxicity", 0.0)
    friend_days = metadata.get("friendship_duration_days", 0)
    age_gap = features.get("age_disparity", 0.0)

    # ==========================
    # LAYER 0: CONTEXT OVERRIDES 
    # ==========================
    if "identity_deception" in flags:
        result["risk_level"] = "hazardous"
        result["confidence"] = 1.0
        return result

    if "suspected_grooming" in flags:
        if age_gap > 5 and friend_days < 30:
            result["risk_level"] = "hazardous"
            result["confidence"] = 0.95
            return result
        else:
            result["risk_level"] = "warning"
            result["confidence"] = 0.7
            return result

    if friend_days > 180 and max_tox < 0.8 and not result["repeat_offender"]:
        result["risk_level"] = "safe"
        result["confidence"] = 0.9
        return result

    # ==========================
    # LAYER 1: Hard Rule Overrides
    # ==========================
    if max_tox >= hazard_threshold:
        result["risk_level"] = "hazardous"
        result["confidence"] = 0.98
        return result
    if "pii_leak_detected" in flags:
        result["risk_level"] = "warning"
        result["confidence"] = 0.85
        return result

    # ==========================
    # LAYER 2: ML Random Forest Fusion
    # ==========================
    if clf is not None:
        # We need to make sure the vector here matches the one used in training!
        # For now, we'll use the basic 6-feature vector. 
        # Future note: We should retrain with the context features included.
        vector = [[
            features.get("avg_toxicity", 0.0),
            features.get("max_toxicity", 0.0),
            float(features.get("num_toxic_messages", 0)),
            float(features.get("max_consecutive_toxic", 0)),
            features.get("sender_imbalance", 0.0),
            features.get("escalation", 0.0)
        ]]
        
        probas = clf.predict_proba(vector)[0]
        max_idx = np.argmax(probas)
        max_p = probas[max_idx]
        
        result["confidence"] = float(max_p)
        if max_idx == 2 and max_p > 0.5:
            result["risk_level"] = "hazardous"
        elif max_idx == 1 and max_p > 0.4:
            result["risk_level"] = "warning"
        else:
            result["risk_level"] = "safe"
        return result

    # FALLBACK
    if avg_tox > 0.5:
        result["risk_level"] = "warning"
    return result
