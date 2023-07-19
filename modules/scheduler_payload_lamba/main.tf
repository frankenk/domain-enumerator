########## Lambda creation ##########

data "archive_file" "lambda_archive" {
  type        = "zip"
  source_file = var.lambda_root
  output_path = "${path.module}/${var.lambda_name}.zip"
}

resource "aws_lambda_function" "lambda" {
  filename         = data.archive_file.lambda_archive.output_path
  function_name    = "tf_${var.lambda_name}"
  role             = aws_iam_role.lambda_tooling_role.arn
  handler          = "${var.lambda_name}.lambda_handler"
  runtime          = var.python_runtime
  source_code_hash = data.archive_file.lambda_archive.output_base64sha256
  layers = var.layers
  timeout = var.timeout
  dynamic "environment" {
    for_each = var.lambda_environment_variables != {} ? [var.lambda_environment_variables] : []
    content {
      variables = environment.value
    }
  }
}
resource "aws_iam_role" "lambda_tooling_role" {
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
        "Action": "sts:AssumeRole",
        "Principal": {
            "Service": "lambda.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
        }
    ]
    }
EOF
}

# Needs to be hardened
resource "aws_iam_policy" "lambda_tooling_policy" {
  path        = "/"
  description = "IAM policy for logging from a lambda"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Action" : [
          "s3:Get*",
          "s3:List*",
          "s3-object-lambda:Get*",
          "s3-object-lambda:List*"
        ],
        "Resource" : "*",
        "Effect" : "Allow"
      },
      {
        "Action" : [
          "ecs:RunTask",
          "ecs:DescribeTasks",
          "ecs:ListTasks",
          "ecs:DescribeTaskDefinition",
          "ecs:ListTaskDefinitions"
        ],
        "Resource" : "*",
        "Effect" : "Allow"
      },
      {
        "Action" : [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        "Resource" : "arn:aws:logs:*:*:*",
        "Effect" : "Allow"
      },
      {
        "Action" : [
          "ssm:GetParameterHistory",
          "ssm:GetParametersByPath",
          "ssm:GetParameters",
          "ssm:GetParameter",
          "ssm:DescribeParameters"
        ],
        "Resource" : "arn:aws:ssm:*:*:*",
        "Effect" : "Allow"
      },
      {
        "Action" : [
          "sns:Publish",
          "sns:ListTopics"
        ],
        "Resource" : "arn:aws:sns:*:*:*",
        "Effect" : "Allow"
      },
      {
        "Action" : [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage"
        ],
        "Resource" : "*",
        "Effect" : "Allow"
      },
      {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::${var.account_id}:role/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_role_attachment" {
  for_each   = { for idx, arn in var.policy_arns : idx => arn } # assigns each value to variables idx, arn and maps them creating key:value pairs to avoid dependency issues. 
  role       = aws_iam_role.lambda_tooling_role.name
  policy_arn = each.value
}

########## Scheduler creation ##########

resource "aws_scheduler_schedule" "sync_monitoring_eventbridge" {
  count = var.exclude_scheduler_creation ? 0 : 1
  name                         = "tf_${var.scheduler_name}"
  group_name                   = "default"
  #schedule_expression_timezone = " " # Default is UTC.
  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = var.cron_expression

  target {
    arn      = aws_lambda_function.lambda.arn
    role_arn = aws_iam_role.eventbridge_role[count.index].arn
    input    = var.json_payload
  }
}

resource "aws_iam_role" "eventbridge_role" {
  count = var.exclude_scheduler_creation ? 0 : 1
  assume_role_policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
        "Action": "sts:AssumeRole",
        "Principal": {
            "Service": "scheduler.amazonaws.com"
        },
        "Effect": "Allow",
        "Sid": ""
        }
    ]
    }
EOF
}

resource "aws_iam_policy" "schedulers_policy" {
  count = var.exclude_scheduler_creation ? 0 : 1
  path = "/"
  policy = jsonencode({
    "Version" : "2012-10-17",
    "Statement" : [
      {
        "Effect" : "Allow",
        "Action" : [
          "lambda:InvokeFunction"
        ],
        "Resource" : [
          "${aws_lambda_function.lambda.arn}*",
          "${aws_lambda_function.lambda.arn}"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attachment" {
  count = var.exclude_scheduler_creation ? 0 : 1
  role       = aws_iam_role.eventbridge_role[count.index].name
  policy_arn = aws_iam_policy.schedulers_policy[count.index].arn
}