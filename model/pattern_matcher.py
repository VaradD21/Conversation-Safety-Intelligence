import re
from typing import List, Dict, Any

PHASE_KEYWORDS = {
    "trust": ["trust me", "best friend", "only one", "understand you", "don't tell"],
    "isolation": ["delete this", "keep it secret", "don't tell your mom", "your parents", "our secret"],
    "meetup": ["meet", "address", "location", "where are you", "outside", "come over", "asl"]
}

def match_patterns(analyzed_messages: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Detect harmful behavioral patterns and the 'Grooming Lifecycle' phase.
    """
    flags = []
    detected_phase = "Normal"
    
    if not analyzed_messages:
        return {"flags": flags, "detected_phase": detected_phase}

    if metadata is None:
        metadata = {"friendship_duration_days": 100, "sender_age": 25, "receiver_age": 25}

    full_text = " ".join([m.get("text", "").lower() for m in analyzed_messages])

    # 1. PII Detection (Minimal Regex for Demo)
    # Matches simple phone numbers or common address keywords
    phone_pattern = r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"
    if re.search(phone_pattern, full_text):
        flags.append("pii_leak_detected")
    if "live at" in full_text or "my address is" in full_text:
        flags.append("pii_leak_detected")

    # 2. Identity Deception / Trap Check
    # Look for "I am [age]" and compare to metadata
    age_claims = re.findall(r"i am (\d+)", full_text)
    age_claims += re.findall(r"i'm (\d+)", full_text)
    
    for claim in age_claims:
        claimed_age = int(claim)
        actual_age = metadata.get("sender_age", 25)
        # If adult claims to be a child (<18)
        if actual_age >= 20 and claimed_age < 18:
            flags.append("identity_deception")

    # 3. Grooming Lifecycle Phase Detection
    # We look at keywords and their chronological appearance
    has_trust = any(k in full_text for k in PHASE_KEYWORDS["trust"])
    has_isolation = any(k in full_text for k in PHASE_KEYWORDS["isolation"])
    has_meetup = any(k in full_text for k in PHASE_KEYWORDS["meetup"])

    if has_meetup and (has_isolation or has_trust):
        detected_phase = "Phase 3: Escalation/Meetup"
        flags.append("suspected_grooming")
    elif has_isolation:
        detected_phase = "Phase 2: Isolation Detected"
    elif has_trust:
        detected_phase = "Phase 1: Trust Building"

    # 4. Standard Harassment (from previous version)
    is_toxic = [m.get("toxicity", 0.0) > 0.5 for m in analyzed_messages]
    if sum(is_toxic) >= 3:
        flags.append("repeated_harassment")

    return {
        "flags": list(set(flags)),
        "detected_phase": detected_phase
    }
