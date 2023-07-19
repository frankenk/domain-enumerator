data "aws_caller_identity" "current" {}

data "aws_vpc" "default" {
  default = true
} 

data "aws_security_group" "selected" {
  vpc_id = data.aws_vpc.default.id

  filter {
    name   = "group-name"
    values = ["default"]
  }
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_s3_bucket" "s3_bucket_targets" { 
  bucket_prefix = "tf-domain-enumerator-"
  force_destroy = true #change to variable and add on destroy.
}

resource "aws_s3_bucket_public_access_block" "block_access_policy" {
  bucket = aws_s3_bucket.s3_bucket_targets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

########## ECS cluster creation ##########

module "ecs_cluster"{
  source = "./modules/tool_containers/"
  container_definitions = jsonencode([
    {
      name           = "subfinder"
      image          = "projectdiscovery/subfinder"
      essential      = true
      logConfiguration = {
        logDriver         = "awslogs"
        options           = {
          "awslogs-create-group"    = "true"
          "awslogs-group"           = "/ecs/${var.cluster_name}"
          "awslogs-region"          = var.aws_region
          "awslogs-stream-prefix"   = "subfinder"
        }
      }
    }
    // Add more container definitions as needed
  ])
}

########## Lambda creation ##########

resource "aws_iam_policy" "invoke_policy" {
  path        = "/"
  description = "IAM policy for invoking alerting lambda"
  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
        {
          "Effect": "Allow",
          "Action": "lambda:InvokeFunction",
          "Resource": "${module.alerting_lambda.lambda_arn}*"
        }
    ]
  })
}


module "alerting_lambda" {
  exclude_scheduler_creation = true
  source      = "./modules/scheduler_payload_lamba/"
  lambda_name = "alerting_lambda"
  account_id  = data.aws_caller_identity.current.account_id
  lambda_root = "lambdas/alerting_lambda.py"
  layers = [module.lambda_layer.lambda_layer_arn]
  lambda_environment_variables = {
    DC_WEBHOOK_URL = var.dc_webhook_url
  }
  policy_arns = [
    module.compare_lambda.default_iam_policy_arn
  ]   
}

module "compare_lambda" {
  source      = "./modules/scheduler_payload_lamba/"
  lambda_name = "compare_lambda"
  account_id  = data.aws_caller_identity.current.account_id
  lambda_root = "lambdas/compare_lambda.py"
  layers = [module.lambda_layer.lambda_layer_arn]
  lambda_environment_variables = {
    DATA_S3 = aws_s3_bucket.s3_bucket_targets.bucket_domain_name
  }
  scheduler_name = "compare_lambda_scheduler"
  # Every 9 hours. Just schedule, expect check_if_alive to be finished in 30 mins.
  cron_expression = "cron(0 */9 ? * * *)"   
  policy_arns = [
    module.compare_lambda.default_iam_policy_arn, # Adding because no clue how to have list as null
    aws_iam_policy.invoke_policy.arn
  ]    
}

module "check_if_alive_lambda" {
  source      = "./modules/scheduler_payload_lamba/"
  lambda_name = "check_if_alive_lambda"
  account_id  = data.aws_caller_identity.current.account_id
  lambda_root = "lambdas/check_if_alive_lambda.py"
  timeout     = 480
  layers = [module.lambda_layer.lambda_layer_arn]
  lambda_environment_variables = {
    DATA_S3 = aws_s3_bucket.s3_bucket_targets.bucket_domain_name
  }
  scheduler_name = "check_if_alive_lambda_scheduler"
  # Every 8,5 hours. Just schedule, expect runtask to be finished in 30 mins.
  cron_expression = "cron(30 */8 ? * * *)" 
  policy_arns = [
    module.compare_lambda.default_iam_policy_arn
  ]    
}

module "ecs_runtask_lambda" {
  source      = "./modules/scheduler_payload_lamba/"
  lambda_name = "ecs_runtask_lambda"
  account_id  = data.aws_caller_identity.current.account_id
  lambda_root = "lambdas/ecs_runtask_lambda.py"
  timeout     = 480
  layers = [module.lambda_layer.lambda_layer_arn]
  lambda_environment_variables = {
    ECS_TASK_DEFINITION_ARN = module.ecs_cluster.task_definition_arn,
    DEFAULT_SECURITY_GROUP = data.aws_security_group.selected.id,
    DEFAULT_SUBNET = data.aws_subnets.default.ids[0],
    DATA_S3 = aws_s3_bucket.s3_bucket_targets.bucket_domain_name
  }
  scheduler_name = "ecs_runtask_lambda_scheduler"
  cron_expression = "cron(0 */8 ? * * *)" # Every 8 hours, requires testing
  json_payload = jsonencode({ # Add more commands
    "tool_names":["subfinder"],
    "tool_commands":["-oJ -silent -d"]
  })
  policy_arns = [
    module.compare_lambda.default_iam_policy_arn
  ]     
}

module "lambda_layer" {
  source      = "./modules/layer_creator/"
  layer_name = "tf_lambda_layers"

}
