module "aws_s3_bucket" {
  source = "./module/s3"
  bucket_name = var.bucket_name
  access_key_id = var.access_key_id
  secret_access_key = var.secret_access_key
  region = var.region
}

module "aws_db_instance" {
  source = "./module/rds"
  allocated_storage = var.allocated_storage
  db_name = var.db_name
  engine = var.engine
  engine_version = var.engine_version
  instance_class = var.instance_class
  username = var.username
  password = var.password
  parameter_group_name = var.parameter_group_name
}


module "glue_iam_role" {
  source      = "./module/iam"
  bucket_name = var.bucket_name
}

module "glue_job" {
  source          = "./module/glue"
  glue_job_name   = var.glue_job_name
  script_path     = var.script_path
  SQL_SERVER_HOST = var.SQL_SERVER_HOST
  SQL_SERVER_PORT = var.SQL_SERVER_PORT
  SQL_SERVER_USER = var.SQL_SERVER_USER
  SQL_SERVER_PASSWORD = var.SQL_SERVER_PASSWORD
  SQL_SERVER_DATABASE = var.SQL_SERVER_DATABASE
  tables           = var.tables
  bucket_name = var.bucket_name
  role_arn         = var.role_arn  
}


