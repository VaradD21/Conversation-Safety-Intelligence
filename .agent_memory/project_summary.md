# Project: Conversation Safety Analyzer
Goal: Classify multi-turn conversations as safe/warning/hazardous.
Stack: Python, FastAPI, detoxify, scikit-learn, sentence-transformers.
Entry: api/main.py → POST /analyze
Output schema: {risk_level, confidence, flags[], reasoning, message_highlights[]}
Architecture: preprocessor → feature_extractor → pattern_matcher → decision_engine → explainer
