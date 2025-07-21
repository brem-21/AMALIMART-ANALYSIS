resource "aws_redshift_cluster" "amalimart" {
  cluster_identifier = var.redshift_cluster
  database_name = var.redshift_db
  master_username = var.redshift_user
  master_password = var.redshift_password
  node_type = "ra3.large"
  cluster_type = "single-node"

  manage_master_password = true
}