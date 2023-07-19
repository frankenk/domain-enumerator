variable "cluster_name" {
  description = "Defines ECS cluster name"
  type        = string
  default = "domain_enumerator"
}

variable "task_definition_name" {
  description = "Defines public docker image that ECS task will use"
  type    = string
  default = "domain_enumerator"
}

variable "container_definitions" {
  description = "Defines container definitions for the ECS task"
  type        = string
}
