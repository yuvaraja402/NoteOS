from functools import lru_cache
from os import getenv


class Settings:
    app_name = "NotesOS API"
    environment = getenv("NOTEOS_ENV", "local")
    aws_region = getenv("AWS_REGION", "ca-central-1")
    cors_origins = [
        origin.strip()
        for origin in getenv("CORS_ORIGINS", "http://localhost:3050").split(",")
        if origin.strip()
    ]
    database_url = getenv("NOTEOS_DATABASE_URL", "sqlite:///./noteos.db")
    database_url_ssm_param = getenv("NOTEOS_DATABASE_URL_SSM_PARAM", "")

    @property
    def is_production_like(self) -> bool:
        return self.environment in {"staging", "production"}

    def validate(self) -> None:
        if self.environment not in {"local", "staging", "production"}:
            raise RuntimeError("NOTEOS_ENV must be local, staging, or production.")

        if self.is_production_like and "*" in self.cors_origins:
            raise RuntimeError("CORS_ORIGINS cannot contain '*' outside local development.")

        if self.is_production_like and not self.database_url_ssm_param:
            raise RuntimeError(
                "NOTEOS_DATABASE_URL_SSM_PARAM is required outside local development."
            )

        if self.is_production_like and getenv("NOTEOS_DATABASE_URL"):
            raise RuntimeError("Use SSM for the database URL outside local development.")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings
