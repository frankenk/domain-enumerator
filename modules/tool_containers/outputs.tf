output "task_definition_arn" {
  description = "Outputs task definition ARN which will passed to ecs_runtask_lambda"
  value       = aws_ecs_task_definition.ecs_tooling_taskdefinition.arn
}