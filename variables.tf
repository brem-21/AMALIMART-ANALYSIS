variable "region" {
  type = string
  description = "Name of the region in AWS"
}

variable "access_key_id" {
  type = string
  description = "Access Key ID of IAM USER"
}

variable "secret_access_key" {
    type = string
    description = "Secret Access Key of IAM USER"
}

variable "bucket_name" {
    type = string
    description = "Name of the S3 bucket used for BLOB Storage"
}