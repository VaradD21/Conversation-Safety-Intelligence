"""feature_extractor.py — Extract message and conversation-level features using pretrained models"""
import numpy as np
from typing import List, Dict, Any

from preprocessor import Message

# --- model loading ---
try:
    from detoxify import Detoxify
    DETOX_MODEL = Detoxify('original')
except ImportError:
    DETOX_MODEL = None

try:
    from transformers import pipeline
    SENTIMENT_MODEL = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment")
except ImportError:
    SENTIMENT_MODEL = None

# --- types ---
# Standard dictionaries used for feature mapping

# --- constants ---
# Fallback sentiment mapping
SENTIMENT_MAP = {
    "LABEL_0": -1.0,  # negative
    "LABEL_1": 0.0,   # neutral
    "LABEL_2": 1.0    # positive
}

# --- core functions ---
def extract_message_features(msg: Message) -> Dict[str, Any]:
    """Returns: {toxicity: float, sentiment: str, sentiment_score: float}. Input: Message. Output: dict."""
    features = {
        "toxicity": 0.0,
        "sentiment": "neutral",
        "sentiment_score": 0.0
    }
    
    if not msg.text:
        return features

    if DETOX_MODEL:
        try:
            res = DETOX_MODEL.predict(msg.text)
            features["toxicity"] = float(res["toxicity"])
        except Exception:
            pass

    if SENTIMENT_MODEL:
        try:
            res = SENTIMENT_MODEL(msg.text)
            if res and len(res) > 0:
                label = res[0]["label"]
                score = float(res[0]["score"])
                mapped_score = SENTIMENT_MAP.get(label, 0.0) * score
                features["sentiment_score"] = mapped_score
                features["sentiment"] = "negative" if mapped_score < -0.3 else ("positive" if mapped_score > 0.3 else "neutral")
        except Exception:
            pass

    return features

def extract_conversation_features(messages: List[Message]) -> Dict[str, Any]:
    """Returns conversation-level feature aggregations. Input: list[Message]. Output: dict."""
    features = {
        "sender_imbalance": 0.0,
        "topic_drift": 0.0,
        "escalation_slope": 0.0,
        "secrecy_count": 0,
        "personal_info_requests": 0
    }
    
    if not messages:
        return features
        
    initiator_cnt = sum(1 for m in messages if m.role == "initiator")
    features["sender_imbalance"] = float(initiator_cnt) / len(messages)
    
    return features

def build_feature_vector(msg_features: List[Dict[str, Any]], conv_features: Dict[str, Any]) -> np.ndarray:
    """Returns: flat numpy array of floats. Input: list[dict], dict. Output: np.ndarray."""
    if not msg_features:
        avg_tox = 0.0
        max_tox = 0.0
    else:
        tox_scores = [f.get("toxicity", 0.0) for f in msg_features]
        avg_tox = sum(tox_scores) / len(tox_scores)
        max_tox = max(tox_scores)

    vector = [
        avg_tox,
        max_tox,
        conv_features.get("sender_imbalance", 0.0),
        conv_features.get("topic_drift", 0.0),
        conv_features.get("escalation_slope", 0.0),
        float(conv_features.get("secrecy_count", 0)),
        float(conv_features.get("personal_info_requests", 0))
    ]
    
    return np.array(vector, dtype=float)

if __name__ == "__main__":
    # smoke test
    m1 = Message(sender="A", text="test 1", ts_unix=1, role="initiator", turn_index=0)
    m2 = Message(sender="B", text="test 2", ts_unix=2, role="receiver", turn_index=1)
    msgs = [m1, m2]
    
    m_feats = [extract_message_features(m) for m in msgs]
    c_feats = extract_conversation_features(msgs)
    vec = build_feature_vector(m_feats, c_feats)
    
    assert len(m_feats) == 2
    assert "toxicity" in m_feats[0]
    assert "sender_imbalance" in c_feats
    assert isinstance(vec, np.ndarray)
    print("feature_extractor smoke test passed.")
