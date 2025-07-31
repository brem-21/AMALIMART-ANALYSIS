# AMALIMART-ANALYSIS
This project aims to design and implement the first version of this analytics platform with production-grade data engineering practices.

#  Data Lake Ingestion and Transformation Orchestration with AWS Step Functions

## Overview

This project orchestrates a complete data ingestion and transformation pipeline using **AWS Step Functions** to manage Glue jobs, Lambda functions, and SNS notifications. The flow moves data across environments and layers, from external systems into a structured data lakehouse architecture, enabling scalable, reliable, and observable data operations.

---

##  Workflow Summary
To ingest data from an external app database, process and transform it through multiple stages (bronze → silver → gold), and finally make it available for analytics, visualization, and storage in Redshift and an internal database — with notifications at key points.
![architecture diagram](<Project Assets/ARCHITECTURE.png>)

### Key Pipeline Stages
*App Database (External Source)*

- Original source of raw transactional data (e.g., orders, users, products).

*Landing Database*

- Temporary RDS used to ingest and stage the raw data.

*Bronze Lakehouse*

- Stores raw ingested data in S3 in Delta format.

- Used for backup, auditing, or reprocessing.

*Silver Datalakehouse*

- Stores cleaned and enriched data.

- Business logic, deduplication, and joins are applied here.

*Gold Datalakehouse*

- Contains high-quality, aggregated, and ready-for-reporting data.

- Optimized for downstream analytics.

*Gold Database & Redshift*

`Internal RDS`: Receives part of the gold-level data for operational use.

`Redshift`: For high-performance analytical queries and BI tools.

*Glue Jobs*

- Handle all ETL transformations between stages (Bronze → Silver → Gold).

- Load data to internal RDS and Redshift.

*Notifications (SNS)*

- Triggered after key ingestion and loading steps to inform stakeholders or systems of progress or issues.

*Visualization*

- Final data can be used for dashboards and reporting (e.g., via QuickSight, Tableau).

 ## Why This is Valuable
- Ensures data quality and lineage across all layers.

- Enables scalable analytics with Delta + Redshift.

- Automates the pipeline with AWS Glue and SNS notifications.

- Supports both operational and analytical workloads.

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

