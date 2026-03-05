#!/usr/bin/env python3
"""
q7x API server — HTTP wrapper around q7x core logic.
Powers the chat.q7x.ai web interface.

POST /api/chat      — send a message, get response + debug payload
POST /api/login     — authenticate
POST /api/logout    — clear session
POST /api/clear     — new session
GET  /api/session   — get current session state
GET  /api/models    — list available OpenRouter models (cached)
GET  /api/model/info — get provider details for active model
POST /api/model     — switch the active model
"""

import os
import json
import uuid
import secrets
import time
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

# ── Model cache ───────────────────────────────────────────────────────────────
_models_cache = {"data": None, "fetched_at": 0, "ttl": 3600}  # 1 hour TTL


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_client(config):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    return OpenAI(base_url=config["llm"]["base_url"], api_key=api_key)


def or_api_get(path):
    """Make an authenticated GET request to OpenRouter API."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    url = "https://openrouter.ai" + path
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


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


# ── Models ────────────────────────────────────────────────────────────────────

@app.route("/api/models", methods=["GET"])
def list_models():
    auth_error = require_auth()
    if auth_error:
        return auth_error

    now = time.time()
    if _models_cache["data"] and (now - _models_cache["fetched_at"]) < _models_cache["ttl"]:
        return jsonify({"models": _models_cache["data"], "cached": True})

    try:
        raw = or_api_get("/api/v1/models")
        models = []
        for m in raw.get("data", []):
            pricing = m.get("pricing", {})
            models.append({
                "id": m["id"],
                "name": m.get("name", m["id"]),
                "context_length": m.get("context_length"),
                "top_provider": m.get("top_provider", {}),
                "pricing": {
                    "prompt": pricing.get("prompt", "0"),
                    "completion": pricing.get("completion", "0"),
                    "image": pricing.get("image", "0"),
                },
            })
        # Sort: free first, then by name
        models.sort(key=lambda x: (x["pricing"]["prompt"] != "0", x["name"].lower()))
        _models_cache["data"] = models
        _models_cache["fetched_at"] = now
        return jsonify({"models": models, "cached": False})
    except Exception as e:
        # Return cache even if stale on error
        if _models_cache["data"]:
            return jsonify({"models": _models_cache["data"], "cached": True, "error": str(e)})
        return jsonify({"error": str(e)}), 502


@app.route("/api/model/info", methods=["GET"])
def model_info():
    """Get provider/endpoint details for the active model."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    config = load_config()
    model_id = config["llm"]["model"]

    # Parse author/slug from model ID (e.g. "arcee-ai/trinity-large-preview:free")
    base_model = model_id.split(":")[0]  # strip variant suffix
    parts = base_model.split("/", 1)
    if len(parts) != 2:
        return jsonify({"error": f"Cannot parse model ID: {model_id}"}), 400

    author, slug = parts

    try:
        endpoints = or_api_get(f"/api/v1/models/{author}/{slug}/endpoints")
        # Also get the model details from the cached list
        model_meta = None
        if _models_cache["data"]:
            for m in _models_cache["data"]:
                if m["id"] == model_id or m["id"] == base_model:
                    model_meta = m
                    break

        return jsonify({
            "model_id": model_id,
            "endpoints": endpoints.get("data", []),
            "meta": model_meta,
        })
    except Exception as e:
        return jsonify({"error": str(e), "model_id": model_id}), 502


@app.route("/api/model", methods=["POST"])
def set_model():
    """Switch the active model."""
    auth_error = require_auth()
    if auth_error:
        return auth_error

    data = request.get_json()
    new_model = (data.get("model") or "").strip()
    if not new_model:
        return jsonify({"error": "No model specified"}), 400

    config = load_config()
    old_model = config["llm"]["model"]
    config["llm"]["model"] = new_model
    save_config(config)

    return jsonify({"ok": True, "old_model": old_model, "new_model": new_model})



# ── Context Assembly ──────────────────────────────────────────────────────────

MAX_CONTEXT_CHARS = 1500   # max total chars of injected context
MIN_SNIPPET_LEN = 20       # skip tiny/useless snippets

def assemble_context(st_context, config):
    """
    Filter and limit context from Steeltrap before injecting into the LLM payload.
    - Drops empty or too-short snippets
    - Truncates to MAX_CONTEXT_CHARS total
    - Returns cleaned list of system messages (or empty list)
    """
    if not st_context:
        return []

    cleaned_snippets = []
    total_chars = 0

    for msg in st_context:
        if msg.get("role") != "system":
            continue
        text = msg.get("content", "").strip()
        if len(text) < MIN_SNIPPET_LEN:
            continue

        # Parse individual snippets from the "- snippet" format
        lines = text.split("\n")
        filtered_lines = []
        for line in lines:
            stripped = line.strip().lstrip("- ").strip()
            # Skip lines that look like LLM boilerplate
            if any(skip in stripped.lower() for skip in [
                "how can i assist", "hello!", "sure,", "certainly!", "of course!",
                "is there anything", "let me know", "i\'d be happy to",
            ]):
                continue
            if len(stripped) >= MIN_SNIPPET_LEN:
                filtered_lines.append(stripped)
                total_chars += len(stripped)
            if total_chars >= MAX_CONTEXT_CHARS:
                break

        if filtered_lines:
            cleaned_snippets.extend(filtered_lines)
        if total_chars >= MAX_CONTEXT_CHARS:
            break

    if not cleaned_snippets:
        return []

    content = "Relevant context from memory:\n" + "\n".join(f"- {s}" for s in cleaned_snippets)
    return [{"role": "system", "content": content}]


# ── Chat ──────────────────────────────────────────────────────────────────────
# ── Status ────────────────────────────────────────────────────────────────────

@app.route("/api/status", methods=["GET"])
def status():
    """Lightweight status — returns current model without hitting OpenRouter."""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    config = load_config()
    return jsonify({
        "model": config["llm"]["model"],
        "steeltrap_enabled": config.get("steeltrap", {}).get("enabled", False),
    })



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

    # Track cumulative usage
    session_usage = web_sess.get("usage", {
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "turn_count": 0,
    })

    # Steeltrap context
    st_context, st_debug = get_steeltrap_context(config, user_input)

    # Build message array
    messages.append({"role": "user", "content": user_input})

    # Context assembly — filter and limit injected context
    injected = assemble_context(st_context, config)
    if injected:
        messages.extend(injected)

    # Snapshot payload BEFORE the LLM call
    payload_snapshot = list(messages)

    # LLM call
    client = get_client(config)
    t_start = time.time()
    try:
        response = client.chat.completions.create(
            model=config["llm"]["model"],
            messages=messages,
            stream=False,
        )
        assistant_content = response.choices[0].message.content
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    t_end = time.time()

    # Extract usage from OpenRouter response
    turn_usage = {}
    if hasattr(response, "usage") and response.usage:
        turn_usage = {
            "prompt_tokens": response.usage.prompt_tokens or 0,
            "completion_tokens": response.usage.completion_tokens or 0,
            "total_tokens": response.usage.total_tokens or 0,
        }
        session_usage["total_prompt_tokens"] += turn_usage["prompt_tokens"]
        session_usage["total_completion_tokens"] += turn_usage["completion_tokens"]
        session_usage["total_tokens"] += turn_usage["total_tokens"]

    session_usage["turn_count"] += 1
    turn_usage["latency_ms"] = round((t_end - t_start) * 1000)

    # Try to get generation cost from OpenRouter
    gen_id = response.id if hasattr(response, "id") else None
    turn_usage["generation_id"] = gen_id

    # Store assistant response
    messages.append({"role": "assistant", "content": assistant_content})

    # Persist — strip system messages
    web_sess["messages"] = [m for m in messages if m["role"] != "system"]
    web_sess["model"] = config["llm"]["model"]
    web_sess["updated_at"] = datetime.now(timezone.utc).isoformat()
    web_sess["usage"] = session_usage
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
                "created_at": web_sess.get("created_at"),
                "updated_at": web_sess.get("updated_at"),
            },
            "usage": {
                "turn": turn_usage,
                "session": session_usage,
            },
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
