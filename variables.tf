variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "cluster_name" {
  description = "Defines ECS cluster name"
  type        = string
  default     = "domain_enumerator"
}

variable "dc_webhook_url" {
  description = "Defines Discord webhook URL"
  type        = string
}
