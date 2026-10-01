"""Authentication, password hashing, rate limiting and request guards.

Design notes
- Passwords are stored as salted PBKDF2-SHA256 hashes (stdlib only). Legacy
  plaintext rows are accepted once and transparently upgraded on login.
- After a successful login the API issues a stateless HMAC-signed bearer
  token. `AuthMiddleware` requires it on every non-public route and checks
  that any user named in the path/query matches the token's user, so one
  child's token cannot read or modify another child's data.
- The signing secret comes from AUTH_SECRET; if unset a random secret is
  generated once and persisted next to the database so tokens survive
  restarts (Fly machines auto-stop).
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# ---------------------------------------------------------------- passwords
_PBKDF2_ITERS = 240_000
_PREFIX = "pbkdf2_sha256"


def hash_password(password: str) -> str:
    """Hash a password. Empty password (passwordless account) stays empty."""
    if not password:
        return ""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERS)
    return f"{_PREFIX}${_PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def is_hashed(stored: Optional[str]) -> bool:
    return bool(stored) and stored.startswith(_PREFIX + "$")


def verify_password(password: str, stored: Optional[str]) -> bool:
    stored = stored or ""
    if not is_hashed(stored):
        # Legacy plaintext (or passwordless "") - constant-time compare.
        return hmac.compare_digest(password.encode(), stored.encode())
    try:
        _, iters, salt_hex, hash_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


# ------------------------------------------------------------------- tokens
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(30 * 24 * 3600)))


def _load_secret() -> bytes:
    env = os.getenv("AUTH_SECRET")
    if env:
        return env.encode()
    from src.db_session import get_db_path

    path = Path(get_db_path()).parent / ".auth_secret"
    try:
        if path.exists():
            return path.read_bytes().strip()
        key = secrets.token_hex(32).encode()
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return key
    except OSError:
        # Read-only FS: fall back to a per-process secret (tokens reset on restart).
        return secrets.token_hex(32).encode()


_SECRET: Optional[bytes] = None


def _secret() -> bytes:
    global _SECRET
    if _SECRET is None:
        _SECRET = _load_secret()
    return _SECRET


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue_token(user_id: int, name: str) -> str:
    payload = _b64(
        json.dumps(
            {"uid": user_id, "n": name, "exp": int(time.time()) + TOKEN_TTL_SECONDS},
            separators=(",", ":"),
        ).encode()
    )
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def parse_token(token: str) -> Optional[dict]:
    try:
        payload, sig = token.split(".", 1)
        expected = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_unb64(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None


# ------------------------------------------------------------ rate limiting
class RateLimiter:
    """Small in-memory sliding-window limiter (single-instance deployment)."""

    def __init__(self):
        self._hits = defaultdict(deque)

    def allow(self, key: str, limit: int, window: int) -> bool:
        if os.getenv("RATE_LIMIT_DISABLED", "").lower() == "true":
            return True  # test environments only
        now = time.time()
        q = self._hits[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        if len(self._hits) > 50_000:  # bound memory
            self._hits.clear()
        return True


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    return (
        request.headers.get("fly-client-ip")
        or (request.client.host if request.client else "unknown")
    )


# --------------------------------------------------------------- middleware
# Routes that must stay reachable without a token.
_PUBLIC = [
    ("POST", re.compile(r"^/users/?$")),  # sign-up
    ("POST", re.compile(r"^/users/[^/]+/verify-password$")),  # login
    ("GET", re.compile(r"^/$")),
    ("GET", re.compile(r"^/healthz$")),
    ("GET", re.compile(r"^/leaderboard/(top|schools|grades)$")),
    ("GET", re.compile(r"^/api/tts/(speak|health|status)$")),
    ("POST", re.compile(r"^/api/tts/speak$")),
    ("GET", re.compile(r"^/moe-words$")),
    ("GET", re.compile(r"^/levels/?(\d+)?$")),
    ("GET", re.compile(r"^/(docs|redoc|openapi\.json)$")),
]
# Admin console has its own HTTP Basic auth (routes depend on `authenticate`).
_ADMIN = re.compile(r"^/(admin|execute_query)(/|$)")

# Path patterns whose first capture group is the acting user's name.
_USER_IN_PATH = [
    re.compile(p)
    for p in (
        r"^/users/([^/]+)/",
        r"^/users/([^/]+)$",
        r"^/words/users/([^/]+)/",
        r"^/tags/user/([^/]+)",
        r"^/tags/available/([^/]+)",
        r"^/login-history/user/([^/]+)",
        r"^/history/(?:study|quiz)/([^/]+)",
        r"^/levels/users/([^/]+)",
        r"^/streaks/users/([^/]+)",
        r"^/streaks/(?!users/)([^/]+)",
        r"^/challenges/user/([^/]+)",
        r"^/lessons/([^/]+)",
    )
]
_USER_QUERY_KEYS = ("user_name", "challenger_name")
_SETTINGS = re.compile(r"^/settings/(\d+)$")

# Per-route throttles: (method, regex, limit, window_seconds, key_by_path_user)
_THROTTLES = [
    ("POST", re.compile(r"^/users/[^/]+/verify-password$"), 10, 300, True),
    ("POST", re.compile(r"^/users/?$"), 10, 3600, False),
    ("GET", re.compile(r"^/api/tts/"), 120, 60, False),
    ("POST", re.compile(r"^/api/tts/"), 120, 60, False),
    ("POST", re.compile(r"^/ai/"), 20, 60, False),
    ("GET", re.compile(r"^/words/\d+/quiz-explanation$"), 30, 60, False),
]


def _is_admin_basic(b64: str) -> bool:
    user, pw = os.getenv("ADMIN_USERNAME"), os.getenv("ADMIN_PASSWORD")
    if not user or not pw:
        return False
    try:
        got = base64.b64decode(b64).decode()
    except Exception:
        return False
    return hmac.compare_digest(got.encode(), f"{user}:{pw}".encode())


def _norm(n: str) -> str:
    return unquote(n or "").strip().upper()


def _json(status: int, detail: str, headers: Optional[dict] = None):
    return JSONResponse({"detail": detail}, status_code=status, headers=headers or {})


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method, path = request.method, request.url.path
        if method == "OPTIONS":
            return await call_next(request)

        ip = client_ip(request)
        for m, rx, limit, window, by_user in _THROTTLES:
            if m == method and rx.match(path):
                key = f"{rx.pattern}|{ip}" + (f"|{path}" if by_user else "")
                if not limiter.allow(key, limit, window):
                    return _json(429, "Too many requests, slow down", {"Retry-After": str(window)})

        # Admin console: CSRF guard (Basic-auth creds are auto-sent by browsers).
        if _ADMIN.match(path):
            if method not in ("GET", "HEAD"):
                origin = request.headers.get("origin")
                if origin and origin.split("://", 1)[-1] != request.headers.get("host"):
                    return _json(403, "Cross-origin admin request blocked")
            return await call_next(request)

        if any(m == method and rx.match(path) for m, rx in _PUBLIC):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        # Operator override: the admin Basic credentials (ADMIN_USERNAME /
        # ADMIN_PASSWORD) may act as any user - used by import scripts.
        if auth.lower().startswith("basic ") and _is_admin_basic(auth[6:].strip()):
            request.state.is_admin = True
            return await call_next(request)
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        claims = parse_token(token) if token else None
        if not claims:
            return _json(401, "Authentication required", {"WWW-Authenticate": "Bearer"})

        target = None
        for rx in _USER_IN_PATH:
            mt = rx.match(path)
            if mt:
                target = _norm(mt.group(1))
                break
        if target is not None and target != _norm(claims["n"]):
            return _json(403, "Not allowed to access another user's data")
        ms = _SETTINGS.match(path)
        if ms and int(ms.group(1)) != claims["uid"]:
            return _json(403, "Not allowed to access another user's data")
        for key in _USER_QUERY_KEYS:
            if key in request.query_params:
                if _norm(request.query_params[key]) != _norm(claims["n"]):
                    return _json(403, "Not allowed to access another user's data")

        request.state.user_name = claims["n"]
        request.state.user_id = claims["uid"]
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/admin"):
            resp.headers.setdefault("Cache-Control", "no-store")
            resp.headers.setdefault(
                "Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
            )
        return resp


def require_same_user(request: Request, name: str):
    """In-route check for body-supplied user names."""
    from fastapi import HTTPException

    if getattr(request.state, "is_admin", False):
        return
    if _norm(name) != _norm(getattr(request.state, "user_name", "")):
        raise HTTPException(status_code=403, detail="Not allowed to act as another user")
