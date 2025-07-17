import sys
from datetime import datetime
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, LongType, TimestampType
import jaydebeapi  # Added import for truncation


def initialize_glue_context(job_name):
    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = (
        SparkSession.builder.appName(job_name)
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.hadoop.fs.s3a.committer.name", "directory")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.marksuccessfuljobs", "false")
        .getOrCreate()
    )
    job = Job(glue_context)
    return glue_context, spark, job


def truncate_rds_table(jdbc_url, table, conn_props, driver_path="/tmp/mysql-connector-java-8.0.28.jar"):
    """Truncate MySQL table using direct JDBC connection"""
    try:
        conn = jaydebeapi.connect(
            "com.mysql.cj.jdbc.Driver",
            jdbc_url,
            [conn_props["user"], conn_props["password"]],
            driver_path
        )
        curs = conn.cursor()
        curs.execute(f"TRUNCATE TABLE {table}")
        conn.commit()
        print(f"Successfully truncated source table: {table}")
    except Exception as e:
        print(f"Error truncating {table}: {str(e)}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()


def main():
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'RDS_HOST',
        'RDS_PORT',
        'RDS_DB_NAME',
        'RDS_USERNAME',
        'RDS_PASSWORD',
        'S3_OUTPUT_BUCKET',
        'DB_TABLES'
    ])

    glue_context, spark, job = initialize_glue_context(args['JOB_NAME'])
    job.init(args['JOB_NAME'], args)

    jdbc_url = f"jdbc:mysql://{args['RDS_HOST']}:{args['RDS_PORT']}/{args['RDS_DB_NAME']}"
    conn_props = {
        "user": args['RDS_USERNAME'],
        "password": args['RDS_PASSWORD'],
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    # Current time → formatted as 2024/Jan/week1
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%b")  # Jan, Feb, Mar...
    week_number = ((now.day - 1) // 7) + 1
    folder_partition = f"{year}/{month}/week{week_number}"

    tables = args["DB_TABLES"].split(",")
    s3_bucket = args["S3_OUTPUT_BUCKET"]
    db_name = args["RDS_DB_NAME"]

    # Define schema for audit logs
    audit_schema = StructType([
        StructField("table_name", StringType()),
        StructField("ingestion_time", StringType()),
        StructField("year", StringType()),
        StructField("month", StringType()),
        StructField("week_number", LongType()),
        StructField("record_count", LongType()),
        StructField("s3_path", StringType())
    ])

    for table in tables:
        print(f"Extracting table: {table}")
        try:
            df = glue_context.read.format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", table) \
                .option("user", conn_props["user"]) \
                .option("password", conn_props["password"]) \
                .option("driver", conn_props["driver"]) \
                .load()

            output_path = f"s3://{s3_bucket}/Raw-Data/{db_name}/{table}/{folder_partition}/"
            print(f"Writing to: {output_path}")

            df.write.format("delta").mode("overwrite").save(output_path)
            
            row_count = df.count()
            print(f"Table {table} has {row_count} records for week {week_number}")
            
            # TRUNCATE SOURCE TABLE AFTER SUCCESSFUL LOAD
            truncate_rds_table(jdbc_url, table, conn_props)
            
            # Create audit record
            audit_data = [(
                table,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                year,
                month,
                week_number,
                row_count,
                output_path
            )]
            
            audit_df = spark.createDataFrame(audit_data, schema=audit_schema)
            
            audit_table_path = f"s3://{s3_bucket}/Raw-Data/audit_logs/"
            audit_df.write.format("delta").mode("append").save(audit_table_path)

        except Exception as e:
            print(f"Error processing table {table}: {str(e)}")
            continue

    job.commit()


if __name__ == "__main__":
    main()
    