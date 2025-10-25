# Telegram bot frameworks

The runtime prefers [aiogram](https://github.com/aiogram/aiogram) for Python bots. The integration is exposed through `app/integrations/telegram/bot_runner.py`:

- Automatically reads `TELEGRAM_BOT_TOKEN` from the environment.
- Provides stub behaviour when `aiogram` is not available (for local tests).
- Supports webhook deployments with secret validation (`X-Telegram-Bot-Api-Secret-Token`).

## Webhook configuration

1. Serve the webhook endpoint at `/tg/webhook` or `/miniapp/webhook` behind HTTPS.
2. Configure a random secret when calling `setWebhook` through the adapter:
   ```python
   from app.integrations.telegram.bot_api import TelegramBotAPI

   async with TelegramBotAPI() as api:
       await api.set_webhook(
           url="https://<your-host>/tg/webhook",
           secret_token=os.environ["TELEGRAM_WEBHOOK_SECRET"],
           allowed_updates=["message", "callback_query"],
       )
   ```
3. In the FastAPI handler, call `verify_secret_token(request.headers, TELEGRAM_WEBHOOK_SECRET)` before processing the update.

## Polling vs webhook

- **Webhook** is recommended for production deployments. Use Cloudflare Workers or Nginx to terminate TLS and forward to the FastAPI app. Enable request body size limits and IP filtering.
- **Long polling** remains available through `TelegramBotRunner.start_polling()` for quick prototypes.

## Node.js bots

When a JavaScript stack is required, the crew can rely on [grammY](https://github.com/grammyjs/grammY). The same webhook pattern applies. Document webhook URLs and secrets in the service catalog.

## Telethon / TDLib clients

For advanced client-side automations (E2E testing, account login) consider [Telethon](https://github.com/LonamiWebs/Telethon) or TDLib. They require `TELEGRAM_API_ID`/`TELEGRAM_API_HASH` as well as local session storage. Keep API credentials in the secure environment store.
