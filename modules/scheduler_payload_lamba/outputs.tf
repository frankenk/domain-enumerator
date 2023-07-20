output "default_iam_policy_arn" {
  description = "Outputs default IAM policy arn"
  value       = aws_iam_policy.lambda_tooling_policy.arn
}

output "lambda_arn" {
  description = "Outputs lambda arn"
  value       = aws_lambda_function.lambda.arn
}