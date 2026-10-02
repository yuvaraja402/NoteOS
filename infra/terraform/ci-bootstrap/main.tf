data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  parameter_arn = "arn:${data.aws_partition.current.partition}:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.snyk_token_ssm_parameter_name}"
  oidc_arn      = var.existing_oidc_provider_arn != "" ? var.existing_oidc_provider_arn : aws_iam_openid_connect_provider.github[0].arn
}

resource "aws_iam_openid_connect_provider" "github" {
  count           = var.existing_oidc_provider_arn == "" ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_kms_key" "ci" {
  description             = "NotesOS CI SSM secrets"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "ci" {
  name          = "alias/${var.name}-ssm"
  target_key_id = aws_kms_key.ci.key_id
}

resource "aws_iam_role" "github_ci" {
  name                 = var.name
  max_session_duration = 3600
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = local.oidc_arn }
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:ref:refs/heads/${var.github_branch}"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "ci_ssm" {
  name = "read-snyk-token"
  role = aws_iam_role.github_ci.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "ssm:GetParameter"
        Resource = local.parameter_arn
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = aws_kms_key.ci.arn
        Condition = {
          StringEquals = {
            "kms:ViaService"                      = "ssm.${var.region}.amazonaws.com"
            "kms:EncryptionContext:PARAMETER_ARN" = local.parameter_arn
          }
        }
      }
    ]
  })
}
