from typing import Dict, Any, Optional, Tuple

_tox_model = None
_sent_model = None
_tox_model_attempted = False
_sent_model_attempted = False
_tox_model_error = ""
_sent_model_error = ""

TOXIC_KEYWORDS = {
    "hate", "worthless", "idiot", "stupid", "kill yourself", "die", "loser",
    "terrible", "disgusting", "shut up", "moron", "jump"
}
NEGATIVE_WORDS = {
    "hate", "worthless", "terrible", "awful", "bad", "angry", "disgusting", "sad"
}
POSITIVE_WORDS = {
    "great", "thanks", "love", "nice", "good", "awesome", "happy", "kind"
}


def _load_toxicity_model():
    global _tox_model, _tox_model_attempted, _tox_model_error
    if _tox_model_attempted:
        return _tox_model

    _tox_model_attempted = True
    try:
        from detoxify import Detoxify
        _tox_model = Detoxify("original")
    except Exception as exc:
        _tox_model = None
        _tox_model_error = f"{type(exc).__name__}: {exc}"
    return _tox_model


def _load_sentiment_model():
    global _sent_model, _sent_model_attempted, _sent_model_error
    if _sent_model_attempted:
        return _sent_model

    _sent_model_attempted = True
    try:
        from transformers import pipeline
        _sent_model = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment",
            top_k=1
        )
    except Exception as exc:
        _sent_model = None
        _sent_model_error = f"{type(exc).__name__}: {exc}"
    return _sent_model


def _fallback_toxicity(text: str) -> float:
    lowered = text.lower()
    hits = sum(1 for keyword in TOXIC_KEYWORDS if keyword in lowered)
    if hits == 0:
        return 0.0
    return min(0.95, 0.35 + (0.2 * hits))


def _fallback_sentiment(text: str) -> float:
    lowered = text.lower()
    positive_hits = sum(1 for word in POSITIVE_WORDS if word in lowered)
    negative_hits = sum(1 for word in NEGATIVE_WORDS if word in lowered)
    if positive_hits == negative_hits == 0:
        return 0.0
    score = (positive_hits - negative_hits) / max(positive_hits + negative_hits, 1)
    return max(-1.0, min(1.0, float(score)))


def _predict_toxicity(text: str) -> Tuple[float, Optional[str]]:
    model = _load_toxicity_model()
    if model is None:
        return _fallback_toxicity(text), "keyword_fallback"

    try:
        toxicity_results = model.predict(text)
        return float(toxicity_results["toxicity"]), None
    except Exception:
        return _fallback_toxicity(text), "keyword_fallback"


def _predict_sentiment(text: str) -> Tuple[float, Optional[str]]:
    model = _load_sentiment_model()
    if model is None:
        return _fallback_sentiment(text), "lexicon_fallback"

    try:
        sentiment_results = model(text)
    except Exception:
        return _fallback_sentiment(text), "lexicon_fallback"

    sentiment = 0.0
    if sentiment_results and isinstance(sentiment_results, list):
        if isinstance(sentiment_results[0], list):
            best_label = sentiment_results[0][0]
        else:
            best_label = sentiment_results[0]

        score = float(best_label.get("score", 0.0))
        label = best_label.get("label", "")

        if label == "LABEL_0":
            sentiment = -1.0 * score
        elif label == "LABEL_1":
            sentiment = 0.0
        elif label == "LABEL_2":
            sentiment = 1.0 * score

    return sentiment, None


def get_model_status() -> Dict[str, Any]:
    _load_toxicity_model()
    _load_sentiment_model()
    return {
        "toxicity_model_loaded": _tox_model is not None,
        "sentiment_model_loaded": _sent_model is not None,
        "toxicity_model_error": _tox_model_error,
        "sentiment_model_error": _sent_model_error
    }


def analyze_message(text: str, sender: str = "unknown") -> Dict[str, Any]:
    if not text.strip():
        return {
            "text": text,
            "sender": sender,
            "toxicity": 0.0,
            "sentiment": 0.0
        }

    toxicity, toxicity_source = _predict_toxicity(text)
    sentiment, sentiment_source = _predict_sentiment(text)

    result = {
        "text": text,
        "sender": sender,
        "toxicity": toxicity,
        "sentiment": sentiment
    }
    if toxicity_source is not None:
        result["toxicity_source"] = toxicity_source
    if sentiment_source is not None:
        result["sentiment_source"] = sentiment_source
    return result

if __name__ == "__main__":
    safe_msg = analyze_message("Hello, it's a great day!", "user1")
    toxic_msg = analyze_message("You are a terrible person and I hate you.", "user2")
    print("Safe message:", safe_msg)
    print("Toxic message:", toxic_msg)
