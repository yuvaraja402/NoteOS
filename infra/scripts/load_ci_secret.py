"""Load a single SSM SecureString into the current GitHub Actions job."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def load_secret(parameter_name: str, env_name: str) -> None:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", env_name):
        raise ValueError("Invalid environment variable name.")
    if not parameter_name.startswith("/"):
        raise ValueError("Use an absolute SSM parameter path.")
    env_file = Path(os.environ["GITHUB_ENV"])
    result = subprocess.run(
        [
            "aws", "ssm", "get-parameter",
            "--name", parameter_name,
            "--with-decryption",
            "--output", "json",
            "--no-cli-pager",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode:
        # AWS errors may include request details; keep them out of CI logs.
        raise RuntimeError("SSM lookup failed. Check the parameter, region, and IAM access.")
    parameter = json.loads(result.stdout)["Parameter"]
    if parameter["Type"] != "SecureString":
        raise ValueError("CI secrets must be SSM SecureString parameters.")
    value = parameter["Value"]
    if not value or any(char in value for char in ("\r", "\n", "\0")):
        raise ValueError("Expected a non-empty, single-line secret.")
    # Escape workflow-command data before masking; never expose values as outputs.
    print(f"::add-mask::{value.replace('%', '%25')}", flush=True)
    with env_file.open("a", encoding="utf-8") as handle:
        handle.write(f"{env_name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parameter_name")
    parser.add_argument("env_name")
    args = parser.parse_args()
    try:
        load_secret(args.parameter_name, args.env_name)
    except (KeyError, ValueError, RuntimeError, OSError, subprocess.TimeoutExpired):
        print("Unable to load the CI secret. Check SSM SecureString and OIDC configuration.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
