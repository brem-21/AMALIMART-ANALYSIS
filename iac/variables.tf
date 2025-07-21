variable "region" {
  type        = string
  description = "Name of the region in AWS"
}

variable "access_key_id" {
  type        = string
  description = "Access Key ID of IAM USER"
}

variable "secret_access_key" {
  type        = string
  description = "Secret Access Key of IAM USER"
}

variable "bucket_name" {
  type        = string
  description = "Name of the S3 bucket used for BLOB Storage"
}

variable "allocated_storage" {
  description = "Storage of the instance"
}

variable "db_name" {
  description = "Database Name"
}

variable "engine" {
  description = "Engine type (PostgreSQL, MySQL)"
}

variable "engine_version" {
  description = "Version of the database engine"
}

variable "instance_class" {
  description = "Instance type the database will running on"
}

variable "username" {
  description = "database User"
}

variable "password" {
  description = "password for the database user(Authentication)"
  sensitive   = true
}

variable "parameter_group_name" {
  description = "Parameter group name"
}

variable "glue_job_name" {
  description = "The name of the glue job for the extraction/ingestion from RDS Database"
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
  sensitive   = true
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

variable "silver_path" {
  description = "Path to the silver Glue Script"
}

variable "delta_path" {
  description = "Delta Lakehouse path"
}

variable "silver_job_name" {
  description = "Name of the silver tranformation Job"
}

variable "redshift_cluster" {
  description = "Cluster identifier"
}

variable "redshift_db" {
  description = "Database of the datawarehouse"
}

variable "redshift_user" {
  description = "user of the database"
}

variable "redshift_password" {
  description = "Password for authentication"
  sensitive   = true
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