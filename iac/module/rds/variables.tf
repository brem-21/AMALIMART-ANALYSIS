variable "allocated_storage" {
  description = "Storage of the instance"
}

variable "db_name" {
  description = "Database Name"
}

variable "engine" {
  description = "Engine type (PostgreSQL, MySQL)"
}

variable "engine_version" {
  description = "Version of the database engine"
}

variable "instance_class" {
  description = "Instance type the database will running on"
}

variable "username" {
  description = "database User"
}

variable "password" {
  description = "password for the database user(Authentication)"
  sensitive = true
}

variable "parameter_group_name" {
  description = "Parameter group name"
}

