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