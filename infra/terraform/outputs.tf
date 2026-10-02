output "web_repository_url" {
  value = aws_ecr_repository.web.repository_url
}

output "api_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "app_url" {
  value = "http://${aws_lb.main.dns_name}"
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "database_url_ssm_parameter" {
  value = aws_ssm_parameter.database_url.name
}
