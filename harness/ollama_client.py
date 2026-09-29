"""Minimal local Ollama chat-completion client, matching llm_client.call_messages()'s
return shape so it drops into the existing harness with no other code changes."""
import json
import urllib.request
import urllib.error

API_URL = "http://localhost:11434/api/chat"


def call_messages(api_key, model, system, user_text, max_tokens=300, temperature=0.0):
    """api_key is unused (local, no auth) -- kept for call-signature parity with llm_client."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_text}],
        "stream": False,
        "think": False,  # this model is a reasoning/"thinking" model (capabilities include
                          # "thinking"); without this, its internal reasoning consumes the
                          # entire max_tokens budget and the final JSON answer never appears
                          # in `content`. Disabling matches this benchmark's own "no hidden
                          # chain-of-thought" rule (directive section 34) -- only the
                          # observable final answer is ever used, whether the model thinks
                          # silently and we suppress it, or doesn't think at all.
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, method="POST",
                                  headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {err_body}") from None
    text = data.get("message", {}).get("content", "")
    return {
        "text": text,
        "input_tokens": data.get("prompt_eval_count", 0),
        "output_tokens": data.get("eval_count", 0),
        "message_id": None,
        "model": data.get("model"),
    }
