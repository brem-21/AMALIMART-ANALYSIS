resource "aws_s3_bucket" "amalimart" {
  bucket = var.bucket_name

  tags = {
    Name = "amalimart"
    Environment="Dev"
  }
}