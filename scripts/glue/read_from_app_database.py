import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import SparkSession

def initialize_glue_context(job_name):
    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = SparkSession.builder.appName(job_name).getOrCreate()
    job = Job(glue_context)
    return glue_context, spark, job

def main():
    args = getResolvedOptions(sys.argv, [
        'JOB_NAME',
        'SOURCE_HOST',
        'SOURCE_PORT',
        'SOURCE_DB_NAME',
        'SOURCE_USERNAME',
        'SOURCE_PASSWORD',
        'TARGET_HOST',
        'TARGET_PORT',
        'TARGET_DB_NAME',
        'TARGET_USERNAME',
        'TARGET_PASSWORD',
        'DB_TABLES'
    ])

    glue_context, spark, job = initialize_glue_context(args['JOB_NAME'])
    job.init(args['JOB_NAME'], args)

    source_url = f"jdbc:mysql://{args['SOURCE_HOST']}:{args['SOURCE_PORT']}/{args['SOURCE_DB_NAME']}"
    target_url = f"jdbc:mysql://{args['TARGET_HOST']}:{args['TARGET_PORT']}/{args['TARGET_DB_NAME']}"

    tables = args["DB_TABLES"].split(",")

    for table in tables:
        table = table.strip()
        print(f"Reading from source table: {table}")
        try:
            # Read from source
            df = glue_context.read.format("jdbc") \
                .option("url", source_url) \
                .option("dbtable", table) \
                .option("user", args["SOURCE_USERNAME"]) \
                .option("password", args["SOURCE_PASSWORD"]) \
                .option("driver", "com.mysql.cj.jdbc.Driver") \
                .load()

            # Write to target (append mode)
            df.write.format("jdbc") \
                .option("url", target_url) \
                .option("dbtable", table) \
                .option("user", args["TARGET_USERNAME"]) \
                .option("password", args["TARGET_PASSWORD"]) \
                .option("driver", "com.mysql.cj.jdbc.Driver") \
                .mode("append") \
                .save()

            print(f"Copied table: {table}")
        except Exception as e:
            print(f"Failed to process table {table}: {e}")
            continue

    job.commit()
    print("All tables processed successfully.")

if __name__ == "__main__":
    main()
