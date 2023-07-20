output "targets_bucket_name" {
  description = "S3 bucket name which will hold metadata and results"
  value       = aws_s3_bucket.s3_bucket_targets.bucket_domain_name
}
