***

# 🤖 AMIer - AI Mock Interviewer

**AMIer** is an intelligent, voice-enabled AI Agent designed to simulate realistic job interviews. It analyzes your **Resume** and the **Job Description (JD)** to generate tailored questions, providing an immersive practice environment with real-time audio interaction.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-orange.svg)

## ✨ Key Features

*   **📄 Context-Aware Analysis**: Upload your Resume and target Job Description (PDF format). The AI acts as a specific interviewer for that specific role.
*   **🎤 Real-time Speech Recognition (STT)**: Utilizes the browser's native **Web Speech API** for unlimited, continuous, and free speech-to-text input.
*   **⚡ Low Latency Interaction**: Optimized architecture for fast responses. 
*   **⏸️ Interruptible**: Stop the interviewer mid-sentence by starting to speak or typing.

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI
*   **AI Model**: OpenAI GPT-3.5 / GPT-4
*   **Frontend**: HTML5, CSS3, JavaScript

## 📂 Project Structure

```bash
AMIer/
├── main.py              # The FastAPI backend application
├── static/              # Frontend files
│   └── index.html       # The main user interface
│   └── script.js        # The Javascript code
├── .env                 # API Keys and configuration (Create this)
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## 🚀 Getting Started

### 1. Prerequisites
*   Python 3.10 or higher installed.
*   An OpenAI API Key.

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/AMIer.git
cd AMIer
```

### 3. Install Dependencies
Create a virtual environment (recommended) and install the required packages:

```bash
# Create venv
python -m venv venv

# Activate venv (Windows)
venv\Scripts\activate
# Activate venv (Mac/Linux)
source venv/bin/activate

# Install requirements
pip install -r .\requirements.txt
```

### 4. Configuration (.env)
Create a file named `.env` in the root directory and add your API keys. 

> **Note for users in China:** If you use an API proxy, set `API_BASE`.

```ini
# .env file content
API_KEY=sk-your_api_key_here

# Optional: If you use a proxy/forwarding service
API_BASE=https://api.your-proxy-service.com/v1
```

### 5. Run the Application
Start the backend server:

```bash
python main.py
```

You should see output indicating the server is running (usually at `http://0.0.0.0:8000`).

### 6. Start Interviewing
1.  Open your browser (Chrome is recommended for best Speech Recognition support).
2.  Go to **`http://localhost:8000`**.
3.  Fill in the **Company** and **Position**.
4.  (Optional) Upload your **Resume PDF** and **JD PDF**.
5.  Click **"Analyze & Start Interview"**.

## Roadmap
*  [Done] Create a simple AI Mock Interviwer (AIMer) which allow users to enter their goal company and position.
*  [Partially Done] Users can submit their resume and JD to the AIMer for reference for making better mock interview.
*  [Done] The AIMer will read its reply to simulate a real interview senario.
*  [Done] Provide a speech translator to allow users input their reply by speaking
*  [Done] User can select two types of interviews (Behavior or Technical)
*  [backend done] Support leetcode algorithm mock interview round
*  Optimize the prompt engineering to make sure the model will not answer questions not related to interview.


## 📖 Usage Guide

### Voice Interaction
*   **Speaking**: Click the **Green Microphone 🎤** button to start recording. It supports **continuous recording**, so you can speak long answers. It will transfer your **voice to text**. Click the **Red Stop Button 🟥** to stop recording.
*   **Sending**:  Click the "Send" button to submit your answer.

### Tips for Best Experience
*   Use **Google Chrome** or **Microsoft Edge** on Desktop (Safari/Firefox have limited Web Speech API support).
*   Ensure your PDFs are text-based (selectable text), not <code style="color : Red">scanned images</code>.

## ❓ Troubleshooting

**Q: I get a 404 Error for `/favicon.ico`.**
A: This is harmless. You can ignore it, or add a `<link rel="icon" href="data:,">` to the HTML head.

**Q: The microphone doesn't work.**
A: Ensure you are accessing the site via `localhost` or `https`. Browsers block microphone access on insecure `http` connections (except localhost).

## 📜 License

This project is licensed under the MIT License.

---

**Happy Interviewing! 🚀**
