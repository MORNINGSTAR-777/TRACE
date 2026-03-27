# TRACE — Timeline & Record Analysis Contradiction Engine

A forensic intelligence web application that lets investigators upload digital evidence (CDR, WhatsApp, GPS, suspect statements) and automatically detects contradictions using AI.

---

## 🚀 Quick Start

### 1. Install Python dependencies
```bash
pip install flask pandas werkzeug
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5001
```

### 4. Login with demo credentials
- **Email:** demo@trace.gov  
- **Password:** demo123

---

## 📁 Project Structure

```
TRACE/
├── app.py                  # Flask backend — all routes & DB logic
├── requirements.txt
├── db/
│   └── trace.db            # SQLite database (auto-created)
├── static/
│   ├── css/main.css        # Light blue/white design system
│   └── js/main.js          # Shared utilities (toast, API helpers)
├── templates/
│   ├── base.html           # Sidebar layout shell
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── dashboard.html      # Stats + recent cases
│   ├── cases.html          # Case list with filters
│   ├── upload.html         # Evidence file upload per case
│   ├── analysis.html       # Core AI contradiction detection
│   ├── report.html         # Printable contradiction report
│   └── settings.html       # API key + profile settings
```

---

## 🔑 Anthropic API Key Setup

1. Go to **Settings** in the app
2. Paste your key from [console.anthropic.com](https://console.anthropic.com)
3. Click **Test Connection**
4. The key is stored in your browser session (not in the database)

**Without an API key:** use **Demo Mode** on the Analysis page to generate sample contradictions.

---

## 📂 Supported File Types

| Type | Format | Description |
|------|--------|-------------|
| CDR | CSV | Call Detail Records — date, time, tower, number |
| WhatsApp | TXT/CSV | Exported chat logs |
| GPS | CSV | Timestamp, latitude, longitude, location |
| Statement | TXT | Suspect's written narrative |
| Social Media | CSV | Platform exports |
| Email | TXT/CSV | Email records |

---

## 🧠 How It Works

1. **Create a Case** — enter suspect name and case title
2. **Upload Evidence** — CDR, GPS logs, WhatsApp export, statement
3. **Run Analysis** — Claude API extracts claims from statement, cross-references against digital records
4. **Review Contradictions** — sorted by severity (High / Medium / Low)
5. **Export Report** — print-ready PDF with all findings

---

## 🗄️ Database Schema

- `users` — investigator accounts
- `cases` — investigation cases
- `uploads` — evidence files per case
- `contradictions` — detected conflicts with severity
- `analysis_runs` — history of each analysis run

---

## ⚙️ Configuration

Edit `app.py` to change:
- `port=5001` → run on a different port
- `DB_PATH` → change database location
- `UPLOAD_FOLDER` → change where files are saved

---

## 🌐 Production Deployment

For production, use **gunicorn** instead of the Flask dev server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```
