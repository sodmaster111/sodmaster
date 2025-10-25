# Treasury Operations Playbook

## 1. Settlement Flow Overview
1. **Subscription capture** – Customers approve a recurring crypto settlement when they create a subscription invoice. Funds land in the designated settlement address generated per subscription tier.
2. **Network-level consolidation** – Receipts are swept into the respective multisig treasury on each chain to guarantee dual-control of assets:
   - Ethereum and EVM chains: consolidated to a Gnosis Safe.
   - TON network: consolidated to the TON multisig wallet.
   - Bitcoin: routed into the BTCPay-controlled cold wallet.
3. **Treasury review and release** – Finance leadership reviews inflows, documents hedging or conversion notes, and then schedules withdrawals from each multisig to fund operating accounts or OTC desks.

## 2. Reference Treasury Setups
- **Gnosis Safe (EVM)** – Core multisig for ETH, USDC, and stablecoin denominated inflows. Requires CFO + CLO signatures for outbound transfers.
- **TON Multisig** – Handles TON-based subscriptions and grants. Mirrors the same CFO/CLO approval pattern with seed storage in Shamir-split hardware modules.
- **BTCPay Cold Wallet** – Air-gapped storage for BTC receipts. CFO authorizes signed PSBT; CLO witnesses and countersigns before broadcast.

## 3. Whitelisting API
`POST /api/v1/treasury/whitelist_wallet`

```json
{
  "chain": "ETH",
  "address": "0x1234...ABCD"
}
```

- **Headers**: `X-Org-Roles: CFO,CLO`
- **Access**: Limited to requests carrying at least one of the roles `CFO` or `CLO`.
- **Response**: `{ "status": "whitelisted", "chain": "ETH", "address": "0x1234..." }`

This endpoint updates the in-memory treasury whitelist used by automated payout workflows to validate withdrawal targets before signing.

## 4. Testing Guidance
Simulate role-restricted access by sending FastAPI TestClient requests with different `X-Org-Roles` headers:

- Expect **HTTP 200** when `CFO` or `CLO` is present.
- Expect **HTTP 403** when unauthorized roles (or no roles) attempt to call the endpoint.

This ensures only the designated finance leadership can register payout destinations.
