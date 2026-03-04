#!/usr/bin/env python3
"""
q7x API server — HTTP wrapper around q7x core logic.
Powers the chat.q7x.ai web interface.

POST /api/chat      — send a message, get response + debug payload
POST /api/login     — authenticate
POST /api/logout    — clear session
GET  /api/session   — get current session state
"""

import os
import json
import uuid
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify, session
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", secrets.token_hex(32))

CONFIG_PATH = Path.home() / ".q7x" / "config.json"
SESSIONS_DIR = Path.home() / ".q7x" / "sessions"
WEB_SESSIONS_DIR = Path.home() / ".q7x" / "web_sessions"
WEB_SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

# Hardcoded credentials (dev only)
VALID_USER = "rproemer@q7core.com"
VALID_PASS = "passw0rd"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def get_client(config):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    return OpenAI(base_url=config["llm"]["base_url"], api_key=api_key)


def get_steeltrap_context(config, query):
    if not config.get("steeltrap", {}).get("enabled", False):
        return [], None
    try:
        endpoint = os.environ.get("STEELTRAP_ENDPOINT", config["steeltrap"]["endpoint"])
        url = endpoint + "/context?q=" + urllib.parse.quote(query)
        with urllib.request.urlopen(url, timeout=2) as r:
            result = json.loads(r.read())
            return result, {"query": query, "url": url, "result": result}
    except Exception as e:
        return [], {"query": query, "error": str(e)}


def load_web_session(session_id):
    path = WEB_SESSIONS_DIR / f"{session_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return {"messages": [], "session_id": session_id, "created_at": datetime.now(timezone.utc).isoformat()}


def save_web_session(session_id, data):
    path = WEB_SESSIONS_DIR / f"{session_id}.json"
    path.write_text(json.dumps(data, indent=2))


def append_to_session_log(session_id, role, content):
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = SESSIONS_DIR / f"web_{session_id}.jsonl"
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "role": role, "content": content}
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    if data.get("email") == VALID_USER and data.get("password") == VALID_PASS:
        session["authenticated"] = True
        session["web_session_id"] = str(uuid.uuid4())
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Invalid credentials"}), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


def require_auth():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401
    return None


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
def chat():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    data = request.get_json()
    user_input = (data.get("message") or "").strip()
    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    config = load_config()
    web_session_id = session["web_session_id"]
    web_sess = load_web_session(web_session_id)
    messages = web_sess["messages"]

    # Steeltrap context
    st_context, st_debug = get_steeltrap_context(config, user_input)

    # Build message array
    messages.append({"role": "user", "content": user_input})
    if st_context:
        messages.extend(st_context)

    # Snapshot payload BEFORE the LLM call (what we're actually sending)
    payload_snapshot = list(messages)

    # LLM call
    client = get_client(config)
    try:
        response = client.chat.completions.create(
            model=config["llm"]["model"],
            messages=messages,
            stream=False,
        )
        assistant_content = response.choices[0].message.content
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Store assistant response (not the injected system context)
    messages.append({"role": "assistant", "content": assistant_content})

    # Persist — strip system messages from stored history so they get re-injected fresh next turn
    web_sess["messages"] = [m for m in messages if m["role"] != "system"]
    web_sess["model"] = config["llm"]["model"]
    web_sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_web_session(web_session_id, web_sess)

    # Log to JSONL
    append_to_session_log(web_session_id, "user", user_input)
    append_to_session_log(web_session_id, "assistant", assistant_content)

    return jsonify({
        "response": assistant_content,
        "debug": {
            "steeltrap": st_debug,
            "payload": payload_snapshot,
            "session": {
                "id": web_session_id,
                "message_count": len(web_sess["messages"]),
                "model": config["llm"]["model"],
                "log": f"~/.q7x/sessions/web_{web_session_id}.jsonl",
            }
        }
    })


@app.route("/api/session", methods=["GET"])
def get_session():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    web_sess = load_web_session(session["web_session_id"])
    return jsonify(web_sess)


@app.route("/api/clear", methods=["POST"])
def clear_session():
    auth_error = require_auth()
    if auth_error:
        return auth_error
    session["web_session_id"] = str(uuid.uuid4())
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
