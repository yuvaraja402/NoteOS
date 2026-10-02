output "aws_ci_role_arn" {
  value = aws_iam_role.github_ci.arn
}

output "ci_ssm_kms_key_arn" {
  value = aws_kms_key.ci.arn
}

output "snyk_token_ssm_parameter_name" {
  value = var.snyk_token_ssm_parameter_name
}
