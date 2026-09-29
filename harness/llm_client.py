"""Minimal raw-HTTP Anthropic Messages API client (no SDK dependency). Key is read from a file
path the CALLER supplies explicitly (never searched for, never printed, never logged).
Reused verbatim from the prior long-horizon benchmark round (docs 126-143)."""
import json
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"


def load_key(key_path):
    with open(key_path) as f:
        return f.read().strip()


def call_messages(api_key, model, system, user_text, max_tokens=400, temperature=0.0):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "content-type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": API_VERSION,
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body}") from None
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    usage = data.get("usage", {})
    return {
        "text": text,
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "message_id": data.get("id"),
        "model": data.get("model"),
    }
