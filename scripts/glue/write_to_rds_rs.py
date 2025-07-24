import sys
import os
import logging
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Glue Job Args ----------
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'DELTA_PATH',
    'DELTA_TABLES',
    'RDS_URL',
    'RDS_USER',
    'RDS_PASSWORD',
    'REDSHIFT_URL',
    'REDSHIFT_USER',
    'REDSHIFT_PASSWORD'
])

BASE_PATH = args['DELTA_PATH'].rstrip('/')
TABLES = [t.strip() for t in args['DELTA_TABLES'].split(',')]

# ---------- JDBC Config ----------
rds_props = {
    "url": args["RDS_URL"],
    "user": args["RDS_USER"],
    "password": args["RDS_PASSWORD"],
    "driver": "com.mysql.cj.jdbc.Driver"  # Use org.postgresql.Driver for PostgreSQL
}

redshift_props = {
    "url": args["REDSHIFT_URL"],
    "user": args["REDSHIFT_USER"],
    "password": args["REDSHIFT_PASSWORD"],
    "driver": "com.amazon.redshift.jdbc.Driver"
}

# ---------- Initialize Spark ----------
sc = SparkContext()
glueContext = GlueContext(sc)
spark = (
    glueContext.spark_session.builder
    .appName(args['JOB_NAME'])
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.hadoop.fs.s3a.aws.credentials.provider", "com.amazonaws.auth.DefaultAWSCredentialsProviderChain")
    .getOrCreate()
)

job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# ---------- Process Each Table ----------
for table_name in TABLES:
    delta_path = f"{BASE_PATH}/{table_name}"
    try:
        logger.info(f"📥 Reading Delta table: {delta_path}")
        df = spark.read.format("delta").load(delta_path)

        logger.info(f"📤 Writing {table_name} to RDS...")
        df.write.format("jdbc") \
            .option("url", rds_props["url"]) \
            .option("dbtable", table_name) \
            .option("user", rds_props["user"]) \
            .option("password", rds_props["password"]) \
            .option("driver", rds_props["driver"]) \
            .mode("overwrite") \
            .save()

        logger.info(f"📤 Writing {table_name} to Redshift...")
        df.write.format("jdbc") \
            .option("url", redshift_props["url"]) \
            .option("dbtable", table_name) \
            .option("user", redshift_props["user"]) \
            .option("password", redshift_props["password"]) \
            .option("driver", redshift_props["driver"]) \
            .mode("overwrite") \
            .save()

        logger.info(f"✅ Completed: {table_name}")

    except Exception as e:
        logger.error(f"❌ Failed to process {table_name}: {e}")
        continue

# ---------- Finalize ----------
job.commit()
logger.info("🎯 Glue job finished successfully.")
