module "aws_s3_bucket" {
  source = "./module/s3"
  bucket_name = var.bucket_name
  access_key_id = var.access_key_id
  secret_access_key = var.secret_access_key
  region = var.region
}