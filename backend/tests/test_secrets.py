import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.config import Settings
from app.secrets import get_database_url


class RuntimeSecretTests(unittest.TestCase):
    def settings(self, production=True, parameter="/noteos/production/database/url"):
        return SimpleNamespace(
            is_production_like=production,
            database_url_ssm_param=parameter,
            database_url="sqlite:///./noteos.db",
            aws_region="ca-central-1",
        )

    def test_runtime_uses_ssm_decryption_in_configured_region(self):
        client = Mock()
        url = "postgresql+psycopg2://user:encoded%25password@db:5432/noteos"
        client.get_parameter.return_value = {
            "Parameter": {"Type": "SecureString", "Value": url}
        }
        with patch("app.secrets.get_settings", return_value=self.settings()):
            with patch("app.secrets.boto3.client", return_value=client) as factory:
                self.assertEqual(get_database_url(), url)
        factory.assert_called_once_with("ssm", region_name="ca-central-1")
        client.get_parameter.assert_called_once_with(
            Name="/noteos/production/database/url", WithDecryption=True
        )

    def test_runtime_rejects_plaintext_or_non_postgres_ssm_values(self):
        for parameter in (
            {"Type": "String", "Value": "postgresql://user:pass@db/noteos"},
            {"Type": "SecureString", "Value": "sqlite:///noteos.db"},
        ):
            client = Mock()
            client.get_parameter.return_value = {"Parameter": parameter}
            with patch("app.secrets.get_settings", return_value=self.settings()):
                with patch("app.secrets.boto3.client", return_value=client):
                    with self.assertRaises(RuntimeError):
                        get_database_url()

    def test_local_development_needs_no_aws_access(self):
        with patch("app.secrets.get_settings", return_value=self.settings(False, "")):
            with patch("app.secrets.boto3.client") as factory:
                self.assertEqual(get_database_url(), "sqlite:///./noteos.db")
        factory.assert_not_called()

    def test_deployed_configuration_requires_ssm_and_rejects_raw_url(self):
        settings = Settings()
        settings.environment = "production"
        settings.database_url_ssm_param = ""
        with self.assertRaises(RuntimeError):
            settings.validate()
        settings.database_url_ssm_param = "/noteos/production/database/url"
        with patch.dict(os.environ, {"NOTEOS_DATABASE_URL": "postgresql://user:pass@db/noteos"}):
            with self.assertRaises(RuntimeError):
                settings.validate()

    def test_invalid_environment_cannot_bypass_guardrails(self):
        settings = Settings()
        settings.environment = "prodution"
        with self.assertRaises(RuntimeError):
            settings.validate()


if __name__ == "__main__":
    unittest.main()
