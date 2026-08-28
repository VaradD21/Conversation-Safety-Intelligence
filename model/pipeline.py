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

# Database initialization is handled by the FastAPI lifespan event in api/main.py


import concurrent.futures

TIER1_MAX_TOXICITY_THRESHOLD = 0.3
TIER1_MAX_SEMANTIC_THRESHOLD = 0.55

def _run_nlp_and_vision(conversation: List[Dict[str, str]]) -> List[MessageAnalysis]:
    analyzed_messages = []
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
    return analyzed_messages

def _run_semantic(conversation: List[Dict[str, str]]):
    try:
        return get_semantic_flags(conversation, threshold=TIER1_MAX_SEMANTIC_THRESHOLD)
    except Exception as e:
        print(f"Warning: Semantic engine error: {e}")
        return [], []

def analyze_conversation_core(conversation: List[Dict[str, str]], metadata: Dict[str, Any] = None, skip_ai_judge: bool = False) -> AnalysisResult:
    """
    Tiered analysis pipeline:
      Tier 0: Fast pattern matching (Regex/Keywords). Short-circuits if hazardous.
      Tier 1: NLP Toxicity + Semantic similarity. Short-circuits to safe if benign.
      Tier 2: Deep ML (Random Forest) + AI Reasoning (LLM Judge).
    """
    metadata_obj = ConversationMetadata.from_dict(metadata)
    sender_id = metadata_obj.sender_id

    if not conversation:
        return AnalysisResult(
            risk_level="safe",
            confidence=1.0,
            reason="Empty conversation.",
        )

    # -------------------------------------------------------------------------
    # TIER 0: FAST REGEX & RULE GATING
    # -------------------------------------------------------------------------
    # Create base messages without heavy ML processing
    base_messages = [MessageAnalysis(
        text=msg.get("text", ""), 
        sender=msg.get("sender", "unknown"),
        image_base64=msg.get("image_base64")
    ) for msg in conversation]
    
    base_patterns = match_patterns(base_messages, metadata_obj)
    base_features = extract_features(base_messages, metadata_obj)
    base_decision = classify(base_features, base_patterns, metadata_obj)
    
    # Preserve the history score fetched during base_decision
    user_risk_score = base_decision.category_scores.get("history", 0.0) * 20.0

    if base_decision.risk_level == "hazardous":
        reason = generate_explanation(base_features, base_patterns, base_decision)
        return AnalysisResult(
            risk_level="hazardous",
            confidence=base_decision.confidence,
            reason=reason,
            flagged_messages=list(set(e_idx for ev in base_patterns.evidence for e_idx in ev.message_indices)),
            behavioral_flags=base_patterns.flags,
            detected_phase=base_patterns.detected_phase,
            evidence=base_patterns.evidence,
            category_scores=base_decision.category_scores,
            decision_trace=base_decision.decision_trace + ["tier0_short_circuit_hazardous"],
            user_risk_score=int(user_risk_score),
            repeat_offender=base_decision.repeat_offender,
        )

    # -------------------------------------------------------------------------
    # TIER 1: PARALLEL NLP & SEMANTIC ANALYSIS
    # -------------------------------------------------------------------------
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_nlp = executor.submit(_run_nlp_and_vision, conversation)
        future_sem = executor.submit(_run_semantic, conversation)
        
        analyzed_messages = future_nlp.result()
        semantic_flags, semantic_hits = future_sem.result()

    max_tox = max((m.toxicity for m in analyzed_messages), default=0.0)
    has_nsfw = any(m.is_nsfw_image for m in analyzed_messages)

    # If completely clean, short circuit and skip Tier 2 completely
    if max_tox < TIER1_MAX_TOXICITY_THRESHOLD and not semantic_flags and not has_nsfw and base_decision.risk_level == "safe":
        return AnalysisResult(
            risk_level="safe",
            confidence=0.9,
            reason="Tier 1 heuristic determined conversation is benign.",
            flagged_messages=[],
            behavioral_flags=base_patterns.flags,
            detected_phase=base_patterns.detected_phase,
            evidence=base_patterns.evidence,
            category_scores=base_decision.category_scores,
            decision_trace=base_decision.decision_trace + ["tier1_short_circuit_safe"],
            user_risk_score=int(user_risk_score),
            repeat_offender=base_decision.repeat_offender,
        )

    # -------------------------------------------------------------------------
    # TIER 2: DEEP ANALYSIS (Random Forest + AI Judge)
    # -------------------------------------------------------------------------
    features = extract_features(analyzed_messages, metadata_obj)
    
    # Re-run patterns now that we have Toxicity and NSFW flags
    patterns = match_patterns(analyzed_messages, metadata_obj)
    
    # Merge semantic flags
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

    # Age Inference
    try:
        age_profiles = build_age_profiles(conversation)
        primary_sender = conversation[0].get("sender", "unknown") if conversation else "unknown"
        if metadata_obj.sender_age == 25 and primary_sender in age_profiles:
            profile = age_profiles[primary_sender]
            if profile["category"] == "adult":
                metadata_obj.sender_age = 35
            elif profile["category"] == "teen":
                metadata_obj.sender_age = 15
            elif profile["category"] == "child":
                metadata_obj.sender_age = 11

            if profile["mimicry_detected"] and "identity_deception" not in patterns.flags:
                patterns.flags.append("identity_deception")
                patterns.evidence.append(PatternEvidence(
                    flag="identity_deception",
                    message_indices=list(range(len(analyzed_messages))),
                    matched_text=["Age mimicry signals detected in linguistic analysis"],
                    detail="Sender's language patterns indicate they are an adult while attempting to appear young.",
                    weight=1.0,
                ))

            if profile["extraction_detected"] and "pii_leak_detected" not in patterns.flags:
                patterns.flags.append("pii_leak_detected")
    except Exception as e:
        print(f"Warning: Age inference error: {e}")
        age_profiles = {}

    decision = classify(features, patterns, metadata_obj)
    reason = generate_explanation(features, patterns, decision)

    flagged_messages = sorted(set(
        index for index, msg in enumerate(analyzed_messages) if msg.toxicity > 0.7
    ) | set(
        evidence_index for evidence in patterns.evidence for evidence_index in evidence.message_indices
    ))

    # AI Reasoning Layer (runs for non-safe outcomes)
    ai_result = {}
    judge_overridden = False
    
    if skip_ai_judge:
        decision.decision_trace.append("ai_judge_skipped_fast_mode")
    elif decision.risk_level != "safe" or decision.repeat_offender or len(patterns.flags) > 0:
        try:
            ai_result = get_ai_judgment(
                conversation,
                decision.risk_level,
                patterns.flags,
                patterns.detected_phase,
                age_profiles,
            )

            # Ensure AI Judge is advisory and only upgrades risk.
            ai_final_risk = ai_result.get("final_risk", decision.risk_level)
            risk_order = {"safe": 0, "warning": 1, "hazardous": 2}
            
            ai_rank = risk_order.get(ai_final_risk, 0)
            decision_rank = risk_order.get(decision.risk_level, 0)
            
            if ai_rank > decision_rank:
                decision.risk_level = ai_final_risk
                decision.decision_trace.append(f"ai_judge_upgraded_to_{ai_final_risk}")
            elif ai_rank < decision_rank:
                judge_overridden = True
                decision.decision_trace.append(f"ai_judge_ignored_downgrade_to_{ai_final_risk}")
        except Exception as e:
            print(f"Warning: AI Judge failed or timed out: {e}")
            decision.decision_trace.append("ai_judge_failed_fallback_to_rules")

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
        user_risk_score=int(user_risk_score),
        repeat_offender=decision.repeat_offender,
        ai_judgment=ai_judgment_text,
        threat_category=ai_result.get("threat_category", "unknown"),
        action_recommended=ai_result.get("action_recommended", ""),
        judge_overridden=judge_overridden,
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
