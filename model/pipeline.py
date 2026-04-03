import uuid
from typing import List, Dict, Any

from model.message_analyzer import analyze_message
from model.feature_extractor import extract_features
from model.pattern_matcher import match_patterns
from model.decision_engine import classify
from model.explainer import generate_explanation
from model.age_inference import build_age_profiles
from model.semantic_engine import get_semantic_flags
from model.image_analyzer import analyze_image
from model import database
from model.schemas import AnalysisResult, ConversationMetadata, MessageAnalysis, PatternEvidence
from model.ai_judge import get_ai_judgment

# Initialize the database when pipeline is loaded
try:
    database.init_db()
except Exception as e:
    print(f"Warning: Failed to initialize memory DB: {e}")


def analyze_conversation_core(conversation: List[Dict[str, str]], metadata: Dict[str, Any] = None) -> AnalysisResult:
    """
    Full analysis pipeline:
      1. NLP toxicity + sentiment per message
      2. Feature extraction (behavioral metrics)
      3. Keyword pattern matching (grooming lifecycle, PII, etc.)
      4. Semantic intent detection (catches slang/obfuscation)
      5. Linguistic age inference (no manual age required)
      6. Decision engine (ML + rule overrides + history)
      7. AI reasoning layer (GPT-4o / Mistral)
    """
    metadata_obj = ConversationMetadata.from_dict(metadata)
    sender_id = metadata_obj.sender_id

    if not conversation:
        return AnalysisResult(
            risk_level="safe",
            confidence=1.0,
            reason="Empty conversation.",
        )

    # STEP 1: Per-message NLP and Image analysis
    analyzed_messages: List[MessageAnalysis] = []
    for msg in conversation:
        analysis_dict = analyze_message(msg.get("text", ""), msg.get("sender", "unknown"))
        
        # Inject image parsing results
        b64 = msg.get("image_base64")
        if b64:
            is_nsfw, score, label = analyze_image(b64)
            analysis_dict["is_nsfw_image"] = is_nsfw
            analysis_dict["nsfw_score"] = score
            analysis_dict["image_base64"] = "<hidden_for_logs>" # don't leak huge base64 in trace
            
            if is_nsfw:
                analysis_dict["text"] += f" [System Auto-flag: NSFW Image Detected ({label})]"
            
        analyzed_messages.append(MessageAnalysis.from_dict(analysis_dict))

    # STEP 2: Load user memory
    try:
        user_record = database.get_user(sender_id)
        user_risk_score = user_record.get("risk_score", 0)
    except Exception:
        user_risk_score = 0

    # STEP 3: Feature extraction
    features = extract_features(analyzed_messages, metadata_obj)

    # STEP 4: Keyword pattern matching
    patterns = match_patterns(analyzed_messages, metadata_obj)

    # STEP 5: Semantic intent detection (slang/emoji/obfuscation bypass)
    try:
        semantic_flags, semantic_hits = get_semantic_flags(conversation, threshold=0.55)
        for sem_flag in semantic_flags:
            if sem_flag not in patterns.flags:
                patterns.flags.append(sem_flag)
                patterns.evidence.append(PatternEvidence(
                    flag=sem_flag,
                    message_indices=[h["message_index"] for h in semantic_hits if h["matched_intent"] == sem_flag],
                    matched_text=[h["message_text"][:80] for h in semantic_hits if h["matched_intent"] == sem_flag],
                    detail=f"Semantic intent detected (similarity-based). Category: {sem_flag}",
                    weight=max((h["weight"] for h in semantic_hits if h["matched_intent"] == sem_flag), default=0.6),
                ))
    except Exception as e:
        print(f"Warning: Semantic engine error: {e}")

    # STEP 6: Age Inference (replaces manual age input requirement)
    try:
        age_profiles = build_age_profiles(conversation)
        # Inject age inference results into metadata if sender_age is not provided
        primary_sender = conversation[0].get("sender", "unknown") if conversation else "unknown"
        if metadata_obj.sender_age == 25 and primary_sender in age_profiles:  # 25 is the default "unknown" value
            profile = age_profiles[primary_sender]
            if profile["category"] == "adult":
                metadata_obj.sender_age = 35  # Representative adult age
            elif profile["category"] == "teen":
                metadata_obj.sender_age = 15
            elif profile["category"] == "child":
                metadata_obj.sender_age = 11

            # If mimicry detected (adult pretending to be young), force identity deception flag
            if profile["mimicry_detected"] and "identity_deception" not in patterns.flags:
                patterns.flags.append("identity_deception")
                patterns.evidence.append(PatternEvidence(
                    flag="identity_deception",
                    message_indices=list(range(len(analyzed_messages))),
                    matched_text=["Age mimicry signals detected in linguistic analysis"],
                    detail="Sender's language patterns indicate they are an adult while attempting to appear young.",
                    weight=1.0,
                ))

            # If extraction detected, boost PII flag
            if profile["extraction_detected"] and "pii_leak_detected" not in patterns.flags:
                patterns.flags.append("pii_leak_detected")
    except Exception as e:
        print(f"Warning: Age inference error: {e}")
        age_profiles = {}

    # STEP 7: Decision engine
    decision = classify(features, patterns, metadata_obj)

    reason = generate_explanation(features, patterns, decision)

    flagged_messages = sorted(set(
        index
        for index, msg in enumerate(analyzed_messages)
        if msg.toxicity > 0.7
    ) | set(
        evidence_index
        for evidence in patterns.evidence
        for evidence_index in evidence.message_indices
    ))

    # STEP 8: AI Reasoning Layer — runs for all non-safe outcomes
    ai_result = {}
    if decision.risk_level != "safe" or decision.repeat_offender or len(patterns.flags) > 0:
        try:
            ai_result = get_ai_judgment(
                conversation,
                decision.risk_level,
                patterns.flags,
                patterns.detected_phase,
                age_profiles,
            )

            # If AI upgrades the risk level, respect it (zero false negatives)
            ai_final_risk = ai_result.get("final_risk", decision.risk_level)
            risk_order = {"safe": 0, "warning": 1, "hazardous": 2}
            if risk_order.get(ai_final_risk, 0) > risk_order.get(decision.risk_level, 0):
                decision.risk_level = ai_final_risk
                decision.decision_trace.append(f"ai_judge_upgraded_to_{ai_final_risk}")
        except Exception as e:
            print(f"Warning: AI Judge failed: {e}")

    ai_judgment_text = ai_result.get("reason", "")
    if ai_result.get("action_recommended"):
        ai_judgment_text += f" Recommended action: {ai_result['action_recommended']}"

    return AnalysisResult(
        risk_level=decision.risk_level,
        confidence=max(decision.confidence, ai_result.get("confidence", 0.0)),
        reason=reason,
        flagged_messages=flagged_messages,
        behavioral_flags=patterns.flags,
        detected_phase=patterns.detected_phase,
        evidence=patterns.evidence,
        category_scores=decision.category_scores,
        decision_trace=decision.decision_trace,
        user_risk_score=user_risk_score,
        repeat_offender=decision.repeat_offender,
        ai_judgment=ai_judgment_text,
        threat_category=ai_result.get("threat_category", "unknown"),
        action_recommended=ai_result.get("action_recommended", ""),
    )


def analyze_conversation(conversation: List[Dict[str, str]], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run analysis and persist the final decision for longitudinal tracking.
    """
    metadata_obj = ConversationMetadata.from_dict(metadata)
    conversation_id = metadata_obj.conversation_id or str(uuid.uuid4())
    result = analyze_conversation_core(conversation, metadata_obj.to_dict())

    try:
        persisted = database.persist_analysis_result(
            conversation_id,
            metadata_obj.sender_id,
            result.risk_level,
            result.confidence,
            result.ai_judgment,
            result.threat_category
        )
        result.user_risk_score = persisted.get("user_risk_score", result.user_risk_score)
    except Exception as e:
        print(f"Warning: Database error: {e}")

    return result.to_dict()
