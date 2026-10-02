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

variable "db_name" {
  type    = string
  default = "noteos"
}

variable "db_username" {
  type    = string
  default = "noteos"
}

variable "db_password_ssm_parameter_name" {
  type        = string
  description = "Existing SSM SecureString containing the RDS password. Create it before planning this stack."

  validation {
    condition     = startswith(var.db_password_ssm_parameter_name, "/")
    error_message = "Use an absolute SSM parameter path, such as /noteos/production/database/password."
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
  default     = "http://localhost:3050"
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
