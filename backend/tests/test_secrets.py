import os
import unittest
from unittest.mock import Mock, patch

from app.config import Settings
from app.secrets import read_secret


class SecretTests(unittest.TestCase):
    def test_ssm_requires_secure_string_and_decryption(self):
        client = Mock()
        client.get_parameter.return_value = {"Parameter": {"Type": "SecureString", "Value": "test-value"}}
        with patch("app.secrets.boto3.client", return_value=client) as factory:
            self.assertEqual(read_secret("/noteos/production/session/key", "ca-central-1"), "test-value")
        factory.assert_called_once_with("ssm", region_name="ca-central-1")
        client.get_parameter.assert_called_once_with(Name="/noteos/production/session/key", WithDecryption=True)

    def test_empty_or_plaintext_secret_is_rejected(self):
        for kind, value in (("String", "value"), ("SecureString", "")):
            client = Mock()
            client.get_parameter.return_value = {"Parameter": {"Type": kind, "Value": value}}
            with patch("app.secrets.boto3.client", return_value=client), self.assertRaises(RuntimeError):
                read_secret("/noteos/production/session/key", "ca-central-1")

    def test_backend_has_no_local_database_fallback(self):
        with patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "", "REDIS_HOST": ""}):
            with self.assertRaises(RuntimeError):
                Settings().validate()

    def test_cloud_configuration_and_time_limits(self):
        with patch.dict(os.environ, {
            "NOTEOS_ENV": "production", "DYNAMODB_TABLE_NAME": "notes",
            "REDIS_HOST": "cache.example.com",
            "REDIS_AUTH_TOKEN_SSM_PARAM": "/noteos/production/redis/auth",
            "SESSION_SIGNING_KEY_SSM_PARAM": "/noteos/production/session/key",
        }):
            settings = Settings()
            settings.validate()
            settings.flush_max_seconds = 10
            with self.assertRaises(RuntimeError):
                settings.validate()

    def test_environment_typo_cannot_bypass_validation(self):
        settings = Settings()
        settings.environment = "prodution"
        with self.assertRaises(RuntimeError):
            settings.validate()


if __name__ == "__main__":
    unittest.main()
