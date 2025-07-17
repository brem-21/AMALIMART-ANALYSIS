resource "aws_glue_job" "mysql_to_s3_delta" {
  name     = var.glue_job_name
  role_arn = var.role_arn

  command {
    name            = "glueetl"
    script_location = var.script_path
    python_version  = "3"
  }

  default_arguments = {
    "--JOB_NAME"                  = var.glue_job_name
    "--RDS_HOST"                  = var.SQL_SERVER_HOST
    "--RDS_PORT"                  = var.SQL_SERVER_PORT
    "--RDS_DB_NAME"               = var.SQL_SERVER_DATABASE
    "--RDS_USERNAME"              = var.SQL_SERVER_USER
    "--RDS_PASSWORD"              = var.SQL_SERVER_PASSWORD
    "--S3_OUTPUT_BUCKET"          = var.bucket_name
    "--DB_TABLES"                 = var.tables
    "--enable-metrics"            = ""
    "--additional-python-modules" = "delta-spark==2.4.0,mysql-connector-python==8.0.33"
    "--TempDir"                   = "s3://${var.bucket_name}/glue/temp/"
  }

  glue_version        = "5.0"
  number_of_workers   = 2
  worker_type         = "G.1X"
  max_retries         = 0
  timeout             = 60
}
