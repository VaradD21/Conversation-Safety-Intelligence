"""
Semantic Intent Engine
======================
Detects predatory intent using sentence-level semantic similarity.
This catches obfuscated text, slang, leetspeak, and emoji substitution
that keyword patterns completely miss.

How it works:
1. Loads a lightweight sentence embedding model (MiniLM)
2. Embeds each message in the conversation
3. Computes cosine similarity against a library of "known threat intents"
4. Returns similarity scores and matched intent categories
"""
import os
from typing import List, Dict, Tuple

import numpy as np

_model = None
_model_attempted = False
_threat_embeddings_cache = None

# ============================================================
# THREAT INTENT LIBRARY
# Each entry is a (intent_label, canonical_phrase, weight) tuple.
# The model learns to detect semantic equivalents of these phrases
# even when the actual words are different (slang, typos, emoji)
# ============================================================
THREAT_INTENTS = [
    # --- Grooming ---
    ("grooming_trust",        "you are special and I understand you better than anyone", 0.7),
    ("grooming_trust",        "you are not like other kids your age you are different", 0.7),
    ("grooming_trust",        "we have a special bond that nobody else would understand", 0.75),
    ("grooming_secrecy",      "keep this between us and do not tell your parents", 0.85),
    ("grooming_secrecy",      "this is our secret nobody needs to know about this", 0.85),
    ("grooming_secrecy",      "delete these messages so nobody finds out", 0.9),
    ("grooming_meetup",       "meet me somewhere private just the two of us", 0.9),
    ("grooming_meetup",       "come to my place after school I will take care of you", 0.9),
    ("grooming_gift",         "I will buy you a gift if you come meet me", 0.8),
    ("grooming_gift",         "I will send you money or presents do not tell anyone", 0.8),

    # --- Age Deception ---
    ("age_deception",         "I am young too the same age as you we are similar", 0.85),
    ("age_deception",         "you are so mature for your age not like other children", 0.9),
    ("age_deception",         "we are basically the same age I feel like a kid too", 0.85),

    # --- Location / PII Extraction ---
    ("pii_extraction",        "tell me where you live what is your home address", 0.95),
    ("pii_extraction",        "send me your location or tell me what school you go to", 0.95),
    ("pii_extraction",        "what time are you usually home alone", 0.9),
    ("pii_extraction",        "add me on another platform like snap discord or telegram", 0.7),

    # --- Sextortion ---
    ("sextortion_coerce",     "send me a photo or I will tell everyone your secret", 0.95),
    ("sextortion_coerce",     "I have something on you and will share it unless you comply", 0.95),
    ("sextortion_coerce",     "do what I say or I will expose you to everyone you know", 0.95),

    # --- Cyberbullying ---
    ("cyberbullying",         "nobody likes you and everyone thinks you are worthless", 0.85),
    ("cyberbullying",         "you should hurt yourself or not exist anymore", 0.95),
    ("cyberbullying",         "everyone hates you and nobody would miss you if you were gone", 0.95),

    # --- Drug Solicitation ---
    ("drug_solicitation",     "I can get you something that will make you feel really good", 0.8),
    ("drug_solicitation",     "everybody tries it at your age it is totally safe", 0.85),
    ("drug_solicitation",     "just deliver this package for me and ask no questions", 0.85),

    # --- Radicalization ---
    ("radicalization",        "the system has failed you and violence is the only answer", 0.85),
    ("radicalization",        "join our group we fight for justice by any means necessary", 0.85),

    # --- Financial Fraud ---
    ("financial_fraud",       "send me money or a gift card and I will pay you back double", 0.9),
    ("financial_fraud",       "you won a prize just send a small payment to verify", 0.9),
]


def _load_model():
    """Lazy-load the sentence transformer model. Fails gracefully."""
    global _model, _model_attempted
    if _model_attempted:
        return _model
    _model_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("✅ Semantic Engine: sentence-transformers model loaded.")
    except Exception as e:
        _model = None
        print(f"⚠️ Semantic Engine: Could not load model ({e}). Semantic scoring disabled.")
    return _model


def _get_threat_embeddings():
    """Cache the threat intent embeddings for speed."""
    global _threat_embeddings_cache
    if _threat_embeddings_cache is not None:
        return _threat_embeddings_cache
    model = _load_model()
    if model is None:
        return None
    phrases = [t[1] for t in THREAT_INTENTS]
    _threat_embeddings_cache = model.encode(phrases, convert_to_numpy=True, normalize_embeddings=True)
    return _threat_embeddings_cache


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))


def score_messages_semantically(messages: List[str], threshold: float = 0.55) -> List[Dict]:
    """
    Score a list of messages against the threat intent library.
    
    Returns a list of hits:
    [
      {
        "message_index": int,
        "message_text": str,
        "matched_intent": str,
        "similarity": float,
        "weight": float
      }
    ]
    """
    model = _load_model()
    if model is None:
        return []

    threat_embeddings = _get_threat_embeddings()
    if threat_embeddings is None:
        return []

    if not messages:
        return []

    # Encode all messages at once for efficiency
    msg_embeddings = model.encode(messages, convert_to_numpy=True, normalize_embeddings=True)

    hits = []
    for msg_idx, msg_emb in enumerate(msg_embeddings):
        best_sim = 0.0
        best_intent = ""
        best_weight = 0.0

        for threat_idx, threat_emb in enumerate(threat_embeddings):
            sim = _cosine_similarity(msg_emb, threat_emb)
            intent_label, _, intent_weight = THREAT_INTENTS[threat_idx]
            if sim > best_sim:
                best_sim = sim
                best_intent = intent_label
                best_weight = intent_weight

        if best_sim >= threshold:
            hits.append({
                "message_index": msg_idx,
                "message_text": messages[msg_idx],
                "matched_intent": best_intent,
                "similarity": round(best_sim, 3),
                "weight": best_weight,
            })

    return hits


def get_semantic_flags(messages: List[Dict[str, str]], threshold: float = 0.55) -> Tuple[List[str], List[Dict]]:
    """
    High-level interface for the pipeline.
    
    Returns:
        (flags: List[str], evidence: List[Dict])
    """
    texts = [m.get("text", "") for m in messages]
    hits = score_messages_semantically(texts, threshold)

    flags = list(dict.fromkeys(h["matched_intent"] for h in hits))
    return flags, hits


if __name__ == "__main__":
    test_msgs = [
        {"sender": "Stranger", "text": "ur so much more mature than other kiddos ur special fr"},
        {"sender": "Stranger", "text": "jus keep dis btw us ok dnt tell ur mom k? 🤫"},
        {"sender": "Stranger", "text": "l3ts m33t @ the park tmrw no 1 needz 2 kno"},
        {"sender": "Child", "text": "omg haha wsp what r we talking abt"},
    ]
    flags, evidence = get_semantic_flags(test_msgs)
    print("Flags:", flags)
    for e in evidence:
        print(f"  [{e['message_index']}] '{e['message_text'][:50]}' → {e['matched_intent']} (sim={e['similarity']})")
