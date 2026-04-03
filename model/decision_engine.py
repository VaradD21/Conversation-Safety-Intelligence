import os
import pickle
import numpy as np
from typing import Optional

from model import database
from model.feature_extractor import build_feature_vector
from model.schemas import ConversationFeatures, ConversationMetadata, DecisionResult, PatternEvidence, PatternMatchResult

# Dynamically load the trained Random Forest model if the training script was run
clf = None
model_path = os.path.join(os.path.dirname(__file__), "..", "models", "classifier.pkl")
if os.path.exists(model_path):
    try:
        with open(model_path, "rb") as f:
            clf = pickle.load(f)
    except Exception:
        pass

HAZARD_THRESHOLDS = {
    "default": 0.9,
    "repeat_offender": 0.7,
    "high_risk_repeat_offender": 0.5,
}


def _append_flag(patterns: PatternMatchResult, flag: str, detail: str) -> None:
    if flag in patterns.flags:
        return
    patterns.flags.append(flag)
    patterns.evidence.append(PatternEvidence(flag=flag, detail=detail))


def _apply_rule_overrides(
    features: ConversationFeatures,
    patterns: PatternMatchResult,
    metadata: ConversationMetadata,
    result: DecisionResult,
) -> Optional[DecisionResult]:
    flags = patterns.flags
    if "identity_deception" in flags:
        result.risk_level = "hazardous"
        result.confidence = 1.0
        result.decision_trace.append("identity_deception_override")
        return result

    if "suspected_grooming" in flags:
        if features.age_disparity > 5 and metadata.friendship_duration_days < 30:
            result.risk_level = "hazardous"
            result.confidence = 0.95
            result.decision_trace.append("grooming_with_age_gap_override")
        else:
            result.risk_level = "warning"
            result.confidence = 0.7
            result.decision_trace.append("grooming_warning_override")
        return result

    if metadata.friendship_duration_days > 180 and features.max_toxicity < 0.8 and not result.repeat_offender:
        result.risk_level = "safe"
        result.confidence = 0.9
        result.decision_trace.append("long_friendship_safe_override")
        return result

    return None


def _run_ml_score(features: ConversationFeatures, result: DecisionResult) -> Optional[DecisionResult]:
    if clf is None:
        return None

    vector = [build_feature_vector(features)]
    probas = clf.predict_proba(vector)[0]
    max_idx = int(np.argmax(probas))
    max_p = float(probas[max_idx])
    result.confidence = max_p
    result.decision_trace.append("ml_classifier")
    if max_idx == 2 and max_p > 0.5:
        result.risk_level = "hazardous"
    elif max_idx == 1 and max_p > 0.4:
        result.risk_level = "warning"
    else:
        result.risk_level = "safe"
    return result


def classify(features: ConversationFeatures, patterns: PatternMatchResult, metadata: ConversationMetadata = None) -> DecisionResult:
    """Final classification logic using rule overrides, ML scoring, and historical risk aggregation."""
    result = DecisionResult(category_scores=dict(patterns.category_scores))

    if metadata is None:
        metadata = ConversationMetadata(friendship_duration_days=100, sender_age=25, receiver_age=25)

    sender_id = metadata.sender_id
    hazard_threshold = HAZARD_THRESHOLDS["default"]

    try:
        user_record = database.get_user(sender_id)
        user_risk_score = user_record.get("risk_score", 0)
        result.category_scores["history"] = min(1.0, user_risk_score / 20.0)

        if user_risk_score > 10:
            hazard_threshold = HAZARD_THRESHOLDS["repeat_offender"]
            result.repeat_offender = True
            _append_flag(patterns, "repeat_offender", "Sender has elevated historical risk.")
        if user_risk_score > 20:
            hazard_threshold = HAZARD_THRESHOLDS["high_risk_repeat_offender"]
            
        stats = database.get_user_interaction_stats(sender_id)
        if stats["unique_conversations"] >= 3 and stats["total_hazardous"] >= 2:
            _append_flag(patterns, "predatory_pattern", "Repeated hazardous interactions across multiple conversations.")
            result.risk_level = "hazardous"
            result.confidence = 0.99
            result.decision_trace.append("predatory_pattern_override")
            return result
    except Exception:
        result.category_scores["history"] = 0.0

    override_result = _apply_rule_overrides(features, patterns, metadata, result)
    if override_result is not None:
        return override_result

    if features.max_toxicity >= hazard_threshold:
        result.risk_level = "hazardous"
        result.confidence = 0.98
        result.decision_trace.append("toxicity_threshold_override")
        return result
    if "pii_leak_detected" in patterns.flags:
        result.risk_level = "warning"
        result.confidence = 0.85
        result.decision_trace.append("pii_warning_override")
        return result

    ml_result = _run_ml_score(features, result)
    if ml_result is not None:
        return ml_result

    if features.avg_toxicity > 0.5:
        result.risk_level = "warning"
        result.confidence = 0.6
        result.decision_trace.append("avg_toxicity_fallback")
    else:
        result.confidence = max(result.confidence, 0.75)
        result.decision_trace.append("safe_fallback")
    return result
