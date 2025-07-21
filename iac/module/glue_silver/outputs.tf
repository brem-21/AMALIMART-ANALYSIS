output "glue_job_name" {
  description = "Name of the Created AWS Glue job"
  value = aws_glue_job.silver_data.name
}

output "glue_job_arn" {
  description = "ARN of the created AWS Glue job"
  value = aws_glue_job.silver_data.arn
}