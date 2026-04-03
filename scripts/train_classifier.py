import json
import os
import pickle
import numpy as np
import sys
from collections import Counter

# Ensure Python can find the model directory
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from model.message_analyzer import analyze_message
from model.feature_extractor import build_feature_vector, extract_features
from model.schemas import ConversationMetadata, MessageAnalysis

def main():
    data_path = "data/conversations.jsonl"
    if not os.path.exists(data_path):
        print("Dataset not found! Please run python scripts/generate_synthetic_data.py first.")
        return

    features_list = []
    labels_list = []
    
    # 0 = safe, 1 = warning, 2 = hazardous
    label_map = {"safe": 0, "warning": 1, "hazardous": 2}
    
    print("Extracting NLP features from dataset. This may take time depending on Hugging Face API limits...")
    with open(data_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    for idx, line in enumerate(lines):
        data = json.loads(line)
        label = data["label"]
        convo = data["conversation"]
        
        # Extract Message-level features
        analyzed = []
        for msg in convo:
            analysis = analyze_message(msg["text"], msg["sender"])
            analyzed.append(MessageAnalysis.from_dict(analysis))
            
        # Extract Conversation-level features
        metadata = ConversationMetadata.from_dict(
            data.get("metadata", {"friendship_duration_days": 100, "sender_age": 25, "receiver_age": 25})
        )
        feats = extract_features(analyzed, metadata)
        vector = build_feature_vector(feats)
        
        features_list.append(vector)
        labels_list.append(label_map[label])
        
        if (idx + 1) % 10 == 0:
            print(f"Propagated {idx + 1}/{len(lines)} conversations...")
        
    X = np.array(features_list)
    y = np.array(labels_list)

    print("\nDataset label distribution:")
    for label_name, numeric_label in label_map.items():
        print(f"  {label_name}: {Counter(y)[numeric_label]}")
    
    # Train / Test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )
    
    print("\nTraining Random Forest Fusion Classifier...")
    clf = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
    clf.fit(X_train, y_train)
    
    preds = clf.predict(X_test)
    print("\nEvaluation Performance Overview:")
    target_names = ["safe", "warning", "hazardous"]
    
    try:
        print(classification_report(y_test, preds, target_names=target_names))
    except Exception as e:
        print(f"Skipped printing classification report due to uniform classes in small mock batches: {str(e)}")
    
    # Save Model Weights
    os.makedirs("models", exist_ok=True)
    model_export_path = "models/classifier.pkl"
    with open(model_export_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"\nModel successfully saved to {model_export_path}. The API will now use ML instead of fallback rules.")

if __name__ == "__main__":
    main()
