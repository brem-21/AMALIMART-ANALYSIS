import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession


def initialize_glue_context(job_name):
    """Initialize and return Glue context with Delta Lake configurations"""
    args = getResolvedOptions(sys.argv, [
        "JOB_NAME",
        "RDS_HOST",
        "RDS_PORT",
        "RDS_DB_NAME",
        "RDS_USERNAME",
        "RDS_PASSWORD",
        "S3_OUTPUT_BUCKET",
        "DB_TABLES"
    ])

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

    spark.conf.set("spark.sql.adaptive.enabled", "true")
    spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
    spark.conf.set("spark.sql.adaptive.skewJoin.enabled", "true")
    spark.conf.set("spark.sql.cbo.enabled", "true")
    spark.conf.set("spark.sql.statistics.histogram.enabled", "true")

    job = Job(glue_context)
    job.init(job_name, args)
    return glue_context, spark, args, job


def get_jdbc_url(args):
    return f"jdbc:mysql://{args['RDS_HOST']}:{args['RDS_PORT']}/{args['RDS_DB_NAME']}"


def extract_table(glue_context, jdbc_url, table_name, conn_props):
    print(f"Extracting table: {table_name}")
    return glue_context.read.format("jdbc") \
        .option("url", jdbc_url) \
        .option("dbtable", table_name) \
        .option("user", conn_props["user"]) \
        .option("password", conn_props["password"]) \
        .option("driver", conn_props["driver"]) \
        .load()


def write_to_s3_delta(df, bucket, db_name, table_name):
    output_path = f"s3://{bucket}/{db_name}/{table_name}/"
    print(f"Writing {table_name} to {output_path} as Delta format...")
    df.write.format("delta").mode("overwrite").save(output_path)


def main():
    glue_context, spark, args, job = initialize_glue_context(args["JOB_NAME"])

    jdbc_url = get_jdbc_url(args)
    conn_props = {
        "user": args["RDS_USERNAME"],
        "password": args["RDS_PASSWORD"],
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    tables = args["DB_TABLES"].split(",")
    for table in tables:
        df = extract_table(glue_context, jdbc_url, table, conn_props)
        write_to_s3_delta(df, args["S3_OUTPUT_BUCKET"], args["RDS_DB_NAME"], table)

    job.commit()


if __name__ == "__main__":
    main()
