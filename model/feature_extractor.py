from typing import List

from model.schemas import ConversationFeatures, ConversationMetadata, MessageAnalysis

FEATURE_VECTOR_FIELDS = [
    "avg_toxicity",
    "max_toxicity",
    "num_toxic_messages",
    "max_consecutive_toxic",
    "sender_imbalance",
    "escalation",
    "age_disparity",
    "is_long_friendship",
    "secrecy_score",
    "pii_request_score",
    "boundary_pressure_score",
]

def extract_features(analyzed_messages: List[MessageAnalysis], metadata: ConversationMetadata = None) -> ConversationFeatures:
    """Convert list of analyzed messages and metadata into conversation-level features."""
    features = ConversationFeatures()
    
    if not analyzed_messages:
        return features

    if metadata is None:
        metadata = ConversationMetadata(friendship_duration_days=100, sender_age=25, receiver_age=25)
        
    # Metadata features
    sender_age = metadata.sender_age
    receiver_age = metadata.receiver_age
    features.age_disparity = abs(sender_age - receiver_age)
    features.is_long_friendship = 1.0 if metadata.friendship_duration_days > 180 else 0.0

    tox_scores = [m.toxicity for m in analyzed_messages]
    features.avg_toxicity = sum(tox_scores) / len(tox_scores)
    features.max_toxicity = max(tox_scores)
    
    is_toxic = [t > 0.5 for t in tox_scores]
    features.num_toxic_messages = sum(is_toxic)
    
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
    features.max_consecutive_toxic = max_consec
    
    # Sender imbalance
    senders = [m.sender for m in analyzed_messages if m.sender]
    if senders:
        initiator = senders[0]
        init_count = sum(1 for s in senders if s == initiator)
        features.sender_imbalance = init_count / len(senders)
        
    # Escalation
    if len(tox_scores) > 1:
        import numpy as np
        x = np.arange(len(tox_scores))
        try:
            slope, _ = np.polyfit(x, tox_scores, 1)
            features.escalation = float(slope)
        except Exception:
            features.escalation = 0.0

    full_text = " ".join(m.text.lower() for m in analyzed_messages)
    secrecy_markers = ["secret", "don't tell", "keep this", "between us"]
    pii_markers = ["address", "location", "phone", "number", "where do you live"]
    pressure_markers = ["if you care", "prove it", "you promised", "answer right now"]
    features.secrecy_score = min(1.0, sum(full_text.count(marker) for marker in secrecy_markers) / 3.0)
    features.pii_request_score = min(1.0, sum(full_text.count(marker) for marker in pii_markers) / 3.0)
    features.boundary_pressure_score = min(1.0, sum(full_text.count(marker) for marker in pressure_markers) / 3.0)

    return features


def build_feature_vector(features: ConversationFeatures) -> List[float]:
    feature_map = features.to_dict()
    return [float(feature_map.get(field, 0.0)) for field in FEATURE_VECTOR_FIELDS]
