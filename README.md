# Conversation Safety Intelligence (CSI) 🛡️

A behavioral, multi-layered machine learning safety engine designed to protect vulnerable users from toxic interactions, grooming cycles, and predatory deception.

## Features
- **Context-Aware Safety Engine**: Uses profile metadata (Age, Friendship Duration) to distinguish between innocent banter and hazardous grooming.
- **Predatory Fingerprinting**: Tracks users with a global risk score using an onboard SQLite database. Detects multi-target repeat offenders instantly.
- **Identity Deception Detection**: Detects adult-to-child impersonation/catfishing attempts.
- **ML Fusion**: Uses HuggingFace's `Toxic-BERT` alongside a Random Forest Behavioral Classifier.

## 🚀 Setup Instructions

1. **Clone the repository**
2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment:**
   Create a `.env` file in the root directory if you possess external API tokens (Optional, this runs fully local out of the box).

## 🧠 Training the Behavioral Model
Before running the API, you must generate the synthetic behavior models and train the local Random Forest Classifier.

1. **Generate Synthetic Storylines:**
   ```bash
   python scripts/generate_synthetic_data.py
   ```
2. **Train the ML Classifier:**
   *Note: On your first run, this will download the HuggingFace `Detoxify` models. This may take some time depending on internet speed.*
   ```bash
   python scripts/train_classifier.py
   ```
   *(This script automatically creates `models/classifier.pkl`)*

## 🌐 Running the Platform

Once the model is trained, spin up the FastAPI backend and Simulator UI:

```bash
python -m api.main
```

Then visit: **[http://localhost:8000](http://localhost:8000)** in your browser to experience the real-time simulation module.

## 📂 Project Structure

* `/api/`: System endpoints and Pydantic schemas.
* `/model/`: Machine Learning inference, Database Manager (`database.py`), Feature Extractors.
* `/frontend/`: Vanilla HTML/JS/CSS Test Bed.
* `/scripts/`: Data Generation and Model Builders.
