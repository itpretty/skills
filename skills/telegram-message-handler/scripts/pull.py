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
MEDIA_DIR = os.path.join(PROJECT_ROOT, ".telegram_media")

# Media fields to check in order of priority
MEDIA_FIELDS = ["photo", "document", "video", "audio", "voice", "animation", "sticker", "video_note"]


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


def api_request(url):
    """Make an API request with retries."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, ssl.SSLError) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            return None, str(e)
    return None, "max retries exceeded"


def download_file(token, file_id):
    """Download a file from Telegram. Returns (local_path, file_size) or (None, error)."""
    result = api_request(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")
    if not result or not result.get("ok"):
        return None, "getFile API failed"

    file_path = result["result"]["file_path"]
    file_size = result["result"].get("file_size", 0)
    file_url = f"https://api.telegram.org/file/bot{token}/{file_path}"

    os.makedirs(MEDIA_DIR, exist_ok=True)
    ext = os.path.splitext(file_path)[1] or ""
    local_name = f"{file_id}{ext}"
    local_path = os.path.join(MEDIA_DIR, local_name)

    for attempt in range(3):
        try:
            req = urllib.request.Request(file_url)
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                with open(local_path, "wb") as f:
                    f.write(resp.read())
            return local_path, file_size
        except (urllib.error.URLError, ssl.SSLError) as e:
            if attempt < 2:
                time.sleep(1)
                continue
            return None, str(e)
    return None, "max retries exceeded"


def extract_media(msg, token):
    """Extract media info from a message and download the file. Returns dict or None."""
    for field in MEDIA_FIELDS:
        content = msg.get(field)
        if not content:
            continue

        # photo is an array of sizes; pick the largest (last)
        if field == "photo":
            item = content[-1]
        else:
            item = content

        file_id = item.get("file_id")
        if not file_id:
            continue

        media_info = {
            "type": field,
            "file_id": file_id,
            "file_unique_id": item.get("file_unique_id", ""),
        }

        if field == "photo":
            media_info["width"] = item.get("width")
            media_info["height"] = item.get("height")
        elif field == "document":
            media_info["file_name"] = item.get("file_name", "")
            media_info["mime_type"] = item.get("mime_type", "")
        elif field in ("video", "animation", "video_note"):
            media_info["duration"] = item.get("duration")
            media_info["width"] = item.get("width")
            media_info["height"] = item.get("height")
        elif field in ("audio", "voice"):
            media_info["duration"] = item.get("duration")
            media_info["mime_type"] = item.get("mime_type", "")
        elif field == "sticker":
            media_info["emoji"] = item.get("emoji", "")
            media_info["set_name"] = item.get("set_name", "")

        local_path, size_or_err = download_file(token, file_id)
        if local_path:
            media_info["local_path"] = local_path
            media_info["file_size"] = size_or_err
        else:
            media_info["download_error"] = size_or_err

        return media_info

    return None


def main():
    env = load_env()
    token = env["TELEGRAM_BOT_TOKEN"]
    allowed_user = int(env["TELEGRAM_ALLOWED_USER_ID"])
    offset = get_offset()

    url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5"

    result = api_request(url)
    if isinstance(result, tuple):
        print(json.dumps({"error": result[1]}), file=sys.stderr)
        sys.exit(1)
    if not result or not result.get("ok"):
        print(json.dumps({"error": "API returned not ok", "response": result}), file=sys.stderr)
        sys.exit(1)

    results = result.get("result", [])
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

        entry = {
            "update_id": update_id,
            "chat_id": msg["chat"]["id"],
            "from": from_user.get("first_name", "Unknown"),
            "text": msg.get("text", ""),
            "caption": msg.get("caption", ""),
            "date": msg.get("date"),
        }

        media = extract_media(msg, token)
        if media:
            entry["media"] = media

        messages.append(entry)

    save_offset(max_update_id)

    if messages:
        for m in messages:
            print(json.dumps(m))
    else:
        print(json.dumps({"status": "no_new_messages"}))


if __name__ == "__main__":
    main()
