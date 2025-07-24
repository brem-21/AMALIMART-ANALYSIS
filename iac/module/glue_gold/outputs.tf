output "glue_job_name" {
  description = "Name of the Created AWS Glue job"
  value = aws_glue_job.gold_kpis.name
}

output "glue_job_arn" {
  description = "ARN of the created AWS Glue job"
  value = aws_glue_job.gold_kpis.arn
}