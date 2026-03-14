#!/usr/bin/env python3
"""Pull Telegram for new messages from the authorized user."""

import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error

# macOS Python often lacks default certs; fall back to unverified context for Telegram API
try:
    _SSL_CTX = ssl.create_default_context()
except ssl.SSLError:
    _SSL_CTX = ssl._create_unverified_context()

try:
    import certifi
    _SSL_CTX.load_verify_locations(certifi.where())
except (ImportError, Exception):
    _SSL_CTX = ssl._create_unverified_context()

# scripts/ -> telegram-message-handler/ -> skills/ -> .claude/ -> project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
OFFSET_PATH = os.path.join(PROJECT_ROOT, ".telegram_offset")


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def get_offset():
    if os.path.exists(OFFSET_PATH):
        with open(OFFSET_PATH) as f:
            return int(f.read().strip())
    return 0


def save_offset(offset):
    with open(OFFSET_PATH, "w") as f:
        f.write(str(offset))


def main():
    env = load_env()
    token = env["TELEGRAM_BOT_TOKEN"]
    allowed_user = int(env["TELEGRAM_ALLOWED_USER_ID"])
    offset = get_offset()

    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5"

    data = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as resp:
                data = json.loads(resp.read().decode())
            break
        except (urllib.error.URLError, ssl.SSLError) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)

    if not data.get("ok"):
        print(json.dumps({"error": "API returned not ok", "response": data}), file=sys.stderr)
        sys.exit(1)

    results = data.get("result", [])
    max_update_id = offset

    messages = []
    for update in results:
        update_id = update["update_id"]
        if update_id >= max_update_id:
            max_update_id = update_id + 1

        msg = update.get("message")
        if not msg:
            continue

        from_user = msg.get("from", {})
        if from_user.get("id") != allowed_user:
            continue

        messages.append({
            "update_id": update_id,
            "chat_id": msg["chat"]["id"],
            "from": from_user.get("first_name", "Unknown"),
            "text": msg.get("text", ""),
            "date": msg.get("date"),
        })

    save_offset(max_update_id)

    if messages:
        for m in messages:
            print(json.dumps(m))
    else:
        print(json.dumps({"status": "no_new_messages"}))


if __name__ == "__main__":
    main()
