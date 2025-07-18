import sys
from datetime import datetime
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import SparkSession
from pyspark.sql.functions import lit
from pyspark.sql.types import StructType, StructField, StringType, LongType
import pymysql

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
        .config("spark.jars.packages", "io.delta:delta-core_2.12:2.3.0")
        .getOrCreate()
    )
    job = Job(glue_context)
    return glue_context, spark, job

def truncate_rds_table(host, port, database, table, user, password):
    try:
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=user,
            password=password,
            database=database,
            connect_timeout=10
        )
        with conn.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {table}")
        conn.commit()
        print(f"Truncated table: {table}")
    except Exception as e:
        print(f"Error truncating {table}: {e}")
        raise
    finally:
        if conn:
            conn.close()

def create_delta_table(spark, df, base_path, table_name, partition_columns=None):
    delta_path = f"{base_path}/{table_name}"

    writer = df.write.format("delta").mode("overwrite")

    if partition_columns:
        writer = writer.partitionBy(*partition_columns)

    writer.save(delta_path)

    return delta_path

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

    now = datetime.utcnow()
    current_year = now.strftime("%Y")
    current_month = now.strftime("%b")
    week_number = ((now.day - 1) // 7) + 1

    tables = args["DB_TABLES"].split(",")
    s3_bucket = args["S3_OUTPUT_BUCKET"]
    db_name = args["RDS_DB_NAME"]

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
        print(f" Processing table: {table}")
        try:
            df = glue_context.read.format("jdbc") \
                .option("url", jdbc_url) \
                .option("dbtable", table) \
                .option("user", conn_props["user"]) \
                .option("password", conn_props["password"]) \
                .option("driver", conn_props["driver"]) \
                .load()

            df = df.withColumn("ingestion_year", lit(current_year)) \
                   .withColumn("ingestion_month", lit(current_month)) \
                   .withColumn("ingestion_week", lit(week_number))

            base_output_path = f"s3://{s3_bucket}/Raw-Data/{db_name}"
            delta_path = create_delta_table(
                spark,
                df,
                base_output_path,
                table,
                partition_columns=["ingestion_year", "ingestion_month", "ingestion_week"]
            )

            row_count = df.count()
            print(f"{row_count} records written to Delta table: {table} at {delta_path}")

            truncate_rds_table(
                args['RDS_HOST'],
                args['RDS_PORT'],
                args['RDS_DB_NAME'],
                table,
                args['RDS_USERNAME'],
                args['RDS_PASSWORD']
            )

            audit_df = spark.createDataFrame([(
                table,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                current_year,
                current_month,
                week_number,
                row_count,
                delta_path
            )], schema=audit_schema)

            audit_table_path = f"s3://{s3_bucket}/Raw-Data/audit_logs/"
            audit_df.write.format("delta").mode("append").save(audit_table_path)

        except Exception as e:
            print(f"Error processing {table}: {e}")
            continue

    job.commit()

if __name__ == "__main__":
    main()
