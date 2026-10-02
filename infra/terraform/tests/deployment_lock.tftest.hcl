# Mocked planning only: these tests never authenticate to AWS or apply resources.
mock_provider "aws" {}

variables {
  redis_auth_token_ssm_parameter_name    = "/noteos/test/redis/auth-token"
  session_signing_key_ssm_parameter_name = "/noteos/test/session/signing-key"
  runtime_secrets_kms_key_arn            = "arn:aws:kms:ca-central-1:123456789012:key/00000000-0000-0000-0000-000000000000"
  web_image                              = "example.invalid/noteos-web:test"
  api_image                              = "example.invalid/noteos-api:test"
  allowed_origin                         = "https://notes.example.com"
  acm_certificate_arn                    = "arn:aws:acm:ca-central-1:123456789012:certificate/00000000-0000-0000-0000-000000000000"
}

run "default_is_locked" {
  command         = plan
  expect_failures = [var.aws_deployment_enabled]
}

run "explicit_false_is_locked" {
  command = plan
  variables {
    aws_deployment_enabled = false
  }
  expect_failures = [var.aws_deployment_enabled]
}

run "targeted_plan_is_locked" {
  command = plan
  plan_options {
    target = [aws_kms_key.redis]
  }
  expect_failures = [var.aws_deployment_enabled]
}
