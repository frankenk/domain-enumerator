variable "account_id" {
  description = "Defines AWS Account ID"
  type        = number
}

variable "lambda_root" {
  description = "Defines source file of lambda"
  type        = string
}

variable "lambda_name" {
  description = "Defines name of the lambda"
  type        = string
}

variable "python_runtime" {
  description = "Defines python run time"
  type        = string
  default     = "python3.9"
}

variable "layers" {
  description = "Defines list of layer arns to be added"
  type        = list(string)
  default     = []
}

variable "timeout" {
  description = "Defines maximus time lambda will run before timeout"
  type        = number
  default     = 90
}

variable "lambda_environment_variables" {
  type        = map(string)
  description = "Defines environment variables for the Lambda function"
  default     = {}
}

variable "exclude_scheduler_creation" {
  description = "Ignore EventBridge scheduler creation for Lambda"
  type        = string
  default     = false
}

variable "scheduler_name" {
  description = "Defines EventBridge scheduler name"
  type        = string
  default     = null
}

variable "cron_expression" {
  description = "Defines when EventBridge schedule runs"
  type        = string
  default     = null
}

variable "json_payload" {
  description = "Defines json payload that will be sent to lambda"
  type        = string
  default     = null
}

variable "policy_arns" {
  description = "Defines list of IAM to be attached to main role"
  type        = list(string)
  default     = []
}