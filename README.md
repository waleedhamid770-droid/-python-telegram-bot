# Python Telegram Bot

A ready-to-run Telegram bot built with [python-telegram-bot](https://python-telegram-bot.org/).

## Features

- `/start` welcome flow
- `/help` command guide
- `/about` bot description
- `/id` current chat ID
- Text echo handler
- Structured logging and safe error handling
- Long polling with all Telegram update types enabled

## Run it

1. Create a bot through Telegram's [@BotFather](https://t.me/BotFather).
2. Add the token to Replit Secrets with the name `TELEGRAM_BOT_TOKEN`.
3. Start the bot:

   ```bash
   python bot.py
   ```

The token is read only from the environment and is never stored in source
control. See `.env.example` for the optional logging setting.

## Extend it

Add an async handler function in `bot.py`, then register it in
`build_application()`. The `python-telegram-bot` documentation has examples
for inline keyboards, conversations, files, webhooks, and scheduled jobs.