#!/usr/bin/env python3
"""
Mass SIWE login for every wallet in Boost.txt.

- 20 parallel workers by default (config.NUM_THREADS).
- Each wallet uses its own assigned proxy from Boost.txt.
- If a proxy is dead (connection/timeout/proxy error), it is swapped for a
  fresh one popped from Proxy.txt. The dead assignment is overwritten in
  Boost.txt (so the wallet keeps a working proxy going forward) and the
  freshly-taken proxy is removed from Proxy.txt immediately (thread-safe),
  so it can never be handed out twice.
- Resumable: wallets already logged in successfully (per login_results.jsonl)
  are skipped on the next run.
"""

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
from siwe_login import SiweSession

PROXY_FAIL_EXCEPTIONS = (
    requests.exceptions.ProxyError,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


class ProxyPool:
    """Thread-safe pool of spare proxies backed by Proxy.txt."""

    def __init__(self, proxy_file: str):
        self.proxy_file = proxy_file
        self.lock = threading.Lock()
        with open(proxy_file, "r", encoding="utf-8") as f:
            self._pool = [line.strip() for line in f if line.strip()]

    def take(self):
        with self.lock:
            if not self._pool:
                return None
            proxy = self._pool.pop(0)
            self._flush()
            return proxy

    def _flush(self):
        with open(self.proxy_file, "w", encoding="utf-8") as f:
            for p in self._pool:
                f.write(p + "\n")

    def remaining(self) -> int:
        with self.lock:
            return len(self._pool)


class BoostStore:
    """In-memory copy of Boost.txt with thread-safe proxy updates persisted back to disk."""

    def __init__(self, boost_file: str):
        self.boost_file = boost_file
        self.lock = threading.Lock()
        self.entries = []
        with open(boost_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.entries.append(json.loads(line))

    def update_proxy(self, index: int, new_proxy: str):
        with self.lock:
            self.entries[index]["proxy"] = new_proxy
            self._flush()

    def _flush(self):
        with open(self.boost_file, "w", encoding="utf-8") as f:
            for e in self.entries:
                f.write(json.dumps(e) + "\n")


class ResultsWriter:
    """Append-only, resumable results log."""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.done_addresses = set()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("ok") and rec.get("address"):
                            self.done_addresses.add(rec["address"].lower())
                    except Exception:
                        pass

    def is_done(self, address: str) -> bool:
        return bool(address) and address.lower() in self.done_addresses

    def write(self, record: dict):
        with self.lock:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
            if record.get("ok") and record.get("address"):
                self.done_addresses.add(record["address"].lower())


def process_wallet(index: int, entry: dict, proxy_pool: ProxyPool, boost_store: BoostStore,
                    results: ResultsWriter) -> dict:
    address = entry.get("address")
    seed = entry.get("seed_phrase")
    proxy = entry.get("proxy")

    if results.is_done(address):
        return {"address": address, "ok": True, "skipped": True}

    last_error = None

    for attempt in range(1, config.MAX_PROXY_ATTEMPTS + 1):
        if not proxy or proxy.strip().lower() == "noproxy":
            proxy = proxy_pool.take()
            if not proxy:
                last_error = "no spare proxies left in pool"
                break
            boost_store.update_proxy(index, proxy)

        siwe = SiweSession(seed_phrase=seed, expected_address=address, proxy=proxy, verbose=False)
        try:
            result = siwe.login()
            record = {
                "ok": True,
                "address": result["address"],
                "user_id": result["user"].get("id"),
                "status": result["user"].get("status"),
                "created": result.get("created"),
                "proxy": proxy,
            }
            results.write(record)
            return record
        except PROXY_FAIL_EXCEPTIONS as e:
            last_error = f"proxy dead ({attempt}/{config.MAX_PROXY_ATTEMPTS}): {e}"
            new_proxy = proxy_pool.take()
            if not new_proxy:
                last_error += " — no spare proxies left"
                break
            proxy = new_proxy
            boost_store.update_proxy(index, proxy)
            continue
        except Exception as e:
            last_error = str(e)
            break

    record = {"ok": False, "address": address, "error": last_error, "proxy": proxy}
    results.write(record)
    return record


def main():
    print("╔" + "═" * 60 + "╗")
    print("║" + "  INTERSTELLAR MASS SIWE LOGIN".center(60) + "║")
    print("╚" + "═" * 60 + "╝")
    print()

    boost_store = BoostStore(config.BOOST_FILE)
    proxy_pool = ProxyPool(config.PROXY_FILE)
    results = ResultsWriter(config.RESULTS_FILE)

    total = len(boost_store.entries)
    todo = [(i, e) for i, e in enumerate(boost_store.entries) if not results.is_done(e.get("address"))]

    print(f"[*] {total} wallets in {config.BOOST_FILE}")
    print(f"[*] {len(todo)} remaining to log in (resuming from {config.RESULTS_FILE})")
    print(f"[*] {proxy_pool.remaining()} spare proxies available for replacement")
    print(f"[*] Using {config.NUM_THREADS} parallel workers")
    print()

    ok_count = 0
    fail_count = 0
    processed = 0

    with ThreadPoolExecutor(max_workers=config.NUM_THREADS) as executor:
        futures = {
            executor.submit(process_wallet, i, e, proxy_pool, boost_store, results): e.get("address")
            for i, e in todo
        }
        for future in as_completed(futures):
            address = futures[future]
            processed += 1
            try:
                res = future.result()
            except Exception as e:
                fail_count += 1
                print(f"  [{processed}/{len(todo)}] [ERROR] {address}: {e}")
                continue

            if res.get("skipped"):
                ok_count += 1
                continue
            if res.get("ok"):
                ok_count += 1
                print(f"  [{processed}/{len(todo)}] [OK] {address} "
                      f"user_id={res.get('user_id')} status={res.get('status')} created={res.get('created')}")
            else:
                fail_count += 1
                print(f"  [{processed}/{len(todo)}] [FAIL] {address}: {res.get('error')}")

    print()
    print("╔" + "═" * 60 + "╗")
    print(f"  DONE — OK: {ok_count}  FAIL: {fail_count}  spare proxies left: {proxy_pool.remaining()}")
    print("╚" + "═" * 60 + "╝")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] Stopped by user (progress saved — re-run to resume)")
        sys.exit(0)
