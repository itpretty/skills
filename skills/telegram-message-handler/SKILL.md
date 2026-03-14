---
name: telegram-message-handler
description: "Handle Telegram messages for the itpretty bot. Use this skill whenever the user mentions Telegram, wants to check Telegram messages, send a message to Telegram, handle Telegram messages, or interact with a Telegram bot — even if they just say 'check messages' or 'reply to Telegram'."
allowed-tools:
  - Bash(python3 .claude/skills/telegram-message-handler/scripts/pull.py*)
  - Bash(python3 .claude/skills/telegram-message-handler/scripts/send.py*)
---

# Telegram Message Handler

This skill lets you check for new messages from a Telegram bot and send responses back. It's designed for a single authorized user — all messages from other users are silently ignored.

## Setup

The bot credentials live in a `.env` file at the project root (`.env`):

```
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_ALLOWED_USER_ID=<uid>
```

Read the `.env` file to get the token before making any API calls. Never log or display the token.

## How it works

The Telegram Bot API is HTTP-based. All calls go to `https://api.telegram.org/bot<token>/<method>`.

### Checking for new messages

Use the `getUpdates` method to pull for new messages. The skill bundles a helper script for this:

```bash
python3 .claude/skills/telegram-message-handler/scripts/pull.py
```

This script reads `.env`, fetches unprocessed updates, filters to the allowed user ID, and prints each message as a JSON line. It also persists the last `update_id` in `.telegram_offset` so you don't re-read old messages.

If you prefer to call the API directly (e.g., via `curl`), the flow is:

1. Read the offset from `.telegram_offset` (or start from 0)
2. `GET /getUpdates?offset=<offset>&timeout=5`
3. Filter results to `message.from.id == <TELEGRAM_ALLOWED_USER_ID from .env>`
4. After processing, write `max(update_id) + 1` to `.telegram_offset`

### Sending a message

```bash
python3 .claude/skills/telegram-message-handler/scripts/send.py <chat_id> "Your message here"
```

Or via curl:

```bash
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": <chat_id>, "text": "...", "parse_mode": "Markdown"}'
```

The `chat_id` comes from the incoming message (`message.chat.id`). Messages support Telegram's Markdown formatting.

For long responses (>4096 characters), split into multiple messages — the send script handles this automatically.

### The typical workflow

When the user says "check Telegram" or "handle Telegram messages":

1. Run the pull script to get new messages
2. For each message from the authorized user:
   - Read and understand what they're asking
   - Process the request (answer questions, run tasks, look things up — whatever is needed)
   - Send the response back to their chat using the send script
3. Summarize to the user (in Claude Code) what messages came in and how you responded

When the user says "send X to Telegram":

1. Use the send script with the appropriate chat_id
2. Confirm to the user that the message was sent

### Authorization

Only process messages from the user ID specified in `TELEGRAM_ALLOWED_USER_ID` in `.env`. If a message comes from a different user, skip it entirely — don't respond to them, don't acknowledge them. This is a personal bot.

### Error handling

If something goes wrong while processing a Telegram message (timeout, API error, task failure, etc.), always send a friendly fallback message so the user isn't left hanging. Use the `--fallback` flag:

```bash
python3 .claude/skills/telegram-message-handler/scripts/send.py <chat_id> "" --fallback
```

This sends a pre-written friendly message letting them know you got their message but hit a snag. The send script also auto-falls back to this message if the original response fails to deliver (e.g., due to Markdown formatting issues).

The key principle: the Telegram user should never send a message and get silence back. Even if Claude Code times out or errors out mid-processing, make sure a friendly acknowledgment gets through.

### Message formatting tips

- Use Markdown for structured responses (bold, links, code blocks)
- Keep responses concise — Telegram is a chat interface, not an essay format
- If the answer involves code, use backtick blocks
- For errors or issues, be direct about what went wrong
