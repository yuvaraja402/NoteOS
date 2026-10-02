variable "aws_deployment_enabled" {
  type        = bool
  description = "Manual bootstrap opt-in only. Keep false for validation, branches, and forks."
  default     = false
  nullable    = false

  validation {
    condition     = var.aws_deployment_enabled
    error_message = "AWS deployment is locked. Complete infra/DEPLOYMENT.md before explicitly enabling a reviewed bootstrap."
  }
}

variable "region" {
  type    = string
  default = "ca-central-1"
}

variable "github_repository" {
  type        = string
  description = "Repository allowed to assume the role, in OWNER/REPO format."

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "Use an OWNER/REPO repository name without wildcards."
  }
}

variable "github_branch" {
  type    = string
  default = "main"

  validation {
    condition     = !can(regex("[*?:]", var.github_branch)) && length(var.github_branch) > 0
    error_message = "Use an explicit branch name without IAM wildcard characters."
  }
}

variable "name" {
  type        = string
  description = "Unique name for this repository's CI role and KMS alias."
  default     = "noteos-ci"
}

variable "snyk_token_ssm_parameter_name" {
  type    = string
  default = "/noteos/ci/snyk-token"

  validation {
    condition     = startswith(var.snyk_token_ssm_parameter_name, "/")
    error_message = "Use an absolute SSM parameter path."
  }
}

variable "existing_oidc_provider_arn" {
  type        = string
  description = "Reuse the account's GitHub OIDC provider if it already exists."
  default     = ""
}
