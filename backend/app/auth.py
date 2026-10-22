"""Demo sign-in and short-lived app session tokens."""

from __future__ import annotations

import hmac
import time
from collections import defaultdict, deque

import jwt
from fastapi import Header

from .config import Config
from .errors import ApiError

_ALGORITHM = "HS256"


class Auth:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._failures: dict[str, deque[float]] = defaultdict(deque)

    def login(self, username: str, password: str) -> str:
        self._check_rate(username)
        expected = self._config.demo_users.get(username)
        if expected is None or not hmac.compare_digest(expected, password):
            self._failures[username].append(time.monotonic())
            raise ApiError(401, "bad_credentials", "That username or password didn't match.")
        self._failures.pop(username, None)
        return self.issue(username)

    def issue(self, user_id: str) -> str:
        now = int(time.time())
        payload = {"sub": user_id, "iat": now, "exp": now + self._config.token_ttl_seconds}
        return jwt.encode(payload, self._config.app_jwt_secret, algorithm=_ALGORITHM)

    def verify(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self._config.app_jwt_secret, algorithms=[_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise ApiError(401, "bad_token", "Sign in again.") from exc
        user_id = payload.get("sub")
        if not isinstance(user_id, str) or user_id not in self._config.demo_users:
            raise ApiError(401, "bad_token", "Sign in again.")
        return user_id

    def user_from_header(self, authorization: str | None) -> str:
        if not authorization or not authorization.startswith("Bearer "):
            raise ApiError(401, "missing_token", "Sign in first.")
        return self.verify(authorization.removeprefix("Bearer ").strip())

    def _check_rate(self, username: str) -> None:
        window = self._failures[username]
        now = time.monotonic()
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= 5:
            raise ApiError(429, "too_many_attempts", "Too many attempts. Wait a minute and try again.")


def bearer(authorization: str | None = Header(default=None)) -> str | None:
    return authorization
