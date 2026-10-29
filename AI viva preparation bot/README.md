# AI Viva Preparation Bot 🎓🤖

An AI-powered web application built with Flask, SQLite, and Google Gemini 2.5 Flash to help students prepare for oral technical viva examinations and technical interviews.

---

## 🌟 Key Features

1. **User Authentication & Data Privacy:**
   - Secure registration, login, and logout with password hashing (`werkzeug.security`).
   - User-specific viva history, dashboard analytics, and reports.

2. **Dynamic AI Viva Question Generation:**
   - Powered by Google Gemini 2.5 Flash (via official `google-genai` SDK).
   - Generates tailored viva questions across subjects: Operating Systems, Data Structures & Algorithms, DBMS, and Machine Learning.
   - Supports difficulty levels (Beginner, Intermediate, Advanced) and specific custom sub-topics.

3. **Multi-Criteria Viva Evaluation:**
   - Evaluates conceptual depth, technical accuracy, and completeness.
   - Provides an earned score out of 10, strengths, missed technical nuances, and an exemplary model viva answer.
   - Examiner Follow-Up Questions: Oral examiners probe deeper—practice follow-up questions with a single click.

4. **Weak Topic Detector & Targeted Study Plan:**
   - Evaluates performance data directly from past sessions.
   - Identifies the student's weakest domain, recommends high-priority sub-topics, and provides actionable AI advice.

5. **Timed Viva Mode:**
   - Enforces real viva examination conditions with an animated countdown timer.
   - Automatically submits responses when time expires.

6. **Smart Progressive Hints System:**
   - Interactive 3-tier hints without leaving the question page:
     - *Hint 1:* Guiding conceptual direction.
     - *Hint 2:* Core mechanism or architecture clue.
     - *Hint 3:* Essential keywords and trade-offs.

7. **Voice Interaction (Speech-to-Text & Text-to-Speech):**
   - Transcribes spoken oral responses directly into the text area using the browser's Web Speech API.
   - Examiner audio read-aloud: Listen to the viva question read aloud before answering.
   - Seamless fallback to keyboard typing.

8. **PDF Performance Report Export:**
   - Generates a downloadable PDF report using ReportLab containing student metrics, subject mastery breakdowns, weak topic advice, and recent session history.

---

## 🛠️ Project Structure

```text
AI-Viva-Preparation-Bot/
├── app.py                      # Core Flask web server, models, and routes
├── config.py                   # App configuration and environment loading
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
├── .env.example                # Example environment configuration template
├── .env                        # Local environment variables (ignored by Git)
├── .gitignore                  # Git ignore rules
├── instance/
│   └── viva_prep.db            # SQLite database for users & sessions
├── services/
│   ├── ai_service.py           # Gemini 2.5 Flash integration & offline fallback
│   └── pdf_service.py          # ReportLab PDF report generator
├── templates/
│   ├── base.html               # Shared layout, navbar, and flash alerts
│   ├── index.html              # Home page with viva configuration
│   ├── practice.html           # Interactive viva arena (Timer, Voice, Hints)
│   ├── result.html             # Assessment results, feedback & follow-up questions
│   ├── dashboard.html          # Analytics & Weak Topic Detector
│   ├── history.html            # Session history log
│   ├── login.html              # User login
│   ├── register.html           # User registration
│   ├── subjects.html           # Domain explorer
│   ├── viva.html               # Compatible alias for practice
│   ├── feedback.html           # Compatible alias for results
│   └── performance.html        # Compatible alias for dashboard
└── static/
    └── style.css               # Responsive modern stylesheet
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Installation
```bash
# Clone the repository and enter the directory
cd "AI viva preparation bot"

# Install required dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
FLASK_SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=sqlite:///viva_prep.db

# Add your Gemini API key from https://aistudio.google.com/
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

> **Note:** If `GEMINI_API_KEY` is not provided or if running offline, the bot automatically runs in resilient offline mode with a built-in repository of viva questions, progressive hints, and heuristic evaluation so you can test all features without interruption.

### 4. Running the Application
```bash
python app.py
```
Open your browser and navigate to: `http://127.0.0.1:5000`

---

## 🧪 Testing

To run the automated verification suite:
```bash
python -m unittest tests/test_app.py
```
