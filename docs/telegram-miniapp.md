# Telegram Mini Apps (Web Apps)

Telegram Mini Apps can render our Astro front-end inside the Telegram client with a fullscreen WebView. The latest Mini Apps 2.0 updates (late 2024) include native [Stars](https://t.me/durov/221) payments and persistent storage via cloud keys.

## Routing

- All Mini App assets are served from the `/miniapp/*` prefix. The FastAPI router in `app/miniapp/routes.py` validates incoming webhooks and provides an endpoint for verifying the `initData` signature.
- Astro builds should include a `public/miniapp` entry with pre-built bundles.

## Client-side bootstrapping

1. Load the Telegram WebApp SDK in Astro:
   ```html
   <script src="https://telegram.org/js/telegram-web-app.js"></script>
   ```
2. Initialise the app in your component and request fullscreen mode:
   ```ts
   Telegram.WebApp.expand();
   Telegram.WebApp.enableClosingConfirmation();
   ```
3. Expose a `Connect Wallet` button backed by TON Connect (see `docs/ton-connect.md`).

## Validating initData

The browser sends a signed `initData` string on load. Send it to `/miniapp/verify` and verify it on the backend using `verify_init_data` helper. Reject requests when the signature mismatches or the `auth_date` is older than 5 minutes.

```python
from app.integrations.telegram.webhook import verify_init_data

init_data_map = dict(parse_qsl(init_data))
if not verify_init_data(init_data_map, TELEGRAM_BOT_TOKEN):
    raise HTTPException(status_code=400, detail="invalid_init_data")
```

## Handling Stars payments

- Mini Apps can open the in-app purchase dialog via `Telegram.WebApp.openInvoice`.
- Use the Bot API `createInvoiceLink` to prepare a payment request.
- After the webhook is delivered (`/miniapp/webhook`), record the transaction ID in the audit trail.

## Security tips

- Serve static assets over HTTPS and enable CSP headers to restrict inline scripts.
- Keep webhook secrets random and rotate them through Render environment groups.
- Always validate `initData` on the server and store only the minimal user profile necessary for the session.
