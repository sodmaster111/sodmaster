# TON smart contracts with Tact

[Tact](https://github.com/tact-lang/tact) is the recommended high-level language for TON smart contracts. Keep all contracts inside the `contracts/` branch and run builds in CI to guarantee reproducibility.

## Scaffolding a contract

1. Install the toolchain:
   ```bash
   npm install -g tact
   ```
2. Scaffold a Jetton (fungible token) contract:
   ```bash
   tact init jetton-demo --template jetton
   ```
3. For soul-bound tokens (SBT) use the `sbt` template instead.
4. Commit contract sources to the `contracts/<feature>` branch.

## CI integration

- Add a GitHub Actions workflow step:
  ```yaml
  - name: Build Tact contracts
    run: tact build
  ```
- Ensure runners have access to the Tact binary. Cache the `node_modules/.cache/tact` directory to speed up builds.

## Deployment checklist

- Audit contracts before mainnet deployment.
- Verify the contract bytecode with explorers (tonviewer, tonscan).
- Keep deployment mnemonics in hardware wallets; never in repository files.
