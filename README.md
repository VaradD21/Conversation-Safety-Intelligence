# Cyber Safety Monitoring System 🛡️

A comprehensive, research-driven Cyber Safety and Abuse Monitoring platform designed to protect younger users through advanced behavioral analysis and multi-layered detection.

This project integrates high-performance NLP, domain-aware computer vision, and expert reasoning models to create a transparent, ethical safety layer for digital environments.

---

## 🌟 Technical Highlights

### 1. Multi-Modal Analysis Capabilities
*   **Media Evaluation Layer**: Detects restricted or inappropriate imagery within static images, animated GIFs, and video files (MP4/WebM) using high-efficiency Vision Transformers (ViT) and automated keyframe extraction.
*   **Linguistic & Semantic Intelligence**: Identifies obfuscated intent or coercive patterns using transformer-based sentiment analysis and semantic similarity engines.
*   **Contextual Risk Assessment**: Dynamically adjusts safety verdicts by correlating user metadata (such as age profiles and relationship duration) with conversation markers.

### 2. Multi-Provider AI Reasoning
*   Features a high-assurance "AI Judge" layer that aggregates verdicts from multiple state-of-the-art reasoning models:
    *   **Google Gemini 2.0 Flash** (Primary Reasoning)
    *   **Groq Llama-3.3-70B** (Low-Latency Fallback)
    *   **HuggingFace Qwen-2.5** (Distributed Fallback)
*   The system provides human-readable justifications for every flag, helping guardians understand risk vectors.

### 3. Ethical Extension Implementation (Manifest V3)
*   Implements on-device content analysis via a non-invasive Chrome Extension.
*   Uses **Transparent Filtering**: Instead of silent monitoring, the system provides clear notifications and "Request Access" options when content is flagged, prioritizing user awareness.

---

## 🚀 Engine Setup & Datasets

### 🛠️ Architecture 
The system is built on a **FastAPI backend** with a **Vanilla JS/HTML/CSS frontend**. 

### 📊 Dataset Origin
The detection engine was developed using a **research-backed synthetic dataset** generated specifically for this project.
*   **Synthetic Baseline**: 600+ realistic, modeled conversation threads covering 10 distinct safety categories (Peer Bullying, Grooming Patterns, Substance Misuse, etc.).
*   **NLP Models**: Pre-trained on established safety benchmarks, including the **Jigsaw Toxicity** dataset for baseline classification.
*   **Vision Models**: Utilizes pre-trained ViT architectures optimized for media safety, which were trained on diverse image-safety datasets provided via HuggingFace Hub.

### ⚙️ Local Deployment
1. **Requirements**: `pip install -r requirements.txt`
2. **Environment**: Configure `.env` with your desired API provider keys (Gemini, Groq, or HF).
3. **Execution**: Start the server with `python -m api.main`.

---

## 📂 Project Navigation

*   **/api/**: RESTful endpoints and Pydantic validation schemas.
*   **/model/**: Inference logic for media analysis, behavioral matching, and the AI Judge reasoning chain.
*   **/extension/**: Manifest V3 source code for the transparent browser safety layer.
*   **/frontend/**: Main dashboard and real-time interaction simulator.
*   **/test_media/**: Local sandbox for verifying media detection across different formats (ignored by Git).

---
*Developed as a demonstration of Ethical AI in Child Safety.*
