
resource "aws_ecs_task_definition" "ecs_tooling_taskdefinition" {
  family                   = "tf_${var.task_definition_name}"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  network_mode             = "awsvpc"
  execution_role_arn       = aws_iam_role.ecs_tooling_role.arn

  container_definitions = var.container_definitions

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
}


resource "aws_ecs_cluster" "tooling_cluster" {
  name = "tf_${var.cluster_name}"
}

resource "aws_iam_role" "ecs_tooling_role" {
  assume_role_policy = <<EOF
{
    "Version": "2008-10-17",
    "Statement": [
        {
            "Sid": "",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF
}

resource "aws_iam_policy" "ecs_tooling_policy" {
  path        = "/"
  description = "IAM policy for logging from a lambda"
  policy      = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:CreateLogGroup"
            ],
            "Resource": "*"
        }
    ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "shodanmore_ecs_tooling" {
  role       = aws_iam_role.ecs_tooling_role.name
  policy_arn = aws_iam_policy.ecs_tooling_policy.arn
}