output "glue_job_name" {
  description = "Name of the Created AWS Glue job"
  value = aws_glue_job.mysql_to_s3_delta.name
}

output "glue_job_arn" {
  description = "ARN of the created AWS Glue job"
  value = aws_glue_job.mysql_to_s3_delta.arn
}