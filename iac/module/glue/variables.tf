variable "glue_job_name" {
  description = "The name of the glue job for the extraction/ingestion from RDS Database"
}

variable "bucket_name" {
    type = string
    description = "Name of the S3 bucket used for BLOB Storage"
}

variable "script_path" {
  description = "Path to the Glue Script"
}

variable "SQL_SERVER_HOST" {
  description = "Host of the RDS instance"
}

variable "SQL_SERVER_PORT" {
  description = "RDS instance port for connectivity"
}

variable "SQL_SERVER_USER" {
  description = "Testing123"
}

variable "SQL_SERVER_PASSWORD" {
  description = "Password of the data source"
  sensitive = true
}

variable "SQL_SERVER_DATABASE" {
  description = "Name of the database from datasource"
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