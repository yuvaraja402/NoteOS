from functools import lru_cache
from os import getenv


class Settings:
    def __init__(self):
        self.app_name = "NotesOS API"
        self.environment = getenv("NOTEOS_ENV", "local")
        self.aws_region = getenv("AWS_REGION", "ca-central-1")
        self.cors_origins = [
            value.strip()
            for value in getenv("CORS_ORIGINS", "http://localhost:3050").split(",")
            if value.strip()
        ]
        self.table_name = getenv("DYNAMODB_TABLE_NAME", "")
        self.redis_host = getenv("REDIS_HOST", "")
        self.redis_port = int(getenv("REDIS_PORT", "6379"))
        self.redis_auth_ssm_param = getenv("REDIS_AUTH_TOKEN_SSM_PARAM", "")
        self.session_key_ssm_param = getenv("SESSION_SIGNING_KEY_SSM_PARAM", "")
        self.flush_idle_seconds = int(getenv("FLUSH_IDLE_SECONDS", "60"))
        self.flush_max_seconds = int(getenv("FLUSH_MAX_SECONDS", "300"))
        self.flush_poll_seconds = int(getenv("FLUSH_POLL_SECONDS", "5"))
        self.cache_ttl_seconds = int(getenv("CACHE_TTL_SECONDS", "86400"))
        self.max_notes = 100

    @property
    def is_production_like(self):
        return self.environment in {"staging", "production"}

    def validate(self):
        if self.environment not in {"local", "staging", "production"}:
            raise RuntimeError("NOTEOS_ENV must be local, staging, or production.")
        if self.is_production_like and "*" in self.cors_origins:
            raise RuntimeError("Deployed environments require explicit CORS origins.")
        for name, value in {
            "DYNAMODB_TABLE_NAME": self.table_name,
            "REDIS_HOST": self.redis_host,
            "REDIS_AUTH_TOKEN_SSM_PARAM": self.redis_auth_ssm_param,
            "SESSION_SIGNING_KEY_SSM_PARAM": self.session_key_ssm_param,
        }.items():
            if not value:
                raise RuntimeError(f"{name} is required. No local database fallback is configured.")
        if not all(path.startswith("/") for path in (self.redis_auth_ssm_param, self.session_key_ssm_param)):
            raise RuntimeError("Secret references must be absolute SSM parameter paths.")
        if not 1 <= self.flush_idle_seconds <= self.flush_max_seconds <= 3600:
            raise RuntimeError("Flush intervals must satisfy 1 <= idle <= max <= 3600.")
        if not 1 <= self.flush_poll_seconds <= self.flush_idle_seconds:
            raise RuntimeError("Flush polling must be between one second and the idle interval.")
        if self.cache_ttl_seconds < self.flush_max_seconds * 2:
            raise RuntimeError("The clean-cache TTL must exceed twice the maximum flush window.")


@lru_cache
def get_settings():
    settings = Settings()
    settings.validate()
    return settings
