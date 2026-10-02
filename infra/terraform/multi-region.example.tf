# This file is an example only. Do not rename it to `.tf` until the current
# single-region stack is extracted into `modules/regional-stack`.
#
# The intended North America, Europe, and Asia rollout is two AWS regions per
# continent. Each region should run the same three-tier stack: ALB, ECS/Fargate,
# DynamoDB, ElastiCache, ECR, SSM, KMS, and CloudWatch.
#
# provider "aws" {
#   alias  = "north_america_east"
#   region = "ca-central-1"
# }
#
# provider "aws" {
#   alias  = "north_america_west"
#   region = "us-west-2"
# }
#
# provider "aws" {
#   alias  = "europe_west"
#   region = "eu-west-1"
# }
#
# provider "aws" {
#   alias  = "europe_central"
#   region = "eu-central-1"
# }
#
# provider "aws" {
#   alias  = "asia_south"
#   region = "ap-south-1"
# }
#
# provider "aws" {
#   alias  = "asia_southeast"
#   region = "ap-southeast-1"
# }
#
# module "north_america_east" {
#   source = "./modules/regional-stack"
#   providers = {
#     aws = aws.north_america_east
#   }
#   region       = "ca-central-1"
#   project_name = "noteos-na-east"
# }
#
# module "north_america_west" {
#   source = "./modules/regional-stack"
#   providers = {
#     aws = aws.north_america_west
#   }
#   region       = "us-west-2"
#   project_name = "noteos-na-west"
# }
#
# Repeat the module for Europe and Asia, then add Route 53 latency records or
# AWS Global Accelerator in a separate global stack.
