output "lambda_layer_arn" {
  description = "Outputs lambda layer arn"
  value       = aws_lambda_layer_version.layer_package.arn
}