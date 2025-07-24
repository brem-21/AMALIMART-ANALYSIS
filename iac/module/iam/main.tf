resource "aws_iam_role" "glue_role" {
  name = "glue-mysql-delta-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "glue.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}
resource "aws_iam_role_policy" "glue_policy" {
  name = "glue-mysql-delta-policy"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      # S3 access for Delta Lake and Redshift temp dir
      {
        Effect   = "Allow",
        Action   = ["s3:*"],
        Resource = [
          "arn:aws:s3:::${var.bucket_name}",
          "arn:aws:s3:::${var.bucket_name}/*"
        ]
      },
      # RDS describe only (optional)
      {
        Effect   = "Allow",
        Action   = ["rds:DescribeDBInstances"],
        Resource = "*"
      },
      # Logs, EC2, CloudWatch (for networking and metrics)
      {
        Effect   = "Allow",
        Action   = [
          "logs:*",
          "ec2:Describe*",
          "cloudwatch:PutMetricData"
        ],
        Resource = "*"
      },
      # Redshift access
      {
        Effect = "Allow",
        Action = [
          "redshift:DescribeClusters",
          "redshift:DescribeTable",
          "redshift:DescribeSchemas",
          "redshift:GetClusterCredentials",
          "redshift:ListSchemas",
          "redshift:ListTables",
          "redshift:GetTableData",
          "redshift:DescribeLoggingStatus",
          "redshift:CreateClusterUser",
          "redshift:CreateCluster",
          "redshift:ModifyCluster",
          "redshift:DeleteCluster",
          "redshift:PauseCluster",
          "redshift:ResumeCluster",
          "redshift-data:*"
        ],
        Resource = "*"
      }
    ]
  })
}
