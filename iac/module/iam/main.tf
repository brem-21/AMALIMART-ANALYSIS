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
      {
        Effect   = "Allow",
        Action   = ["s3:*"],
        Resource = [
          "arn:aws:s3:::${var.bucket_name}",
          "arn:aws:s3:::${var.bucket_name}/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = ["rds:DescribeDBInstances"],
        Resource = "*"
      },
      {
        Effect   = "Allow",
        Action   = [
          "logs:*",
          "ec2:Describe*",
          "cloudwatch:PutMetricData"
        ],
        Resource = "*"
      }
    ]
  })
}