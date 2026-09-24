# interstellar-siwe-login

Automates wallet sign-in ("Sign-In With Ethereum") for [interstellar.dachain.io](https://interstellar.dachain.io) — the DAC Quantum Chain mainnet launch portal.

It reproduces the exact flow the site's own frontend does in the browser:

1. `POST /api/v1/auth/siwe/nonce/` — get a nonce for a wallet address
2. Build and sign the SIWE message locally with the wallet's private key (derived from its seed phrase)
3. `POST /api/v1/auth/siwe/` — submit the signed message, get back a session

No browser, no wallet extension — pure HTTP + local signing.

## Features

- Single-wallet login (`siwe_login.py`) or bulk login for a whole list of wallets (`mass_login.py`, 20 parallel workers by default)
- Every request goes through a proxy — there is no direct-connection fallback
- If a wallet's assigned proxy is dead, a fresh one is pulled from the spare pool and the wallet's assignment is updated, so it never gets reassigned
- Resumable: already-logged-in wallets are skipped on re-run

## Setup

```bash
pip install -r requirements.txt
```

Copy the example data files and fill them with your own wallets/proxies:

```bash
cp Boost.example.txt Boost.txt
cp Proxy.example.txt Proxy.txt
```

**`Boost.txt`** — one JSON object per line, one per wallet:

```json
{"address": "0x...", "proxy": "user:pass@host:port", "seed_phrase": "your twelve or twenty-four word mnemonic", "dacc_gained": 0, "timestamp": 0}
```

Only `proxy` and `seed_phrase` are actually used; the other fields are ignored (kept for compatibility with farming tools that produce this format).

**`Proxy.txt`** — one `user:pass@host:port` proxy per line. This is the spare pool used to replace any dead proxy found in `Boost.txt`.

> `Boost.txt`, `Proxy.txt` and the generated result/log files are gitignored — your seed phrases and proxy credentials never get committed.

## Usage

**Log in a single wallet** (the first line of `Boost.txt`):

```bash
python siwe_login.py
```

**Log in every wallet in `Boost.txt`**, 20 at a time:

```bash
python mass_login.py
```

Progress is written to `login_results.jsonl` as it goes (one JSON line per wallet: `ok`, `address`, `user_id`, `status`, `created`, `proxy`). If the run is interrupted, just run it again — wallets already marked `ok` are skipped.

## Configuration

All endpoints, headers and tunables (thread count, timeouts, max proxy retries per wallet) live in `config.py`.
