from typing import Dict, Any

def generate_explanation(features: Dict[str, Any], patterns: Dict[str, Any], decision: Dict[str, Any]) -> str:
    """Generate human-readable reasoning based on inputs and decision."""
    rl = decision.get("risk_level", "safe")
    flags = patterns.get("flags", [])
    phase = patterns.get("detected_phase", "Normal")
    
    reasons = []
    
    if rl == "safe":
        return "No significant toxic patterns or harmful behaviors detected."

    if "identity_deception" in flags:
        reasons.append("suspected identity deception based on age claims")
    if "suspected_grooming" in flags:
        reasons.append(f"grooming indicators matched {phase.lower()}")
    if "pii_leak_detected" in flags:
        reasons.append("personal information sharing or address/phone disclosure")
    if "predatory_pattern" in flags:
        reasons.append("repeat hazardous behavior across multiple conversations")
    if "repeat_offender" in flags or decision.get("repeat_offender", False):
        reasons.append("historical risk score indicates repeat offending behavior")
    if "repeated_harassment" in flags:
        reasons.append("repeated harassment")
    if features.get("max_toxicity", 0.0) > 0.9:
        reasons.append("extremely high toxicity in a message")
    if "harmful_reply_to_vulnerable" in flags:
        reasons.append("harmful response to a vulnerable message")
    if features.get("escalation", 0.0) > 0.3:
        reasons.append("escalating toxicity trend over time")
        
    if not reasons:
        return f"Interaction classified as {rl} due to general toxicity thresholds."
        
    return f"Interaction classified as {rl} because of: " + ", ".join(reasons) + "."
