import sys
import os
import logging
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Job Arguments ----------
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'DELTA_PATH',            # Shared root path
    'DELTA_TABLES',          # Comma-separated table names
    'REDSHIFT_URL',
    'REDSHIFT_USER',
    'REDSHIFT_PASSWORD'
])

DELTA_PATH = args['DELTA_PATH'].rstrip('/')
DELTA_TABLES = args['DELTA_TABLES'].split(',')

REDSHIFT_URL = args['REDSHIFT_URL']
REDSHIFT_USER = args['REDSHIFT_USER']
REDSHIFT_PASSWORD = args['REDSHIFT_PASSWORD']
REDSHIFT_DRIVER = "com.amazon.redshift.jdbc.Driver"

# ---------- Spark Initialization ----------
sc = SparkContext()
glueContext = GlueContext(sc)
spark = (
    glueContext.spark_session.builder
    .appName(args['JOB_NAME'])
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .getOrCreate()
)
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

# ---------- Main Execution ----------
for table in DELTA_TABLES:
    try:
        delta_table_path = f"{DELTA_PATH}/{table}"
        logger.info(f"📥 Reading Delta table: {table} from {delta_table_path}")
        df = spark.read.format("delta").load(delta_table_path)

        # ✅ Cast Boolean columns to Integer if needed (Redshift doesn't support BIT/BOOLEAN)
        for column_name, dtype in df.dtypes:
            if dtype == 'boolean':
                logger.info(f"⚠️ Casting boolean column '{column_name}' to integer for Redshift compatibility.")
                df = df.withColumn(column_name, when(col(column_name) == True, 1).otherwise(0))

        logger.info(f"📤 Writing to Redshift table: {table}")
        df.write.format("jdbc") \
            .option("url", REDSHIFT_URL) \
            .option("dbtable", table) \
            .option("user", REDSHIFT_USER) \
            .option("password", REDSHIFT_PASSWORD) \
            .option("driver", REDSHIFT_DRIVER) \
            .mode("overwrite") \
            .save()

        logger.info(f"✅ Table {table} written to Redshift.")

    except Exception as e:
        logger.error(f"❌ Failed processing table {table}: {e}")

logger.info("🎯 Glue job completed.")
job.commit()
