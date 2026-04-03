"""
AI Judge — Multi-Provider Reasoning Layer
==========================================
Uses a large language model to generate a final human-readable safety verdict.
Supports OpenAI GPT-4o (preferred) or HuggingFace Mistral (fallback).
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_TOKEN = os.getenv("HF_API_TOKEN")

# Structured JSON that the AI must return
SYSTEM_PROMPT = """You are a government-certified Child Safety AI monitoring system.
Your job is to protect children by analyzing chat conversations detected as potentially dangerous.
You will receive:
  1. The raw conversation transcript
  2. Behavioral flags raised by the automated system
  3. An inferred age analysis for each sender

You MUST respond in valid JSON with this exact format:
{
  "final_risk": "safe" | "warning" | "hazardous",
  "reason": "A 2-3 sentence plain-language explanation for a parent",
  "threat_category": "grooming" | "bullying" | "sextortion" | "stranger_danger" | "drug_solicitation" | "radicalization" | "self_harm" | "financial_fraud" | "age_deception" | "safe",
  "action_recommended": "A single actionable instruction for the parent",
  "confidence": 0.0-1.0
}

CRITICAL RULES:
- Prioritize child safety. A false negative (missing a real threat) is ALWAYS worse than a false positive.
- If there's ANY ambiguity about intent, lean toward warning or hazardous.
- Be authoritative, not wishy-washy.
- Plain language only. No technical jargon."""


def _build_prompt(conversation, system_flags, age_profiles, risk_level, detected_phase):
    convo_text = "\n".join([f"  {m['sender']}: {m['text']}" for m in conversation])

    profiles_text = ""
    for sender, profile in age_profiles.items():
        cat = profile.get("category", "unknown")
        conf = profile.get("confidence", 0)
        mimicry = "⚠️ MIMICRY DETECTED" if profile.get("mimicry_detected") else ""
        extraction = "⚠️ EXTRACTION ATTEMPT" if profile.get("extraction_detected") else ""
        alerts = " ".join(filter(None, [mimicry, extraction]))
        profiles_text += f"  {sender}: Likely {cat} (confidence: {conf}) {alerts}\n"

    return f"""=== CONVERSATION TRANSCRIPT ===
{convo_text}

=== AUTOMATED SYSTEM FLAGS ===
  Risk Level: {risk_level}
  Detected Phase: {detected_phase}
  Behavioral Flags: {system_flags}

=== INFERRED AGE PROFILES ===
{profiles_text}

Provide your safety verdict as JSON."""


def _call_openai(user_prompt: str) -> dict:
    """Call OpenAI GPT-4o for the AI judgment."""
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=400,
    )
    import json
    return json.loads(response.choices[0].message.content)


def _call_huggingface(user_prompt: str) -> dict:
    """Call HuggingFace Mistral as fallback."""
    from huggingface_hub import InferenceClient
    import json
    client = InferenceClient(api_key=HF_TOKEN)
    response = client.chat_completion(
        model="mistralai/Mistral-7B-Instruct-v0.3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=400,
        temperature=0.3,
    )
    content = response.choices[0].message.content.strip()
    # Try to extract JSON from response
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(content[start:end])
    raise ValueError("No valid JSON in response")


def get_ai_judgment(
    conversation: List[Dict[str, str]],
    risk_level: str,
    behavioral_flags: List[str],
    detected_phase: str,
    age_profiles: Dict = None,
) -> Dict:
    """
    Feed all signal data to an LLM for final reasoning.

    Returns a structured dict:
    {
      "final_risk": str,
      "reason": str,
      "threat_category": str,
      "action_recommended": str,
      "confidence": float,
      "error": str (only if failed)
    }
    """
    default = {
        "final_risk": risk_level,
        "reason": "",
        "threat_category": "unknown",
        "action_recommended": "Monitor this conversation and consult a trusted adult if concerned.",
        "confidence": 0.5,
    }

    if not OPENAI_API_KEY and not HF_TOKEN:
        default["error"] = "No API token configured."
        return default

    user_prompt = _build_prompt(
        conversation,
        behavioral_flags,
        age_profiles or {},
        risk_level,
        detected_phase
    )

    # Try OpenAI first, then HuggingFace
    if OPENAI_API_KEY:
        try:
            result = _call_openai(user_prompt)
            return {**default, **result}
        except Exception as e:
            print(f"AI Judge (OpenAI) Error: {e}")

    if HF_TOKEN:
        try:
            result = _call_huggingface(user_prompt)
            return {**default, **result}
        except Exception as e:
            print(f"AI Judge (HuggingFace) Error: {e}")

    default["error"] = "All AI providers failed."
    return default


if __name__ == "__main__":
    test_convo = [
        {"sender": "Stranger", "text": "You're so mature for your age."},
        {"sender": "Child", "text": "Thanks I guess"},
        {"sender": "Stranger", "text": "Let's keep this between us. Don't tell your mom."},
        {"sender": "Stranger", "text": "Send me your address I'll send you a surprise gift."},
    ]
    result = get_ai_judgment(
        test_convo,
        "hazardous",
        ["suspected_grooming", "pii_leak_detected"],
        "Phase 3: Escalation",
        {"Stranger": {"category": "adult", "confidence": 0.91, "mimicry_detected": True, "extraction_detected": True, "signals": []}}
    )
    for k, v in result.items():
        print(f"{k}: {v}")
