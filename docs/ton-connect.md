# TON Connect integration

Use the official TON Connect SDK to link user wallets to our dApps.

- Developer guidelines: [TON Docs](https://docs.ton.org/v3/guidelines/ton-connect/guidelines/developers)
- SDK reference: [ton-connect.github.io/sdk](https://ton-connect.github.io/sdk/index.html)

## Front-end (Astro)

1. Install the UI package:
   ```bash
   npm install @tonconnect/ui
   ```
2. Render a connect button in Astro:
   ```ts
   import { TonConnectUI } from '@tonconnect/ui';

   const tonConnectUI = new TonConnectUI({
     manifestUrl: 'https://<your-host>/tonconnect-manifest.json'
   });

   tonConnectUI.onStatusChange(walletInfo => {
     window.dispatchEvent(new CustomEvent('tonconnect:wallet', { detail: walletInfo }));
   });
   ```
3. Store the wallet address in the session after the backend validates the proof.

## Backend validation

- Use `app/integrations/ton/tonconnect_validator.py` to decode payloads and verify HMAC-based wallet proofs.
- Persist the mapping `user_id -> wallet_address` in an encrypted store. Never log the raw proof payload.
- Rotate the shared secret used for proof validation via Render secrets.

## Privacy & UX

- Display a clear consent screen explaining what data is linked.
- Allow users to disconnect their wallet (remove the mapping and revoke stored proofs).
- Only request permissions necessary for the feature (read balance, initiate transaction, etc.).
