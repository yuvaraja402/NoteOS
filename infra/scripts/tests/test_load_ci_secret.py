import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "load_ci_secret", Path(__file__).resolve().parents[1] / "load_ci_secret.py"
)
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)


class LoadSecretTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.env_file = Path(self.directory.name) / "job-env"
        env_patch = patch.dict(os.environ, {"GITHUB_ENV": str(self.env_file)})
        env_patch.start()
        self.addCleanup(env_patch.stop)

    def response(self, value="test%value", parameter_type="SecureString", code=0):
        return subprocess.CompletedProcess(
            [], code,
            json.dumps({"Parameter": {"Type": parameter_type, "Value": value}}),
            "AWS request details",
        )

    def test_masks_value_before_export_and_requests_decryption(self):
        logs = io.StringIO()
        with patch.object(loader.subprocess, "run", return_value=self.response()) as run:
            with contextlib.redirect_stdout(logs):
                loader.load_secret("/noteos/ci/snyk-token", "SNYK_TOKEN")
        self.assertEqual(logs.getvalue(), "::add-mask::test%25value\n")
        self.assertEqual(self.env_file.read_text(), "SNYK_TOKEN=test%value\n")
        self.assertIn("--with-decryption", run.call_args.args[0])
        self.assertTrue(run.call_args.kwargs["capture_output"])

    def test_rejects_workflow_command_injection_and_empty_values(self):
        for value in ("", "value\nOTHER_VAR=unsafe", "value\r::error::unsafe", "value\0"):
            with self.subTest(value=repr(value)):
                with patch.object(loader.subprocess, "run", return_value=self.response(value)):
                    with self.assertRaises(ValueError):
                        loader.load_secret("/noteos/ci/snyk-token", "SNYK_TOKEN")
                self.assertFalse(self.env_file.exists())

    def test_rejects_plaintext_parameters(self):
        with patch.object(loader.subprocess, "run", return_value=self.response(parameter_type="String")):
            with self.assertRaises(ValueError):
                loader.load_secret("/noteos/ci/snyk-token", "SNYK_TOKEN")
        self.assertFalse(self.env_file.exists())

    def test_aws_errors_do_not_export_or_echo_response(self):
        logs = io.StringIO()
        with patch.object(loader.subprocess, "run", return_value=self.response(code=1)):
            with contextlib.redirect_stdout(logs), self.assertRaises(RuntimeError):
                loader.load_secret("/noteos/ci/snyk-token", "SNYK_TOKEN")
        self.assertEqual(logs.getvalue(), "")
        self.assertFalse(self.env_file.exists())

    def test_rejects_invalid_names_before_calling_aws(self):
        with patch.object(loader.subprocess, "run") as run:
            with self.assertRaises(ValueError):
                loader.load_secret("/noteos/ci/snyk-token", "SNYK_TOKEN\nBAD")
            with self.assertRaises(ValueError):
                loader.load_secret("relative/path", "SNYK_TOKEN")
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
