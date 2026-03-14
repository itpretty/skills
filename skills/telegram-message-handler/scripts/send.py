#!/usr/bin/env python3
"""Send messages and media to a Telegram chat."""

import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.request
import urllib.error
import uuid

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
MAX_LENGTH = 4096
MAX_CAPTION = 1024

# Media type -> (API method, file param name)
MEDIA_TYPES = {
    "photo":      ("sendPhoto",     "photo"),
    "document":   ("sendDocument",  "document"),
    "video":      ("sendVideo",     "video"),
    "audio":      ("sendAudio",     "audio"),
    "voice":      ("sendVoice",     "voice"),
    "animation":  ("sendAnimation", "animation"),
    "sticker":    ("sendSticker",   "sticker"),
    "video_note": ("sendVideoNote", "video_note"),
}

# Extension -> media type (for auto-detection)
EXT_TO_TYPE = {
    ".jpg": "photo", ".jpeg": "photo", ".png": "photo", ".gif": "animation",
    ".webp": "sticker", ".tgs": "sticker",
    ".mp4": "video", ".mov": "video", ".avi": "video", ".mkv": "video",
    ".mp3": "audio", ".m4a": "audio", ".flac": "audio", ".wav": "audio",
    ".ogg": "voice", ".oga": "voice",
    ".webm": "video_note",
    ".pdf": "document", ".zip": "document", ".txt": "document",
}


def load_env():
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


def _api_call_json(token, method, payload):
    """Make a JSON API call (for text messages and URL-based media)."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(payload).encode()
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, ssl.SSLError) as e:
            if "SSL" in str(e) and attempt < 2:
                time.sleep(1)
                continue
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "max retries exceeded"}


def _api_call_multipart(token, method, fields, file_param, file_path):
    """Make a multipart/form-data API call (for local file uploads)."""
    url = f"https://api.telegram.org/bot{token}/{method}"
    boundary = uuid.uuid4().hex

    body = b""
    for key, value in fields.items():
        if value is None:
            continue
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()

    # File part
    filename = os.path.basename(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="{file_param}"; filename="{filename}"\r\n'.encode()
    body += f"Content-Type: {mime_type}\r\n\r\n".encode()
    with open(file_path, "rb") as f:
        body += f.read()
    body += f"\r\n--{boundary}--\r\n".encode()

    for attempt in range(3):
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        })
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode())
        except (urllib.error.URLError, ssl.SSLError) as e:
            if "SSL" in str(e) and attempt < 2:
                time.sleep(1)
                continue
            return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "max retries exceeded"}


def send_message(token, chat_id, text, parse_mode="Markdown"):
    """Send a text message (up to 4096 chars)."""
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    result = _api_call_json(token, "sendMessage", payload)
    if not result.get("ok") and parse_mode:
        return send_message(token, chat_id, text, parse_mode=None)
    return result


def send_media(token, chat_id, media_type, media_source, caption=None, parse_mode="Markdown"):
    """Send any media type. media_source can be a URL, file_id, or local file path."""
    if media_type not in MEDIA_TYPES:
        return {"ok": False, "error": f"Unknown media type: {media_type}. Supported: {', '.join(MEDIA_TYPES)}"}

    method, file_param = MEDIA_TYPES[media_type]

    # Determine if it's a local file, URL, or file_id
    is_local_file = os.path.isfile(media_source)

    if is_local_file:
        fields = {"chat_id": str(chat_id)}
        if caption and media_type != "sticker":
            fields["caption"] = caption[:MAX_CAPTION]
            if parse_mode:
                fields["parse_mode"] = parse_mode
        result = _api_call_multipart(token, method, fields, file_param, media_source)
        if not result.get("ok") and parse_mode and caption:
            fields.pop("parse_mode", None)
            result = _api_call_multipart(token, method, fields, file_param, media_source)
        return result
    else:
        payload = {"chat_id": chat_id, file_param: media_source}
        if caption and media_type != "sticker":
            payload["caption"] = caption[:MAX_CAPTION]
            if parse_mode:
                payload["parse_mode"] = parse_mode
        result = _api_call_json(token, method, payload)
        if not result.get("ok") and parse_mode and caption:
            payload.pop("parse_mode", None)
            result = _api_call_json(token, method, payload)
        return result


def detect_media_type(source):
    """Auto-detect media type from file extension or URL."""
    ext = os.path.splitext(source.split("?")[0])[1].lower()
    return EXT_TO_TYPE.get(ext, "document")


FALLBACK_MESSAGE = (
    "Hey! I got your message but ran into a hiccup while processing it. "
    "I'll get back to you shortly — feel free to send it again if it's urgent!"
)


def main():
    if len(sys.argv) < 3:
        print(
            "Usage:\n"
            "  send.py <chat_id> <message> [--fallback]\n"
            "  send.py <chat_id> --photo <url_or_path> [--caption <text>]\n"
            "  send.py <chat_id> --video <url_or_path> [--caption <text>]\n"
            "  send.py <chat_id> --audio <url_or_path> [--caption <text>]\n"
            "  send.py <chat_id> --document <url_or_path> [--caption <text>]\n"
            "  send.py <chat_id> --animation <url_or_path> [--caption <text>]\n"
            "  send.py <chat_id> --voice <url_or_path> [--caption <text>]\n"
            "  send.py <chat_id> --sticker <url_or_path>\n"
            "  send.py <chat_id> --video_note <url_or_path>\n"
            "  send.py <chat_id> --media <url_or_path> [--caption <text>]  (auto-detect type)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    chat_id = sys.argv[1]
    args = sys.argv[2:]

    try:
        env = load_env()
        token = env["TELEGRAM_BOT_TOKEN"]
    except Exception as e:
        print(json.dumps({"error": "Failed to load env", "details": str(e)}), file=sys.stderr)
        sys.exit(1)

    # Parse --caption
    caption = None
    if "--caption" in args:
        idx = args.index("--caption")
        if idx + 1 < len(args):
            caption = args[idx + 1]
            args = args[:idx] + args[idx + 2:]

    # Check for media flags
    media_type = None
    media_source = None
    for mtype in list(MEDIA_TYPES) + ["media"]:
        flag = f"--{mtype}"
        if flag in args:
            idx = args.index(flag)
            if idx + 1 < len(args):
                media_source = args[idx + 1]
                media_type = mtype if mtype != "media" else detect_media_type(media_source)
                break

    if media_type and media_source:
        result = send_media(token, chat_id, media_type, media_source, caption=caption)
        if result.get("ok"):
            print(json.dumps({"ok": True, "media_type": media_type}))
        else:
            print(json.dumps({"error": "Failed to send media", "details": result}), file=sys.stderr)
            sys.exit(1)
        return

    # Text message mode
    text = args[0] if args else ""
    is_fallback = "--fallback" in args

    if is_fallback:
        text = FALLBACK_MESSAGE

    # Split long messages
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= MAX_LENGTH:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, MAX_LENGTH)
        if split_at == -1 or split_at < MAX_LENGTH // 2:
            split_at = MAX_LENGTH
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    failed = False
    for chunk in chunks:
        result = send_message(token, chat_id, chunk)
        if not result.get("ok"):
            print(json.dumps({"error": "Failed to send", "details": result}), file=sys.stderr)
            failed = True
            break

    if failed and not is_fallback:
        fallback_result = send_message(token, chat_id, FALLBACK_MESSAGE, parse_mode=None)
        if fallback_result.get("ok"):
            print(json.dumps({"ok": True, "fallback_sent": True}))
        else:
            print(json.dumps({"error": "Failed to send even fallback", "details": fallback_result}), file=sys.stderr)
            sys.exit(1)
    elif not failed:
        print(json.dumps({"ok": True, "chunks_sent": len(chunks)}))


if __name__ == "__main__":
    main()
