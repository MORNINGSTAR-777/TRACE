from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import sqlite3
import os
import json
import csv
import io
import uuid
import hashlib
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "trace_forensic_secret_2024"
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "trace.db")

# ─── Database Setup ──────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'investigator',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            suspect_name TEXT,
            status TEXT DEFAULT 'active',
            user_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            row_count INTEGER DEFAULT 0,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            claim_text TEXT NOT NULL,
            data_source TEXT NOT NULL,
            conflict_detail TEXT NOT NULL,
            severity TEXT NOT NULL,
            timestamp_claim TEXT,
            timestamp_data TEXT,
            location_claim TEXT,
            location_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            run_at TEXT DEFAULT CURRENT_TIMESTAMP,
            duration_sec REAL,
            total_contradictions INTEGER DEFAULT 0,
            high_severity INTEGER DEFAULT 0,
            medium_severity INTEGER DEFAULT 0,
            low_severity INTEGER DEFAULT 0,
            summary TEXT
        );
    """)
    # Demo user
    try:
        c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ("Demo Investigator", "demo@trace.gov", hashlib.sha256("demo123".encode()).hexdigest(), "investigator"))
    except:
        pass
    conn.commit()
    conn.close()

init_db()

# ─── Auth Helpers ─────────────────────────────────────────────────────────────
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Routes: Auth ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        email = data.get("email", "")
        password = hashlib.sha256(data.get("password", "").encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid credentials"})
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        data = request.get_json()
        name = data.get("name", "")
        email = data.get("email", "")
        password = hashlib.sha256(data.get("password", "").encode()).hexdigest()
        conn = get_db()
        try:
            conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        except:
            conn.close()
            return jsonify({"success": False, "error": "Email already registered"})
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── Routes: Dashboard ────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user_name=session["user_name"])

@app.route("/api/dashboard/stats")
@login_required
def dashboard_stats():
    conn = get_db()
    total_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE user_id=?", (session["user_id"],)).fetchone()[0]
    active_cases = conn.execute("SELECT COUNT(*) FROM cases WHERE user_id=? AND status='active'", (session["user_id"],)).fetchone()[0]
    total_contradictions = conn.execute("""
        SELECT COUNT(*) FROM contradictions c
        JOIN cases cs ON c.case_id = cs.case_id
        WHERE cs.user_id=?
    """, (session["user_id"],)).fetchone()[0]
    high_severity = conn.execute("""
        SELECT COUNT(*) FROM contradictions c
        JOIN cases cs ON c.case_id = cs.case_id
        WHERE cs.user_id=? AND c.severity='high'
    """, (session["user_id"],)).fetchone()[0]
    recent_cases = conn.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM contradictions co WHERE co.case_id = c.case_id) as contradiction_count
        FROM cases c WHERE c.user_id=? ORDER BY c.created_at DESC LIMIT 5
    """, (session["user_id"],)).fetchall()
    conn.close()
    return jsonify({
        "total_cases": total_cases,
        "active_cases": active_cases,
        "total_contradictions": total_contradictions,
        "high_severity": high_severity,
        "recent_cases": [dict(r) for r in recent_cases]
    })

# ─── Routes: Cases ────────────────────────────────────────────────────────────
@app.route("/cases")
@login_required
def cases():
    return render_template("cases.html", user_name=session["user_name"])

@app.route("/api/cases", methods=["GET"])
@login_required
def get_cases():
    conn = get_db()
    cases = conn.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM contradictions co WHERE co.case_id = c.case_id) as contradiction_count,
               (SELECT COUNT(*) FROM uploads u WHERE u.case_id = c.case_id) as file_count
        FROM cases c WHERE c.user_id=? ORDER BY c.created_at DESC
    """, (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([dict(c) for c in cases])

@app.route("/api/cases", methods=["POST"])
@login_required
def create_case():
    data = request.get_json()
    case_id = "TRC-" + str(uuid.uuid4())[:8].upper()
    conn = get_db()
    conn.execute("INSERT INTO cases (case_id, title, suspect_name, user_id) VALUES (?, ?, ?, ?)",
                 (case_id, data.get("title"), data.get("suspect_name"), session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "case_id": case_id})

@app.route("/api/cases/<case_id>", methods=["DELETE"])
@login_required
def delete_case(case_id):
    conn = get_db()
    conn.execute("DELETE FROM contradictions WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM uploads WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM analysis_runs WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM cases WHERE case_id=? AND user_id=?", (case_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ─── Routes: Upload ───────────────────────────────────────────────────────────
@app.route("/upload/<case_id>")
@login_required
def upload(case_id):
    conn = get_db()
    case = conn.execute("SELECT * FROM cases WHERE case_id=? AND user_id=?", (case_id, session["user_id"])).fetchone()
    conn.close()
    if not case:
        return redirect(url_for("cases"))
    return render_template("upload.html", case=dict(case), user_name=session["user_name"])

@app.route("/api/upload/<case_id>", methods=["POST"])
@login_required
def upload_file(case_id):
    file = request.files.get("file")
    file_type = request.form.get("file_type")
    if not file or not file_type:
        return jsonify({"success": False, "error": "Missing file or type"})
    filename = secure_filename(f"{case_id}_{file_type}_{file.filename}")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)
    row_count = 0
    try:
        if filename.endswith(".csv"):
            with open(filepath, "r", errors="ignore") as f:
                row_count = sum(1 for _ in csv.reader(f)) - 1
        elif filename.endswith(".txt"):
            with open(filepath, "r", errors="ignore") as f:
                row_count = len(f.readlines())
    except:
        pass
    conn = get_db()
    conn.execute("INSERT INTO uploads (case_id, file_type, file_name, file_path, row_count) VALUES (?, ?, ?, ?, ?)",
                 (case_id, file_type, file.filename, filepath, row_count))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "row_count": row_count, "filename": file.filename})

@app.route("/api/uploads/<case_id>")
@login_required
def get_uploads(case_id):
    conn = get_db()
    uploads = conn.execute("SELECT * FROM uploads WHERE case_id=?", (case_id,)).fetchall()
    conn.close()
    return jsonify([dict(u) for u in uploads])

# ─── Routes: Analysis ─────────────────────────────────────────────────────────
@app.route("/analysis/<case_id>")
@login_required
def analysis(case_id):
    conn = get_db()
    case = conn.execute("SELECT * FROM cases WHERE case_id=? AND user_id=?", (case_id, session["user_id"])).fetchone()
    conn.close()
    if not case:
        return redirect(url_for("cases"))
    return render_template("analysis.html", case=dict(case), user_name=session["user_name"])

@app.route("/api/analyze/<case_id>", methods=["POST"])
@login_required
def run_analysis(case_id):
    """
    This endpoint receives the AI-extracted contradictions from the frontend
    (which calls Anthropic API directly) and stores them in the database.
    """
    import time
    start = time.time()
    data = request.get_json()
    contradictions = data.get("contradictions", [])
    summary = data.get("summary", "")
    
    conn = get_db()
    # Clear old contradictions for this case
    conn.execute("DELETE FROM contradictions WHERE case_id=?", (case_id,))
    
    high = medium = low = 0
    for c in contradictions:
        sev = c.get("severity", "low")
        if sev == "high": high += 1
        elif sev == "medium": medium += 1
        else: low += 1
        conn.execute("""
            INSERT INTO contradictions 
            (case_id, claim_text, data_source, conflict_detail, severity, timestamp_claim, timestamp_data, location_claim, location_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (case_id, c.get("claim", ""), c.get("data_source", ""), c.get("conflict", ""),
              sev, c.get("timestamp_claim", ""), c.get("timestamp_data", ""),
              c.get("location_claim", ""), c.get("location_data", "")))
    
    duration = round(time.time() - start, 2)
    conn.execute("""
        INSERT INTO analysis_runs (case_id, duration_sec, total_contradictions, high_severity, medium_severity, low_severity, summary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (case_id, duration, len(contradictions), high, medium, low, summary))
    conn.execute("UPDATE cases SET updated_at=CURRENT_TIMESTAMP, status='analyzed' WHERE case_id=?", (case_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "stored": len(contradictions)})

@app.route("/api/contradictions/<case_id>")
@login_required
def get_contradictions(case_id):
    severity = request.args.get("severity", "all")
    conn = get_db()
    if severity == "all":
        rows = conn.execute("SELECT * FROM contradictions WHERE case_id=? ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END", (case_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM contradictions WHERE case_id=? AND severity=?", (case_id, severity)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/analysis_runs/<case_id>")
@login_required
def get_analysis_runs(case_id):
    conn = get_db()
    runs = conn.execute("SELECT * FROM analysis_runs WHERE case_id=? ORDER BY run_at DESC", (case_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in runs])

# ─── Routes: Report ───────────────────────────────────────────────────────────
@app.route("/report/<case_id>")
@login_required
def report(case_id):
    conn = get_db()
    case = conn.execute("SELECT * FROM cases WHERE case_id=? AND user_id=?", (case_id, session["user_id"])).fetchone()
    conn.close()
    if not case:
        return redirect(url_for("cases"))
    return render_template("report.html", case=dict(case), user_name=session["user_name"])

@app.route("/api/report/data/<case_id>")
@login_required
def report_data(case_id):
    conn = get_db()
    case = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    contradictions = conn.execute("SELECT * FROM contradictions WHERE case_id=? ORDER BY CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END", (case_id,)).fetchall()
    runs = conn.execute("SELECT * FROM analysis_runs WHERE case_id=? ORDER BY run_at DESC LIMIT 1", (case_id,)).fetchone()
    uploads = conn.execute("SELECT * FROM uploads WHERE case_id=?", (case_id,)).fetchall()
    conn.close()
    return jsonify({
        "case": dict(case) if case else {},
        "contradictions": [dict(c) for c in contradictions],
        "latest_run": dict(runs) if runs else {},
        "uploads": [dict(u) for u in uploads]
    })

# ─── Routes: Settings ─────────────────────────────────────────────────────────
@app.route("/settings")
@login_required
def settings():
    return render_template("settings.html", user_name=session["user_name"])

@app.route("/api/settings/update", methods=["POST"])
@login_required
def update_settings():
    data = request.get_json()
    conn = get_db()
    if data.get("name"):
        conn.execute("UPDATE users SET name=? WHERE id=?", (data["name"], session["user_id"]))
        session["user_name"] = data["name"]
    if data.get("new_password"):
        pw = hashlib.sha256(data["new_password"].encode()).hexdigest()
        conn.execute("UPDATE users SET password=? WHERE id=?", (pw, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/api/settings/apikey", methods=["POST"])
@login_required
def save_api_key():
    data = request.get_json()
    session["anthropic_api_key"] = data.get("api_key", "")
    return jsonify({"success": True})

@app.route("/api/settings/apikey", methods=["GET"])
@login_required
def get_api_key():
    return jsonify({"has_key": bool(session.get("anthropic_api_key"))})

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render dynamic port
    app.run(host="0.0.0.0", port=port)
