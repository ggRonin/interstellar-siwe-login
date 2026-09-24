"""Configuration for the interstellar.dachain.io SIWE login bot."""

BASE_URL = "https://interstellar.dachain.io"
API_BASE = f"{BASE_URL}/api/v1"

NONCE_ENDPOINT = f"{API_BASE}/auth/siwe/nonce/"
SIWE_ENDPOINT = f"{API_BASE}/auth/siwe/"
ME_ENDPOINT = f"{API_BASE}/auth/me/"

# Same derivation path used by the Dachain Boost tooling that generated Boost.txt.
DERIVATION_PATH = "m/44'/60'/0'/0/0"

# SIWE message parameters observed from the live site (DevTools capture).
SIWE_DOMAIN = "interstellar.dachain.io"
SIWE_URI = "https://interstellar.dachain.io"
SIWE_VERSION = "1"
SIWE_CHAIN_ID = 21892
SIWE_STATEMENT = "Sign in to Interstellar. Your wallet is your identity."
SIWE_EXPIRATION_MINUTES = 10

API_TIMEOUT = 20

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-CH-UA": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-CH-UA-Mobile": "?0",
    "Sec-CH-UA-Platform": '"Windows"',
}

BOOST_FILE = "Boost.txt"
PROXY_FILE = "Proxy.txt"
RESULTS_FILE = "login_results.jsonl"

NUM_THREADS = 20
MAX_PROXY_ATTEMPTS = 3  # original proxy + up to N-1 replacements before giving up on a wallet
