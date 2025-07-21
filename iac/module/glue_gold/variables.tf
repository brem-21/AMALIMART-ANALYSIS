variable "bucket_name" {
    type = string
    description = "Name of the S3 bucket used for BLOB Storage"
}

variable "tables" {
  description = "Tables needed to be exported into s3"
}

variable "role_arn" {
  description = "IAM Role ARN for Glue job"
  type        = string
}

variable "requirements_path" {
  description = "Path to requirements.txt file for installations"
}

variable "silver_path" {
  description = "Path to the silver Glue Script"
}

variable "delta_path" {
  description = "Delta Lakehouse path"
}

variable "silver_job_name" {
  description = "Name of the silver tranformation Job"
}

variable "db_name" {
  description = "Database Name"
}

variable "gold_script_path" {
  description = "Script path of the gold transformation"
}

variable "gold_job_name" {
  description = "name of the glue job for the gold transformation"
}

variable "gold_delta" {
  description = "Gold delta path"
}