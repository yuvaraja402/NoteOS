import boto3

from app.config import get_settings


def get_database_url() -> str:
    settings = get_settings()
    if not settings.database_url_ssm_param:
        if settings.is_production_like and settings.database_url.startswith("sqlite"):
            raise RuntimeError("Production-like environments cannot use SQLite.")
        return settings.database_url

    ssm = boto3.client("ssm", region_name=settings.aws_region)
    response = ssm.get_parameter(
        Name=settings.database_url_ssm_param,
        WithDecryption=True,
    )
    parameter = response["Parameter"]
    if parameter["Type"] != "SecureString":
        raise RuntimeError("The database URL parameter must be an SSM SecureString.")

    database_url = parameter["Value"]
    if settings.is_production_like and not database_url.startswith("postgresql"):
        raise RuntimeError("Deployed environments require a PostgreSQL database URL.")
    return database_url
