# 🎓 FREE Real-Time Hinglish Speech-to-Speech Tutor Bot
### *Didi — Aapki Pyaari English Teacher*

> A fully voice-based AI English tutor for **visually impaired students** who feel shy or scared speaking English.
> Communicates naturally in **Hinglish** (Hindi + English mix). 100% free. No API keys. No subscriptions.

---

## 📌 Table of Contents

1. [What Does It Do?](#what-does-it-do)
2. [Quick Start (5 minutes)](#quick-start)
3. [Setup — macOS](#setup-macos)
4. [Setup — Windows](#setup-windows)
5. [Install Ollama (optional — for smarter AI)](#install-ollama)
6. [Running the Server](#running-the-server)
7. [Opening in Google Chrome](#opening-in-google-chrome)
8. [How to Use the Bot](#how-to-use-the-bot)
9. [Voice Commands](#voice-commands)
10. [Tech Stack](#tech-stack)
11. [Troubleshooting](#troubleshooting)
12. [Project Structure](#project-structure)

---

## What Does It Do?

| Feature | Detail |
|---|---|
| 🎤 Real-time voice input | Web Speech API (Chrome) — no external service |
| 🔊 Voice output | SpeechSynthesis API — Indian female voice when available |
| 🤖 AI Brain | Ollama (llama3 / mistral) → smart rule-based fallback |
| 🌐 Languages | Hindi, English, Hinglish |
| ♿ Accessibility | Screen-reader friendly, high contrast, keyboard shortcuts |
| 💰 Cost | Completely FREE |
| 📶 Offline | Works offline after first load (rule-based mode) |

### Example Conversation

```
Student  :  Didi mujhe English seekhni hai
Didi Bot :  Zaroor beta! Chalo aaj English practice karte hain.
             Pehle ek simple sentence boliye: "My name is..."

Student  :  I am scared to speak English
Didi Bot :  Arey beta, main hoon na! Koi judge nahi karega.
             Galti se hi seekhte hain. Chalo ek baar try karo!

Student  :  Courage ka matlab kya hai
Didi Bot :  Courage ka matlab hai Himmat! Example:
             "You have the courage to learn English." Bahut acha!
```

---

## Quick Start

```bash
# 1. Clone / Download the project
cd ~/Documents/Voice_Bot

# 2. Create virtual environment
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py

# 5. Open Chrome → http://localhost:5000
```

---

## Setup — macOS

### Step 1 — Install Python 3.10+

Check if Python is installed:
```bash
python3 --version
```

If not installed, download from: https://www.python.org/downloads/

Or use Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python
```

### Step 2 — Download / Clone the Project

```bash
# If you downloaded a ZIP, unzip it to:
~/Documents/Voice_Bot/

# Or use git:
git clone <your-repo-url> ~/Documents/Voice_Bot
```

### Step 3 — Create Virtual Environment

```bash
cd ~/Documents/Voice_Bot
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Run the Server

```bash
python app.py
```

Expected output:
```
════════════════════════════════════════════════════════════
  Hinglish Speech-to-Speech Tutor Bot — Didi
════════════════════════════════════════════════════════════
  Server  : http://localhost:5000
  Browser : Open Google Chrome → http://localhost:5000
  Ollama  : OFFLINE → using smart rule-based fallback
════════════════════════════════════════════════════════════
```

### Step 6 — Open in Chrome

Open **Google Chrome** (not Safari, not Firefox):
```
http://localhost:5000
```

Click **Allow** when Chrome asks for microphone permission.

---

## Setup — Windows

### Step 1 — Install Python 3.10+

1. Go to: https://www.python.org/downloads/windows/
2. Download the latest **Python 3.x Windows Installer**
3. Run installer — ✅ **Check "Add Python to PATH"** before clicking Install

Verify:
```cmd
python --version
```

### Step 2 — Open the Project in VS Code

1. Download VS Code: https://code.visualstudio.com/
2. Open VS Code → File → Open Folder → Select `Voice_Bot` folder
3. Open Terminal: **View → Terminal** (or Ctrl + `)

### Step 3 — Create Virtual Environment

```cmd
cd C:\Users\YourName\Documents\Voice_Bot
python -m venv venv
venv\Scripts\activate
```

You will see `(venv)` in the terminal.

### Step 4 — Install Dependencies

```cmd
pip install -r requirements.txt
```

### Step 5 — Run the Server

```cmd
python app.py
```

### Step 6 — Open in Chrome

Open **Google Chrome**:
```
http://localhost:5000
```

Click **Allow** when Chrome asks for microphone access.

---

## Install Ollama (Optional — For Smarter AI Responses)

Without Ollama, the bot uses a **smart rule-based engine** which works well.
With Ollama, the bot uses **local AI (llama3 / mistral)** for natural conversation.

### macOS

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama (runs in background)
ollama serve

# Pull llama3 model (first time only, ~4 GB download)
ollama pull llama3

# Or use lighter model (1.5 GB)
ollama pull mistral
```

### Windows

1. Download Ollama installer: https://ollama.com/download/windows
2. Run the `.exe` installer
3. Open a new Command Prompt or PowerShell:

```powershell
# Pull llama3 model
ollama pull llama3

# Or lighter model
ollama pull mistral
```

Ollama runs automatically on port `11434`.

### Verify Ollama is Working

```bash
curl http://localhost:11434/api/tags
```

Should return a JSON list of your installed models.

### Restart the Bot Server

After pulling a model, restart `app.py` — the terminal will confirm:
```
  Ollama  : ONLINE  (model: llama3)
```

---

## Running the Server

```bash
# Always activate venv first!

# macOS / Linux
source venv/bin/activate
python app.py

# Windows
venv\Scripts\activate
python app.py
```

The server runs on: **http://localhost:5000**

To stop the server: Press **Ctrl + C** in the terminal.

---

## Opening in Google Chrome

1. Open **Google Chrome** browser
2. Go to address bar → type: `http://localhost:5000` → press Enter
3. A pop-up will ask for **microphone permission** → click **Allow**
4. The page loads with Didi's welcome message

> ⚠️ **Important:** Use Google Chrome only. Safari and Firefox do not fully support the Web Speech API used by this project.

---

## How to Use the Bot

### Starting the Bot

Click the green **"Shuru Karo"** button, OR press the **Space bar**.

The bot will say:
> *"Namaste beta! Main aapki speaking teacher hoon. Aaj kya seekhna hai?"*

### Speaking

Just speak naturally into your microphone. The bot continuously listens.

**You can speak in:**
- Hindi: *"Didi mujhe English sikhao"*
- English: *"Teach me a new word"*
- Hinglish: *"Didi, today ka word kya hai?"*

### Stopping

Click **"Band Karo"** button, OR press **Space bar**, OR say **"Bye"** / **"Band karo"**.

### Repeating Last Message

Click **"Phir Bolo"** button, OR press **R** key, OR say **"Phir bolo"**.

### Adjusting Speed

Use the **speed slider** at the bottom to make Didi speak slower or faster.
Press **S** key to quickly toggle between normal and slow mode.

---

## Voice Commands

| What to say | What happens |
|---|---|
| `"Hello Didi"` | Bot greets you |
| `"Didi mujhe English sikhao"` | Starts English lessons |
| `"Aaj ka word kya hai?"` | Today's vocabulary word |
| `"Courage ka matlab kya hai?"` | Word meaning in Hindi |
| `"Ek sentence practice karni hai"` | Speaking practice |
| `"Pronunciation batao"` | Pronunciation tips |
| `"Mujhe dar lag raha hai"` | Confidence building response |
| `"Phir bolo"` / `"Repeat karo"` | Repeats last message |
| `"Dheere bolo"` / `"Slowly"` | Slows down speech |
| `"Bye"` / `"Band karo"` / `"Exit"` | Stops the bot |

### Keyboard Shortcuts

| Key | Action |
|---|---|
| `Space` | Start / Stop bot |
| `R` | Repeat last message |
| `S` | Toggle slow / normal speed |

---

## Tech Stack

| Component | Technology | Cost |
|---|---|---|
| Frontend | HTML5, CSS3, JavaScript | Free |
| Speech Input | Web Speech API (Chrome) | Free |
| Speech Output | SpeechSynthesis API (Chrome) | Free |
| AI Brain | Ollama + llama3 / mistral | Free |
| Fallback | Rule-based Hinglish engine | Free |
| Backend | Python Flask | Free |
| Voice | Browser TTS (Veena on macOS, Google hi-IN) | Free |

**No paid APIs. No keys. No subscriptions. Forever free.**

---

## Troubleshooting

### ❌ "Microphone permission denied"

**Chrome → Settings → Privacy and Security → Site Settings → Microphone**
- Find `localhost` and set to **Allow**
- Reload the page

### ❌ Voice recognition not working

- Make sure you are using **Google Chrome** (not Firefox / Safari / Edge)
- Check your system microphone is working: System Preferences → Sound → Input (macOS) or Control Panel → Sound → Recording (Windows)
- Try unplugging and replugging your headset

### ❌ Bot is not responding (no reply)

- Check the terminal — is `python app.py` still running?
- Reload Chrome: `Ctrl + Shift + R` (Windows) or `Cmd + Shift + R` (macOS)
- If using Ollama, check it is running: `ollama serve`

### ❌ "pip: command not found" (macOS)

```bash
python3 -m pip install -r requirements.txt
```

### ❌ flask-cors error on Windows

```cmd
pip install flask flask-cors requests
```

### ❌ Ollama says "model not found"

```bash
ollama pull llama3
# or
ollama pull mistral
```

### ❌ Bot speaks too fast

- Use the **Speed Slider** on the page to reduce speed
- Or press **S** key for slow mode

### ❌ Port 5000 already in use

```bash
# macOS — find and kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID_NUMBER> /F
```

Or change port in `app.py`:
```python
app.run(debug=False, host="0.0.0.0", port=5001)
```

### ❌ macOS Firewall Blocks Ollama

System Preferences → Security & Privacy → Firewall → Allow `ollama`

---

## Project Structure

```
Voice_Bot/
│
├── app.py                  ← Flask backend (AI brain + API routes)
├── requirements.txt        ← Python dependencies
│
├── templates/
│   └── index.html          ← Main accessible web page
│
├── static/
│   ├── style.css           ← High-contrast accessible stylesheet
│   ├── script.js           ← Voice engine (SpeechRecognition + SpeechSynthesis)
│   └── manifest.json       ← PWA manifest (installable app support)
│
└── README.md               ← This file
```

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Serve main page |
| `/chat` | POST | Send message, get Didi's response |
| `/health` | GET | Check Ollama status |
| `/vocab/daily` | GET | Today's vocabulary word |
| `/vocab/random` | GET | Random vocabulary word |

---

## For Presenters (College Demo Tips)

1. **Before the demo:** Run `python app.py` and open Chrome. Speak once to confirm mic works.
2. **If Ollama is slow:** The rule-based engine kicks in instantly — demo still works perfectly.
3. **Showcase:** Say *"Didi mujhe English sikhao"*, then *"Courage ka matlab kya hai?"*, then *"Mujhe dar lag raha hai"* — this shows the full Hinglish personality.
4. **Accessibility demo:** Use keyboard-only (Tab + Space) to show screen-reader friendliness.
5. **Repeat feature:** If judges can't hear clearly, press **R** to replay.

---

## License

MIT License — Free to use, share, and modify.

Made with ❤️ for visually impaired students across India.
```

---

*"Main hoon na, beta. Seekhte raho!"* — Didi 🎓
