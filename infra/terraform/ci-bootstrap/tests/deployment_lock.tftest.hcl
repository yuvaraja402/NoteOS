# Mocked planning only: these tests never authenticate to AWS or apply resources.
mock_provider "aws" {}

variables {
  github_repository = "example/NoteOS"
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
    target = [aws_kms_key.ci]
  }
  expect_failures = [var.aws_deployment_enabled]
}
