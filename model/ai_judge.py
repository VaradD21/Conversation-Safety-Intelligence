"""
AI Judge — Free Multi-Provider Reasoning Layer
===============================================
Provider priority:
  1. Google Gemini 1.5 Flash  — Free (1,500 req/day). Best quality/cost ratio.
  2. Groq (Llama-3.3-70B)     — Free tier. Fastest inference available.
  3. HuggingFace Qwen-2.5-72B — Always-available fallback with your HF token.

Get free API keys:
  Gemini : https://aistudio.google.com/app/apikey
  Groq   : https://console.groq.com
"""
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
HF_TOKEN       = os.getenv("HF_API_TOKEN")

# ---------------------------------------------------------------
# Shared prompt template
# ---------------------------------------------------------------
SYSTEM_PROMPT = """You are a government-certified Child Safety AI monitoring system.
Your job is to protect children by analyzing chat conversations detected as potentially dangerous.

You will receive:
  1. The raw conversation transcript
  2. Behavioral flags raised by the automated system
  3. An inferred age analysis for each sender

You MUST respond in valid JSON with this EXACT format:
{
  "final_risk": "safe" | "warning" | "hazardous",
  "reason": "A 2-3 sentence plain-language explanation for a parent",
  "threat_category": "grooming" | "bullying" | "sextortion" | "stranger_danger" | "drug_solicitation" | "radicalization" | "self_harm" | "financial_fraud" | "age_deception" | "safe",
  "action_recommended": "A single actionable instruction for the parent",
  "confidence": 0.0
}

CRITICAL RULES:
- Prioritize child safety. A false NEGATIVE is always worse than a false POSITIVE.
- If there is ANY ambiguity, lean toward warning or hazardous.
- Write plain language. No technical jargon.
- ONLY output valid JSON. No extra text before or after."""


def _build_user_prompt(conversation, system_flags, age_profiles, risk_level, detected_phase) -> str:
    convo_text = "\n".join([f"  {m['sender']}: {m['text']}" for m in conversation])
    profiles_text = ""
    for sender, profile in age_profiles.items():
        cat = profile.get("category", "unknown")
        conf = profile.get("confidence", 0)
        alerts = []
        if profile.get("mimicry_detected"):
            alerts.append("⚠️ AGE MIMICRY")
        if profile.get("extraction_detected"):
            alerts.append("⚠️ EXTRACTION ATTEMPT")
        alert_str = "  ".join(alerts)
        profiles_text += f"  {sender}: Likely {cat} (confidence: {conf}) {alert_str}\n"

    return f"""=== CONVERSATION ===
{convo_text}

=== AUTOMATED SYSTEM FLAGS ===
Risk Level: {risk_level}
Phase: {detected_phase}
Behavioral Flags: {system_flags}

=== INFERRED AGE PROFILES ===
{profiles_text if profiles_text else '  No profiles available.'}

Respond with your JSON verdict now."""


def _extract_json(text: str) -> dict:
    """Extract a JSON object from a model response that may have extra text."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError("No valid JSON block found in response.")


# ---------------------------------------------------------------
# Provider 1: Google Gemini 2.0 Flash (FREE - 1500/day, new SDK)
# ---------------------------------------------------------------
def _call_gemini(user_prompt: str) -> dict:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=500,
        )
    )
    return json.loads(response.text)


# ---------------------------------------------------------------
# Provider 2: Groq — Llama-3.3-70B (FREE tier)
# ---------------------------------------------------------------
def _call_groq(user_prompt: str) -> dict:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.3,
        max_tokens=400,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------
# Provider 3: HuggingFace Qwen-2.5-72B (confirmed working fallback)
# ---------------------------------------------------------------
def _call_huggingface(user_prompt: str) -> dict:
    from huggingface_hub import InferenceClient
    client = InferenceClient(api_key=HF_TOKEN)
    response = client.chat_completion(
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt}
        ],
        max_tokens=500,
        temperature=0.3,
    )
    return _extract_json(response.choices[0].message.content)


# ---------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------
def get_ai_judgment(
    conversation: List[Dict[str, str]],
    risk_level: str,
    behavioral_flags: List[str],
    detected_phase: str,
    age_profiles: Dict = None,
) -> Dict:
    """
    Call the best available free AI provider for a structured safety verdict.
    Returns dict with keys: final_risk, reason, threat_category, action_recommended, confidence.
    """
    default = {
        "final_risk": risk_level,
        "reason": "",
        "threat_category": "unknown",
        "action_recommended": "Monitor this conversation and consult a trusted adult if concerned.",
        "confidence": 0.5,
    }

    if not any([GEMINI_API_KEY, GROQ_API_KEY, HF_TOKEN]):
        default["error"] = "No AI provider API keys configured."
        return default

    user_prompt = _build_user_prompt(
        conversation, behavioral_flags, age_profiles or {}, risk_level, detected_phase
    )

    providers = []
    if GEMINI_API_KEY:
        providers.append(("Gemini Flash",  _call_gemini))
    if GROQ_API_KEY:
        providers.append(("Groq Llama-3",  _call_groq))
    if HF_TOKEN:
        providers.append(("HuggingFace",   _call_huggingface))

    for name, fn in providers:
        try:
            result = fn(user_prompt)
            print(f"✅ AI Judge: {name} responded successfully.")
            return {**default, **result}
        except Exception as e:
            print(f"⚠️  AI Judge ({name}) Error: {str(e)[:120]}")

    default["error"] = "All AI providers failed."
    return default


if __name__ == "__main__":
    test = get_ai_judgment(
        [{"sender": "Stranger", "text": "You are so mature for your age, let us keep this between us and meet after school"}],
        "hazardous",
        ["suspected_grooming", "grooming_secrecy"],
        "Phase 3: Escalation",
        {"Stranger": {"category": "adult", "confidence": 0.91, "mimicry_detected": True, "extraction_detected": True, "signals": []}}
    )
    print(json.dumps(test, indent=2))
