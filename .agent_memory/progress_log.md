# Progress
- [INIT] Memory system created.
- [2026-04-01] src/preprocessor.py: Created module with text normalization and message parsing.
- [2026-04-01] src/feature_extractor.py: Implemented feature extraction using detoxify and roberta-sentiment.
- [2026-04-02] model/message_analyzer.py: Removed HTTP HF API calls, loaded detoxify and roberta as module-level static pipelines.
- [2026-04-02] model/decision_engine.py: Updated feature vector to 6 features to match feature_extractor and fixed confidence formula.
