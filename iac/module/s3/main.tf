provider "aws" {
  region = var.region
  access_key = var.access_key_id
  secret_key = var.secret_access_key
}

resource "aws_s3_bucket" "amalimart" {
  bucket = var.bucket_name

  tags = {
    Name = "amalimart"
    Environment="Dev"
  }
}