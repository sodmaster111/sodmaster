# Telegram Bot API integration

The project uses the official [tdlib/telegram-bot-api](https://github.com/tdlib/telegram-bot-api) distribution. Two modes are supported:

1. **Hosted Bot API (default).** All requests are sent to `https://api.telegram.org` using the bot token stored in the Render environment group.
2. **Self-hosted Bot API server (optional).** Deploy the official container or binary behind an internal Nginx/Cloudflare endpoint. The FastAPI adapter expects the service to be reachable at `https://<your-bot-api-domain>` and forwards Bot API calls to port `8081` on the private network.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Bot token used by the HTTP adapter and the aiogram runner. |
| `TELEGRAM_API_ID` | Only required when using the self-hosted Bot API server. Used by the server to authenticate to Telegram. |
| `TELEGRAM_API_HASH` | Companion secret for `TELEGRAM_API_ID`. |
| `TELEGRAM_BOT_API_BASE` | Optional override for the Bot API base URL (e.g. `https://bot-api.internal`). |

Store secrets inside the shared Render **Environment Group** so they are not leaked into source control.

## Running the local Bot API server

1. Deploy the [telegram-bot-api](https://github.com/tdlib/telegram-bot-api) binary (or Docker image) close to the application. Enable HTTPS termination with Nginx or Cloudflare and forward traffic to the internal port `8081`.
2. Configure environment variables on the server:
   ```bash
   export TELEGRAM_API_ID=<your_api_id>
   export TELEGRAM_API_HASH=<your_api_hash>
   telegram-bot-api --local --http-port=8081 --dir=/var/lib/tg-bot-api
   ```
3. Update the application environment with `TELEGRAM_BOT_API_BASE=https://bot-api.internal` (matching the reverse proxy hostname).
4. Use the wrapper in `app/integrations/telegram/bot_api.py` to call methods. The adapter supports `sendMessage`, `setWebhook`, `deleteWebhook`, and arbitrary method calls via `call()`.

When running behind Cloudflare, enable **Authenticated Origin Pulls** or Mutual TLS to prevent the endpoint from being exposed. Rate limit ingress to mitigate brute-force attacks.
