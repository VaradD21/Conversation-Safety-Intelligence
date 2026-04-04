# 🛡️ Step-by-Step Guide: Running the Safety Model on Another PC

This guide will walk you through setting up and running the **Cyber Safety Monitoring System** on a fresh Windows PC.

---

## 📋 Prerequisites
Ensure the following are installed on the target machine:
1.  **Python 3.9 or newer**: [Download from python.org](https://www.python.org/downloads/)
    *   *Important*: Check the box "**Add Python to PATH**" during installation.
2.  **Git**: [Download from git-scm.com](https://git-scm.com/downloads) (optional, if you're cloning the repo).
3.  **An IDE (Optional)**: VS Code is recommended.

---

## 🚀 Step 1: Clone or Copy the Repository
Either clone using Git:
```bash
git clone https://github.com/VaradD21/Cyber-Safety-Monitoring-System-Model.git
cd Cyber-Safety-Monitoring-System-Model
```
Or simply copy the project folder to the new PC and open a terminal (PowerShell or CMD) in that directory.

---

## 📦 Step 2: Create a Virtual Environment (Highly Recommended)
Isolating dependencies ensures the system runs correctly without conflicting with other Python projects.

1.  **Create the environment**:
    ```powershell
    python -m venv venv
    ```
2.  **Activate it**:
    *   **PowerShell**: `.\venv\Scripts\Activate.ps1`
    *   **CMD**: `.\venv\Scripts\activate.bat`

---

## 🛠️ Step 3: Install Dependencies
Install all required libraries using the provided `requirements.txt`:
```powershell
pip install -r requirements.txt
```
*Note: This might take a few minutes as it downloads the model frameworks (Transformers, Torch, etc.).*

---

## 🔑 Step 4: Configure API Keys (.env)
The "AI Judge" layer requires at least one free API key to provide advanced reasoning.

1.  In the root directory, create a file named `.env` (or edit the existing one).
2.  Add your keys in this format:
    ```env
    # Primary (Recommended) - Get at https://aistudio.google.com/app/apikey
    GEMINI_API_KEY=your_gemini_key_here

    # Fallback 1 - Get at https://console.groq.com
    GROQ_API_KEY=your_groq_key_here

    # Fallback 2 - Get at https://huggingface.co/settings/tokens
    HF_API_TOKEN=your_hf_token_here
    ```

---

## 🖥️ Step 5: Run the Server
Start the FastAPI backend server:
```powershell
python -m api.main
```
If successful, you will see output indicating the server is running at `http://127.0.0.1:8000`.

---

## 🌐 Step 6: Access the Dashboard
1.  Open your web browser.
2.  Navigate to: `http://127.0.0.1:8000`
3.  You can now start simulating conversations in the interactive dashboard!

---

## 🧩 Step 7: Load the Chrome Extension (Optional)
To test the transparent browser protection:
1.  Open Chrome and go to `chrome://extensions/`.
2.  Enable **Developer Mode** (top right toggle).
3.  Click **Load unpacked**.
4.  Select the `extension` folder from the project directory.
5.  Click the extension icon in your toolbar and ensure it's pointed to `http://localhost:8000`.

---

## 🔍 Troubleshooting
*   **Port 8000 already in use**: Run the server on a different port: `python -m api.main --port 8001`.
*   **ModuleNotFoundError**: Ensure you have activated your `venv` (Step 2) before running.
*   **API Key Error**: Double-check your `.env` file formatting and ensure the key has no extra spaces.
