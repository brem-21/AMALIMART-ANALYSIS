import sys
from datetime import datetime
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import SparkSession


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

    for table in tables:
        print(f"Extracting table: {table}")
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

    job.commit()


if __name__ == "__main__":
    main()
