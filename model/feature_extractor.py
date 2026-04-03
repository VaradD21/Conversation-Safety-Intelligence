from typing import List, Dict, Any

def extract_features(analyzed_messages: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Convert list of analyzed messages and metadata into conversation-level features."""
    features = {
        "avg_toxicity": 0.0,
        "max_toxicity": 0.0,
        "num_toxic_messages": 0,
        "max_consecutive_toxic": 0,
        "sender_imbalance": 0.0,
        "escalation": 0.0,
        "age_disparity": 0.0,
        "is_long_friendship": 0.0,
        "phase_score": 0.0
    }
    
    if not analyzed_messages:
        return features

    if metadata is None:
        metadata = {"friendship_duration_days": 100, "sender_age": 25, "receiver_age": 25}
        
    # Metadata features
    sender_age = metadata.get("sender_age", 25)
    receiver_age = metadata.get("receiver_age", 25)
    features["age_disparity"] = abs(sender_age - receiver_age)
    features["is_long_friendship"] = 1.0 if metadata.get("friendship_duration_days", 0) > 180 else 0.0

    tox_scores = [m.get("toxicity", 0.0) for m in analyzed_messages]
    features["avg_toxicity"] = sum(tox_scores) / len(tox_scores)
    features["max_toxicity"] = max(tox_scores)
    
    is_toxic = [t > 0.5 for t in tox_scores]
    features["num_toxic_messages"] = sum(is_toxic)
    
    # Max consecutive
    max_consec = 0
    current_consec = 0
    for t in is_toxic:
        if t:
            current_consec += 1
            if current_consec > max_consec:
                max_consec = current_consec
        else:
            current_consec = 0
    features["max_consecutive_toxic"] = max_consec
    
    # Sender imbalance
    senders = [m.get("sender") for m in analyzed_messages if "sender" in m]
    if senders:
        initiator = senders[0]
        init_count = sum(1 for s in senders if s == initiator)
        features["sender_imbalance"] = init_count / len(senders)
        
    # Escalation
    if len(tox_scores) > 1:
        import numpy as np
        x = np.arange(len(tox_scores))
        try:
            slope, _ = np.polyfit(x, tox_scores, 1)
            features["escalation"] = float(slope)
        except Exception:
            features["escalation"] = 0.0
        
    return features
