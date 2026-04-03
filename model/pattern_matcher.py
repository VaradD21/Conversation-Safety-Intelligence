import re
from typing import List

from model.schemas import ConversationMetadata, MessageAnalysis, PatternEvidence, PatternMatchResult

PHASE_RULES = {
    "trust": {
        "keywords": ["trust me", "best friend", "only one", "understand you", "don't tell"],
        "weight": 0.3,
    },
    "isolation": {
        "keywords": ["delete this", "keep it secret", "don't tell your mom", "your parents", "our secret"],
        "weight": 0.55,
    },
    "meetup": {
        "keywords": ["meet", "address", "location", "where are you", "outside", "come over", "asl"],
        "weight": 0.65,
    },
}

SCORING_RULES = {
    "pii_leak_detected": {
        "keywords": ["live at", "my address is", "address", "location", "phone", "number"],
        "weight": 0.85,
        "category": "pii_risk",
        "detail": "Conversation includes contact or location-sharing language.",
    },
    "boundary_pressure": {
        "keywords": ["if you care", "prove it", "you promised", "answer right now", "don't avoid me"],
        "weight": 0.5,
        "category": "coercion",
        "detail": "Conversation contains manipulative or pressuring language.",
    },
}

def _collect_keyword_hits(messages: List[MessageAnalysis], keywords: List[str]) -> List[int]:
    hits = []
    for index, message in enumerate(messages):
        lowered = message.text.lower()
        if any(keyword in lowered for keyword in keywords):
            hits.append(index)
    return hits


def _append_weighted_evidence(result: PatternMatchResult, flag: str, indices: List[int], matched_text: List[str], detail: str, category: str, weight: float) -> None:
    if not indices:
        return
    if flag not in result.flags:
        result.flags.append(flag)
    result.evidence.append(PatternEvidence(
        flag=flag,
        message_indices=sorted(set(indices)),
        matched_text=matched_text,
        detail=detail,
        weight=weight,
    ))
    result.category_scores[category] = max(result.category_scores.get(category, 0.0), weight)


def match_patterns(analyzed_messages: List[MessageAnalysis], metadata: ConversationMetadata = None) -> PatternMatchResult:
    """
    Detect harmful behavioral patterns and the 'Grooming Lifecycle' phase.
    """
    result = PatternMatchResult(detected_phase="Normal", category_scores={
        "harassment": 0.0,
        "grooming": 0.0,
        "pii_risk": 0.0,
        "deception": 0.0,
        "coercion": 0.0,
    })
    
    if not analyzed_messages:
        return result

    if metadata is None:
        metadata = ConversationMetadata(friendship_duration_days=100, sender_age=25, receiver_age=25)

    full_text = " ".join([m.text.lower() for m in analyzed_messages])

    # 1. PII Detection (Minimal Regex for Demo)
    # Matches simple phone numbers or common address keywords
    phone_pattern = r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"
    pii_indices = []
    if re.search(phone_pattern, full_text):
        pii_indices.extend(_collect_keyword_hits(analyzed_messages, ["phone", "number"]))
    pii_rule = SCORING_RULES["pii_leak_detected"]
    pii_indices.extend(_collect_keyword_hits(analyzed_messages, pii_rule["keywords"]))
    _append_weighted_evidence(
        result,
        "pii_leak_detected",
        pii_indices,
        ["address/location/phone disclosure"],
        pii_rule["detail"],
        pii_rule["category"],
        pii_rule["weight"],
    )

    boundary_rule = SCORING_RULES["boundary_pressure"]
    boundary_indices = _collect_keyword_hits(analyzed_messages, boundary_rule["keywords"])
    _append_weighted_evidence(
        result,
        "boundary_pressure",
        boundary_indices,
        ["manipulative or coercive language"],
        boundary_rule["detail"],
        boundary_rule["category"],
        boundary_rule["weight"],
    )

    # 2. Identity Deception / Trap Check
    # Look for "I am [age]" and compare to verified metadata.
    # IMPORTANT: Only flag if sender_age was explicitly provided (not default 25).
    # A teen saying "I'm 14" is truthful — we should NOT flag that.
    # We flag if: an adult sender (explicitly set >= 20) claims to be a child (<18)
    # AND at least one other risk signal is present (grooming, meetup, PII, pressure).
    age_claims = re.findall(r"i am (\d+)", full_text)
    age_claims += re.findall(r"i'm (\d+)", full_text)
    age_claims += re.findall(r"im (\d+)", full_text)

    SENDER_AGE_DEFAULT = 25  # The API default — means "not explicitly set"

    for claim in age_claims:
        claimed_age = int(claim)
        actual_age = metadata.sender_age

        # Skip if this is the default placeholder value — we can't assume deception
        if actual_age == SENDER_AGE_DEFAULT:
            continue

        # Skip if the claim is plausibly consistent with actual age (±5 years)
        if abs(actual_age - claimed_age) <= 5:
            continue

        # Only flag meaningful adult → child deception
        if actual_age >= 20 and claimed_age < 18:
            # Require at least one co-occurring risk signal to reduce false positives
            existing_risk_flags = [f for f in result.flags if f in (
                "suspected_grooming", "pii_leak_detected", "boundary_pressure",
                "grooming_meetup", "grooming_secrecy", "pii_extraction"
            )]
            has_context = bool(existing_risk_flags) or any(
                score > 0.3 for score in result.category_scores.values()
            )

            if has_context:
                _append_weighted_evidence(
                    result,
                    "identity_deception",
                    _collect_keyword_hits(analyzed_messages, [f"i am {claim}", f"i'm {claim}", f"im {claim}"]),
                    [f"claimed age {claim}"],
                    f"Sender's verified profile age is {actual_age}, but conversation claims age {claim} alongside other risk signals.",
                    "deception",
                    1.0,
                )

    # 3. Grooming Lifecycle Phase Detection
    # We look at keywords and their chronological appearance
    trust_keywords = PHASE_RULES["trust"]["keywords"]
    isolation_keywords = PHASE_RULES["isolation"]["keywords"]
    meetup_keywords = PHASE_RULES["meetup"]["keywords"]
    trust_hits = _collect_keyword_hits(analyzed_messages, trust_keywords)
    isolation_hits = _collect_keyword_hits(analyzed_messages, isolation_keywords)
    meetup_hits = _collect_keyword_hits(analyzed_messages, meetup_keywords)
    has_trust = bool(trust_hits)
    has_isolation = bool(isolation_hits)
    has_meetup = bool(meetup_hits)

    if has_meetup and (has_isolation or has_trust):
        result.detected_phase = "Phase 3: Escalation/Meetup"
        _append_weighted_evidence(
            result,
            "suspected_grooming",
            trust_hits + isolation_hits + meetup_hits,
            ["trust/isolation/meetup sequence"],
            "Trust-building, secrecy, and meetup cues appear in the same conversation.",
            "grooming",
            0.95,
        )
    elif has_isolation:
        result.detected_phase = "Phase 2: Isolation Detected"
        result.category_scores["grooming"] = max(result.category_scores["grooming"], PHASE_RULES["isolation"]["weight"])
    elif has_trust:
        result.detected_phase = "Phase 1: Trust Building"
        result.category_scores["grooming"] = max(result.category_scores["grooming"], PHASE_RULES["trust"]["weight"])

    # 4. Standard Harassment (from previous version)
    is_toxic = [m.toxicity > 0.5 for m in analyzed_messages]
    if sum(is_toxic) >= 3:
        toxic_indices = [idx for idx, is_flagged in enumerate(is_toxic) if is_flagged]
        _append_weighted_evidence(
            result,
            "repeated_harassment",
            toxic_indices,
            ["multiple toxic messages"],
            "Three or more messages crossed the toxicity threshold.",
            "harassment",
            0.8,
        )

    result.flags = list(dict.fromkeys(result.flags))
    return result
