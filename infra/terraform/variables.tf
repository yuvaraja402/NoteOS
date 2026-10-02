variable "project_name" {
  type    = string
  default = "noteos"
}

variable "region" {
  type    = string
  default = "ca-central-1"
}

variable "environment" {
  type        = string
  description = "Deployment environment name used by runtime guardrails."
  default     = "production"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production for Terraform-managed deployments."
  }
}

variable "redis_auth_token_ssm_parameter_name" {
  type        = string
  description = "Existing SSM SecureString containing the Redis AUTH token."

  validation {
    condition     = startswith(var.redis_auth_token_ssm_parameter_name, "/")
    error_message = "Use an absolute SSM parameter path."
  }
}

variable "session_signing_key_ssm_parameter_name" {
  type        = string
  description = "Existing SSM SecureString containing the anonymous-session HMAC key."

  validation {
    condition     = startswith(var.session_signing_key_ssm_parameter_name, "/")
    error_message = "Use an absolute SSM parameter path."
  }
}

variable "runtime_secrets_kms_key_arn" {
  type        = string
  description = "Customer-managed KMS key used to encrypt both runtime SSM secrets."
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "flush_idle_seconds" {
  type    = number
  default = 60

  validation {
    condition     = var.flush_idle_seconds >= 5 && var.flush_idle_seconds <= 300
    error_message = "The idle flush interval must be between 5 and 300 seconds."
  }
}

variable "flush_max_seconds" {
  type    = number
  default = 300

  validation {
    condition     = var.flush_max_seconds >= 300 && var.flush_max_seconds <= 3600
    error_message = "The maximum flush interval must be between 300 and 3600 seconds."
  }
}

variable "web_image" {
  type        = string
  description = "Full image URI for the NotesOS Next.js container."
}

variable "api_image" {
  type        = string
  description = "Full image URI for the NotesOS FastAPI container."
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "allowed_origin" {
  type        = string
  description = "Browser origin allowed to call the API."
  validation {
    condition     = can(regex("^https://[A-Za-z0-9.-]+(:[0-9]+)?$", var.allowed_origin))
    error_message = "Deployed anonymous sessions require an HTTPS origin without a path or trailing slash."
  }
}

variable "acm_certificate_arn" {
  type        = string
  description = "Issued ACM certificate in this region, covering the application hostnames."
}

variable "route53_zone_id" {
  type        = string
  description = "Optional Route 53 hosted zone ID for public DNS records."
  default     = ""
}

variable "app_domain_name" {
  type        = string
  description = "Optional application domain name for latency-based routing."
  default     = ""
}

variable "geo_domain_name" {
  type        = string
  description = "Optional application domain name for geolocation-based routing."
  default     = ""
}

variable "route53_continent_code" {
  type        = string
  description = "Continent code for geolocation routing, such as NA, EU, or AS."
  default     = "NA"
}
