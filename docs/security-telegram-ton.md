# Security checklist for Telegram & TON integrations

## Bot API & webhooks

- Enforce HTTPS termination (TLS 1.2+) for `/tg/webhook` and `/miniapp/webhook`.
- Validate `X-Telegram-Bot-Api-Secret-Token` using `verify_secret_token` to block spoofed requests.
- Keep bot tokens and API credentials inside Render Environment Groups. Never commit them to git.
- Rotate webhook secrets whenever the endpoint changes or after incident response.

## initData validation

- Use `verify_init_data` with a 5-minute TTL. Reject payloads with stale `auth_date`.
- Parse the `user` JSON carefully and avoid storing the whole blob—persist only what is required for the session.
- Combine initData validation with session cookies or short-lived JWTs for defence in depth.

## TON Connect

- Store wallet linkage in a privacy-preserving store (hashed user IDs, encrypted payloads).
- Validate TON Connect proofs via HMAC as implemented in `tonconnect_validator.verify_wallet_proof`.
- Do not log signatures or state_init values; treat them as secrets.

## TON transactions

- Always run testnet transactions first using the sandbox endpoint before switching to mainnet.
- Monitor balances and transaction statuses via audit logs. Emit alerts when large transactions are requested.

## MTProto vs Bot API

- Use MTProto (TDLib) only when strictly necessary. It requires additional secure storage (encryption keys and sessions).
- Prefer the Bot API because it piggybacks on HTTPS and has fewer moving pieces.
