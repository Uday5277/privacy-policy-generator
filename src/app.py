# src/app.py
import os
import json
import time
import hashlib
import secrets
from typing import Dict, Any
from flask import Flask, request, jsonify, send_file, abort, send_from_directory
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from docx import Document

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_ROOT, "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")

# Default data for first-run
DEFAULT_QUESTIONS = [
    {
        "id": "q1",
        "category": "Basics",
        "label": "Company name",
        "key": "company_name",
        "type": "text",
        "required": True
    },
    {
        "id": "q2",
        "category": "Contact",
        "label": "Contact email",
        "key": "contact_email",
        "type": "email",
        "required": False
    },
    {
        "id": "q3",
        "category": "Data",
        "label": "Do you collect personal data?",
        "key": "collects_personal_data",
        "type": "boolean",
        "required": True
    },
    {
        "id": "q4",
        "category": "Tracking",
        "label": "Do you use cookies?",
        "key": "uses_cookies",
        "type": "boolean",
        "required": True
    },
    {
        "id": "q5",
        "category": "Legal",
        "label": "Jurisdiction (country)",
        "key": "jurisdiction",
        "type": "text",
        "required": False
    }
]

DEFAULT_TEMPLATES = [
    {
        "id": "default",
        "name": "Minimal template",
        "clauses": {
            "collects_personal_data_true": "We collect personal information such as name and email required to provide services.",
            "collects_personal_data_false": "We do not collect personal data beyond anonymous metrics.",
            "uses_cookies_true": "We use cookies and similar technologies to improve the experience.",
            "uses_cookies_false": "We do not use cookies.",
            "default_footer": "By using our service you accept this policy."
        }
    }
]

# In-memory session store: token -> {user, expires_at}
SESSIONS: Dict[str, Dict[str, Any]] = {}

# Simple cache for previews: key -> (value, expiry)
CACHE: Dict[str, Dict[str, Any]] = {}

CACHE_TTL = 10  # seconds for preview caching (fast response requirement)

app = Flask(__name__, static_folder=os.path.join(APP_ROOT, "..", "static"), static_url_path='/static')

def load_or_init(file_path: str, default):
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(file_path: str, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# Initialize data files
_questions = load_or_init(QUESTIONS_FILE, DEFAULT_QUESTIONS)
_templates = load_or_init(TEMPLATES_FILE, DEFAULT_TEMPLATES)

# -------------------------
# Authentication Utilities
# -------------------------
def create_token(user: str, ttl_seconds: int = 900) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + ttl_seconds
    SESSIONS[token] = {"user": user, "expires_at": expires_at}
    return token

def validate_token(token: str) -> bool:
    if not token:
        return False
    s = SESSIONS.get(token)
    if not s:
        return False
    if time.time() > s["expires_at"]:
        # auto-logout: remove expired token
        del SESSIONS[token]
        return False
    return True

def require_auth(fn):
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token.split(" ", 1)[1]
        if not validate_token(token):
            return jsonify({"error": "unauthorized or session expired"}), 401
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# -------------------------
# Helper: clause logic & generation (IM-6, IM-7)
# -------------------------
def _select_clauses(answers: dict, template: dict):
    clauses = []
    tclauses = template.get("clauses", {})
    # collects_personal_data
    if answers.get("collects_personal_data", True):
        if "collects_personal_data_true" in tclauses:
            clauses.append(tclauses["collects_personal_data_true"])
    else:
        if "collects_personal_data_false" in tclauses:
            clauses.append(tclauses["collects_personal_data_false"])

    # cookies
    if answers.get("uses_cookies", True):
        if "uses_cookies_true" in tclauses:
            clauses.append(tclauses["uses_cookies_true"])
    else:
        if "uses_cookies_false" in tclauses:
            clauses.append(tclauses["uses_cookies_false"])

    # custom additional clause keys
    for k, v in tclauses.items():
        if k.startswith("if_"):
            # key format: if_{answer_key}_{value} => include if
            try:
                _, question_key, expected = k.split("_", 2)
                if str(answers.get(question_key, "")).lower() == expected.lower():
                    clauses.append(v)
            except Exception:
                pass

    # footer
    footer = tclauses.get("default_footer", "")
    return clauses, footer

def generate_policy_text(answers: dict, template_id: str = "default") -> str:
    templates = load_or_init(TEMPLATES_FILE, DEFAULT_TEMPLATES)
    tpl = next((t for t in templates if t.get("id") == template_id), templates[0])
    company_name = answers.get("company_name", "Company")
    contact = answers.get("contact_email")
    jurisdiction = answers.get("jurisdiction", "Unknown")
    clauses, footer = _select_clauses(answers, tpl)
    lines = []
    lines.append(f"Privacy Policy for {company_name}")
    lines.append(f"Effective date: {datetime.utcnow().date().isoformat()}")
    lines.append("")
    lines.append(f"{company_name} (\"we\") values your privacy.")
    lines.append("")
    lines.extend(clauses)
    lines.append("")
    lines.append(f"We operate in {jurisdiction}.")
    if contact:
        lines.append(f"For questions, contact us at {contact}.")
    lines.append("")
    if footer:
        lines.append(footer)
    return "\n".join(lines)

# -------------------------
# Caching helper (fast preview)
# -------------------------
def cache_get(key: str):
    entry = CACHE.get(key)
    if not entry:
        return None
    if entry["expires_at"] < time.time():
        del CACHE[key]
        return None
    return entry["value"]

def cache_set(key: str, value, ttl=CACHE_TTL):
    CACHE[key] = {"value": value, "expires_at": time.time() + ttl}

def make_cache_key(payload: dict) -> str:
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return h

# -------------------------
# API Routes
# -------------------------
@app.route("/api/questions", methods=["GET"])
def get_questions():
    qs = load_or_init(QUESTIONS_FILE, DEFAULT_QUESTIONS)
    # group by category for categorized questions (IM-2)
    categorized: Dict[str, list] = {}
    for q in qs:
        categorized.setdefault(q.get("category", "General"), []).append(q)
    return jsonify({"questions": qs, "categorized": categorized})

@app.route("/api/questions", methods=["POST"])
@require_auth
def add_question():
    body = request.get_json(force=True, silent=True) or {}
    qs = load_or_init(QUESTIONS_FILE, DEFAULT_QUESTIONS)
    # validate minimal fields
    if not body.get("id") or not body.get("label") or not body.get("key"):
        return jsonify({"error": "missing id/label/key"}), 400
    qs.append(body)
    write_json(QUESTIONS_FILE, qs)
    return jsonify({"ok": True, "question": body}), 201

@app.route("/api/questions/<qid>", methods=["PUT", "DELETE"])
@require_auth
def modify_question(qid):
    qs = load_or_init(QUESTIONS_FILE, DEFAULT_QUESTIONS)
    found = next((q for q in qs if q.get("id") == qid), None)
    if not found:
        return jsonify({"error": "not found"}), 404
    if request.method == "DELETE":
        qs = [q for q in qs if q.get("id") != qid]
        write_json(QUESTIONS_FILE, qs)
        return jsonify({"ok": True}), 200
    body = request.get_json(force=True, silent=True) or {}
    # update allowed fields
    for k in ("label", "category", "type", "key", "required"):
        if k in body:
            found[k] = body[k]
    write_json(QUESTIONS_FILE, qs)
    return jsonify({"ok": True, "question": found}), 200

# Templates management (IM-16)
@app.route("/api/templates", methods=["GET"])
def get_templates():
    t = load_or_init(TEMPLATES_FILE, DEFAULT_TEMPLATES)
    return jsonify({"templates": t})

@app.route("/api/templates", methods=["POST"])
@require_auth
def add_template():
    body = request.get_json(force=True, silent=True) or {}
    if not body.get("id") or not body.get("name"):
        return jsonify({"error": "missing id or name"}), 400
    t = load_or_init(TEMPLATES_FILE, DEFAULT_TEMPLATES)
    t.append(body)
    write_json(TEMPLATES_FILE, t)
    return jsonify({"ok": True, "template": body}), 201

@app.route("/api/templates/<tid>", methods=["PUT", "DELETE"])
@require_auth
def modify_template(tid):
    t = load_or_init(TEMPLATES_FILE, DEFAULT_TEMPLATES)
    found = next((x for x in t if x.get("id") == tid), None)
    if not found:
        return jsonify({"error": "not found"}), 404
    if request.method == "DELETE":
        t = [x for x in t if x.get("id") != tid]
        write_json(TEMPLATES_FILE, t)
        return jsonify({"ok": True}), 200
    body = request.get_json(force=True, silent=True) or {}
    found.update(body)
    write_json(TEMPLATES_FILE, t)
    return jsonify({"ok": True, "template": found}), 200

# Login / session (IM-19, IM-20)
@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(force=True, silent=True) or {}
    username = body.get("username")
    password = body.get("password")
    # Minimal auth for demo: credentials in env or default admin/admin
    admin_user = os.environ.get("PPG_ADMIN_USER", "admin")
    admin_pass = os.environ.get("PPG_ADMIN_PASS", "admin")
    if username == admin_user and password == admin_pass:
        token = create_token(username, ttl_seconds=900)  # 15 minutes default, auto-logout ok
        return jsonify({"token": token, "expires_in": 900}), 200
    return jsonify({"error": "invalid credentials"}), 401

# Generate policy and preview endpoints
@app.route("/api/generate", methods=["POST"])
def generate():
    payload = request.get_json(force=True, silent=True) or {}
    # produce text policy
    try:
        template_id = payload.get("template_id", "default")
        answers = payload.get("answers", {})
        policy = generate_policy_text(answers, template_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"policy": policy}), 200

@app.route("/api/preview", methods=["POST"])
def preview():
    payload = request.get_json(force=True, silent=True) or {}
    key = make_cache_key(payload)
    cached = cache_get(key)
    if cached:
        return jsonify({"policy": cached, "cached": True})
    template_id = payload.get("template_id", "default")
    answers = payload.get("answers", {})
    policy = generate_policy_text(answers, template_id)
    cache_set(key, policy)
    return jsonify({"policy": policy, "cached": False})

# Export as PDF and DOCX (IM-12 & IM-13)
@app.route("/api/export/pdf", methods=["POST"])
def export_pdf():
    payload = request.get_json(force=True, silent=True) or {}
    answers = payload.get("answers", {})
    template_id = payload.get("template_id", "default")
    txt = generate_policy_text(answers, template_id)
    # Create PDF in memory
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin
    lines = txt.split("\n")
    c.setFont("Helvetica", 11)
    for line in lines:
        if y < margin:
            c.showPage()
            y = height - margin
            c.setFont("Helvetica", 11)
        c.drawString(margin, y, line)
        y -= 14
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="privacy_policy.pdf")

@app.route("/api/export/docx", methods=["POST"])
def export_docx():
    payload = request.get_json(force=True, silent=True) or {}
    answers = payload.get("answers", {})
    template_id = payload.get("template_id", "default")
    txt = generate_policy_text(answers, template_id)
    doc = Document()
    for line in txt.split("\n"):
        doc.add_paragraph(line)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     as_attachment=True, download_name="privacy_policy.docx")

# Serve static UI (IM-23 responsive UI)
@app.route("/", methods=["GET"])
def index():
    # Serve the static single-page app
    return send_from_directory(os.path.join(APP_ROOT, "..", "static"), "index.html")

# Health check + fast response tip (IM-22)
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

# Run
if __name__ == "__main__":
    # For dev only: debug True. Do NOT enable debug in production.
    app.run(debug=True, host="0.0.0.0", port=5000)
