# AMALIMART-ANALYSIS
This project aims to design and implement the first version of this analytics platform with production-grade data engineering practices.

#  Data Lake Ingestion and Transformation Orchestration with AWS Step Functions

## Overview

This project orchestrates a complete data ingestion and transformation pipeline using **AWS Step Functions** to manage Glue jobs, Lambda functions, and SNS notifications. The flow moves data across environments and layers, from external systems into a structured data lakehouse architecture, enabling scalable, reliable, and observable data operations.

---

##  Workflow Summary

###  Step Function Flow:
![orchestration](<Project Assets/stepfunctions_graph.png>)

| Component              | Description                                          |
| ---------------------- | ---------------------------------------------------- |
| **AWS Glue**           | For running ETL jobs at each pipeline stage          |
| **Amazon SNS**         | To notify on success/failure events                  |
| **AWS Lambda**         | For pausing clusters (RDS & Redshift) after job runs |
| **Amazon S3**          | Stores Delta Lake (bronze, silver, gold)             |
| **Amazon Redshift**    | Final warehouse target for analytics                 |
| **AWS Step Functions** | Orchestration and state management of the pipeline   |


| Glue Job Name            | Purpose                                                |
| ------------------------ | ------------------------------------------------------ |
| `read_from_app_database` | Ingests data from an external RDS into an internal RDS |
| `ingestion_from_rds`     | Ingests from internal RDS to Delta Lake (Bronze)       |
| `silver_transformation`  | Cleans and transforms bronze data to silver layer      |
| `gold_transformation`    | Aggregates and curates silver data into gold layer     |
| `rds`                    | Loads silver layer data back into internal RDS         |
| `write_to_rds_rs`        | Loads gold layer data into Redshift                    |


### Benefits of This Design
`Modular and Scalable`: Each stage runs independently and can be retried or modified without impacting the full workflow.

`Failure Isolation and Alerting`: Any job failure ends the pipeline early and notifies the team via SNS, ensuring quick resolution.
    ![success](<Project Assets/image.png>)
    ![failure](<Project Assets/image copy.png>)

`Resource Cost Optimization`: Automatically pauses both Redshift and RDS clusters after job execution to reduce costs.

`Parallel Execution`: The two final loading steps (RDS + Redshift) run in parallel, improving throughput.

`Observability`: SNS messages after key stages provide visibility into pipeline progress.

`Cloud-Native & Serverless`: Fully managed using AWS-native services, no infrastructure to manage.

