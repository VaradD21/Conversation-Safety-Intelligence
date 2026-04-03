"""
Age Inference Engine
====================
Infers approximate age category from chat behavior and linguistics alone.
No manual age input required. The system learns to detect whether a sender
behaves like a child, teen, or adult — and flags mismatches as potential deception.

Age Categories:
  - "child"  : likely < 13
  - "teen"   : likely 13–17
  - "adult"  : likely 18+
  - "unknown": insufficient data
"""
import re
from typing import Dict, List

# Vocabulary signals for each age group
CHILD_VOCAB = {
    "hehe", "teehee", "lol", "omg", "bestie", "slay", "ngl", "lowkey",
    "periodt", "sussy", "baka", "oof", "bruh", "uwu", "owo", "sksksk",
    "aaaaa", "yeet", "vibe check", "no cap", "its giving", "fr fr"
}
TEEN_VOCAB = {
    "wsp", "wya", "wyd", "tbh", "imo", "smh", "idk", "nvm", "btw",
    "lmao", "lmfao", "rn", "bc", "bc of", "yk", "deadass", "bro",
    "dude", "bffr", "istg", "ong", "finna", "tryna"
}
ADULT_COMPLEX = {
    "regardless", "however", "certainly", "understand", "relationship",
    "responsibility", "appreciate", "consider", "situation", "comfortable",
    "private", "mature", "experience", "honest", "trust", "secret",
    "special", "nobody needs to know", "between us", "just the two of us"
}

# Predatory adult mimicry signals (adult pretending to be young)
MIMICRY_SIGNALS = [
    r"\bi[' ]?m (also |so )?(young|young too|young as well)\b",
    r"\bsame age as you\b",
    r"\bi[' ]?m \d{1,2} (too|as well|also)\b",
    r"\bwe[' ]?re the same age\b",
    r"\bi know how (you|kids|teens) feel\b",
    r"\bi was young once\b",
    r"\byou[' ]?re so mature for your age\b",
    r"\byou[' ]?re not like other kids\b",
    r"\byou[' ]?re different from other (kids|teens|children)\b",
    r"\bspecial (friend|relationship|bond)\b",
    r"\bonlyfans\b",
    r"\bwant to see something\b",
]

# Extraction-focused adult probing patterns
EXTRACTION_SIGNALS = [
    r"\bwhere (do you live|are you|do you go to school)\b",
    r"\bwhat school\b",
    r"\bsend (me )?(your )?(pic|photo|selfie|location|address)\b",
    r"\bdo you have (instagram|snap|snapchat|discord|telegram|whatsapp)\b",
    r"\badd me on\b",
    r"\bcome (over|meet me|to my place)\b",
    r"\bjust (us|me and you|the two of us)\b",
    r"\bkeep (it|this) (secret|between us|private|quiet)\b",
    r"\bdon[' ]?t tell (your|the) (mom|dad|parents|teacher)\b",
    r"\bi[' ]?ll (give|send|buy) you\b",
    r"\bsurprise for you\b",
]


def _count_vocab_hits(text_lower: str, vocab: set) -> int:
    return sum(1 for word in vocab if word in text_lower)


def infer_sender_age_category(messages_from_sender: List[str]) -> Dict[str, object]:
    """
    Analyze all messages from a single sender and return an age category inference.
    
    Returns:
        {
          "category": "child" | "teen" | "adult" | "unknown",
          "confidence": float (0.0-1.0),
          "mimicry_detected": bool,
          "extraction_detected": bool,
          "signals": List[str]  -- human-readable signals found
        }
    """
    if not messages_from_sender:
        return {"category": "unknown", "confidence": 0.0, "mimicry_detected": False, "extraction_detected": False, "signals": []}

    full_text = " ".join(messages_from_sender).lower()
    signals = []

    child_score = _count_vocab_hits(full_text, CHILD_VOCAB)
    teen_score = _count_vocab_hits(full_text, TEEN_VOCAB)
    adult_score = _count_vocab_hits(full_text, ADULT_COMPLEX)

    # Sentence length analysis: adults write longer sentences
    word_counts = [len(m.split()) for m in messages_from_sender if m.strip()]
    avg_words = sum(word_counts) / len(word_counts) if word_counts else 0
    if avg_words > 12:
        adult_score += 2
        signals.append(f"Long average sentence length ({avg_words:.1f} words)")
    elif avg_words < 5:
        child_score += 1
        teen_score += 1

    # Punctuation complexity: adults use commas, semicolons more
    punct_ratio = full_text.count(",") + full_text.count(";") + full_text.count(".")
    if punct_ratio > 5:
        adult_score += 1

    # Mimicry detection: adult trying to sound young
    mimicry_detected = False
    for pattern in MIMICRY_SIGNALS:
        if re.search(pattern, full_text):
            mimicry_detected = True
            signals.append(f"Mimicry pattern: '{pattern[:40]}...'")

    # Extraction / solicitation detection
    extraction_detected = False
    for pattern in EXTRACTION_SIGNALS:
        if re.search(pattern, full_text):
            extraction_detected = True
            signals.append(f"Extraction attempt: '{pattern[:40]}...'")

    # Scoring
    total = child_score + teen_score + adult_score
    if total == 0:
        category = "unknown"
        confidence = 0.3
    elif adult_score > child_score and adult_score > teen_score:
        category = "adult"
        confidence = min(0.95, 0.5 + (adult_score / max(total, 1)) * 0.5)
        signals.append(f"Adult vocabulary score: {adult_score}")
    elif teen_score >= child_score:
        category = "teen"
        confidence = min(0.85, 0.4 + (teen_score / max(total, 1)) * 0.45)
        signals.append(f"Teen vocabulary score: {teen_score}")
    else:
        category = "child"
        confidence = min(0.85, 0.4 + (child_score / max(total, 1)) * 0.45)
        signals.append(f"Child vocabulary score: {child_score}")

    # If mimicry is detected, we upgrade to suspicious even if they scored teen/child
    if mimicry_detected:
        category = "adult"
        confidence = max(confidence, 0.82)
        signals.append("ALERT: Sender appears to be mimicking a younger age.")

    return {
        "category": category,
        "confidence": round(confidence, 3),
        "mimicry_detected": mimicry_detected,
        "extraction_detected": extraction_detected,
        "signals": signals
    }


def build_age_profiles(messages: List[Dict]) -> Dict[str, Dict]:
    """
    Build an age profile for every unique sender in the conversation.
    
    Args:
        messages: List of {"sender": str, "text": str} dicts
        
    Returns:
        Dict mapping sender -> age profile
    """
    sender_messages: Dict[str, List[str]] = {}
    for msg in messages:
        sender = msg.get("sender", "unknown")
        text = msg.get("text", "")
        if sender not in sender_messages:
            sender_messages[sender] = []
        sender_messages[sender].append(text)

    profiles = {}
    for sender, texts in sender_messages.items():
        profiles[sender] = infer_sender_age_category(texts)

    return profiles


if __name__ == "__main__":
    test_messages = [
        {"sender": "Stranger", "text": "Hey! I'm 14 too, we're the same age."},
        {"sender": "Stranger", "text": "You're so mature for your age, you know that?"},
        {"sender": "Stranger", "text": "Let's keep this between us. Don't tell your mom."},
        {"sender": "Stranger", "text": "Can you send me a selfie? I'll send you a surprise."},
        {"sender": "Child", "text": "omg hehe bruh what is going on lmao"},
        {"sender": "Child", "text": "ngl that's kinda sus oof"},
    ]
    profiles = build_age_profiles(test_messages)
    for sender, profile in profiles.items():
        print(f"\n[{sender}] Category: {profile['category']} (confidence: {profile['confidence']})")
        print(f"  Mimicry: {profile['mimicry_detected']}, Extraction: {profile['extraction_detected']}")
        for signal in profile['signals']:
            print(f"  → {signal}")
