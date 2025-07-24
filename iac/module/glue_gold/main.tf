resource "aws_glue_job" "gold_kpis" {
  name     = var.gold_job_name
  role_arn = var.role_arn

  command {
    name            = "glueetl"
    script_location = var.gold_script_path
    python_version  = "3"
  }

  default_arguments = {
    "--JOB_NAME"                  = var.gold_job_name
    "--S3_OUTPUT_BUCKET"          = var.bucket_name
    "--DELTA_TABLES"              = var.tables
    "--enable-metrics"            = ""
    "--additional-python-modules" = "delta-spark==2.4.0,PyMySQL==1.1.1,jaydebeapi==1.2.3"
    "--TempDir"                   = "s3://${var.bucket_name}/glue/temp/"
    "--GOLD_PATH"               = "s3://${var.bucket_name}/KPIS/${var.db_name}/"
    "--SILVER_PATH"                = var.silver_location
  }

  glue_version        = "5.0"
  number_of_workers   = 2
  worker_type         = "G.1X"
  max_retries         = 0
  timeout             = 60
}
