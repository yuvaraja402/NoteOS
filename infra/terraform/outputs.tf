output "web_repository_url" {
  value = aws_ecr_repository.web.repository_url
}

output "api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "app_url" {
  value = var.allowed_origin
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "notes_table_name" {
  value = aws_dynamodb_table.notes.name
}

output "redis_endpoint" {
  value = aws_elasticache_replication_group.notes.primary_endpoint_address
}

output "runtime_ssm_parameters" {
  value = {
    redis_auth_token    = var.redis_auth_token_ssm_parameter_name
    session_signing_key = var.session_signing_key_ssm_parameter_name
  }
}
