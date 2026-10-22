"""Configuration read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def parse_users(raw: str) -> dict[str, str]:
    """Parse DEMO_USERS ("name:password,name2:password2")."""
    users: dict[str, str] = {}
    for pair in (p.strip() for p in raw.split(",")):
        name, _, password = pair.partition(":")
        if name and password:
            users[name] = password
    return users


@dataclass(frozen=True)
class Config:
    app_jwt_secret: str
    demo_users: dict[str, str]
    demo_mode: bool = False
    twilio_account_sid: str = ""
    twilio_api_key_sid: str = ""
    twilio_api_key_secret: str = ""
    twilio_twiml_app_sid: str = ""
    twilio_push_credential_sid: str = ""
    # Detection plug-ins (docs/plugins.md). "none" never warns.
    phrase_engine: str = "none"
    detector_provider: str = "none"
    detector_timeout_seconds: float = 3.0
    detector_rate_per_minute: int = 40
    detector_url: str = ""
    detector_token: str = ""
    detection_plugins: tuple[str, ...] = ()
    heartbeat_seconds: float = 3.0
    # Multiplies every delay in the demo call driver; tests use a tiny value.
    demo_time_scale: float = 1.0
    token_ttl_seconds: int = 12 * 60 * 60
    allowed_langs: frozenset[str] = field(default_factory=lambda: frozenset({"en", "hi", "pa"}))

    @property
    def voice_configured(self) -> bool:
        return all(
            (
                self.twilio_account_sid,
                self.twilio_api_key_sid,
                self.twilio_api_key_secret,
                self.twilio_twiml_app_sid,
            )
        )


def load_config() -> Config:
    secret = os.environ.get("APP_JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("APP_JWT_SECRET must be set to 32 or more characters")
    users = parse_users(os.environ.get("DEMO_USERS", ""))
    if not users:
        raise RuntimeError("DEMO_USERS must hold at least one username:password pair")
    return Config(
        app_jwt_secret=secret,
        demo_users=users,
        demo_mode=os.environ.get("DEMO_MODE", "0") == "1",
        twilio_account_sid=os.environ.get("TWILIO_ACCOUNT_SID", ""),
        twilio_api_key_sid=os.environ.get("TWILIO_API_KEY_SID", ""),
        twilio_api_key_secret=os.environ.get("TWILIO_API_KEY_SECRET", ""),
        twilio_twiml_app_sid=os.environ.get("TWILIO_TWIML_APP_SID", ""),
        twilio_push_credential_sid=os.environ.get("TWILIO_PUSH_CREDENTIAL_SID", ""),
        phrase_engine=os.environ.get("PHRASE_ENGINE", "none"),
        detector_provider=os.environ.get("DETECTOR_PROVIDER", "none"),
        detector_timeout_seconds=float(os.environ.get("DETECTOR_TIMEOUT", "3.0")),
        detector_rate_per_minute=int(os.environ.get("DETECTOR_RATE_PER_MINUTE", "40")),
        detector_url=os.environ.get("DETECTOR_URL", ""),
        detector_token=os.environ.get("DETECTOR_TOKEN", ""),
        detection_plugins=tuple(m.strip() for m in os.environ.get("DETECTION_PLUGINS", "").split(",") if m.strip()),
    )
