# Python Telegram Bot

An extensible Telegram bot built with Python and python-telegram-bot.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `python bot.py` — run the Telegram bot with long polling
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required secret: `TELEGRAM_BOT_TOKEN` — token created with @BotFather

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `bot.py` — bot setup, commands, text echo, and error handling
- `.env.example` — environment variable reference
- `README.md` — setup and extension guide

## Architecture decisions

- Long polling is used for a simple, deployment-friendly first version.
- The bot token is read from `TELEGRAM_BOT_TOKEN` and never committed.
- Handlers are async, matching python-telegram-bot's current application API.

## Product

The bot responds to a small set of helpful commands and echoes regular text,
providing a clean foundation for custom Telegram workflows.

## User preferences

No additional preferences recorded.

## Gotchas

- Add `TELEGRAM_BOT_TOKEN` as a secret before starting `bot.py`.
- The bot must be stopped before switching it between polling and webhook mode.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
