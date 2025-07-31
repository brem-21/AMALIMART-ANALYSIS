import sys
import logging
import math
import pandas as pd
from sqlalchemy import create_engine
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql.functions import col, when

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Job Arguments ----------
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'DELTA_PATH',
    'DELTA_TABLES',
    'RDS_URL',
    'RDS_PORT',
    'RDS_SCHEMA',
    'RDS_USER',
    'RDS_PASSWORD'
])

DELTA_PATH = args['DELTA_PATH'].rstrip('/')
DELTA_TABLES = [t.strip() for t in args['DELTA_TABLES'].split(',') if t.strip()]

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

# ---------- SQLAlchemy Engine ----------
mysql_url = f"mysql+pymysql://{args['RDS_USER']}:{args['RDS_PASSWORD']}@{args['RDS_URL']}:{args['RDS_PORT']}/{args['RDS_SCHEMA']}"
engine = create_engine(mysql_url)

# ---------- Main Execution ----------
for table in DELTA_TABLES:
    try:
        logger.info(f"📥 Reading Delta table: {table}")
        df = spark.read.format("delta").load(f"{DELTA_PATH}/{table}")

        # Cast boolean to integer
        for col_name, dtype in df.dtypes:
            if dtype == 'boolean':
                df = df.withColumn(col_name, when(col(col_name), 1).otherwise(0))

        # Convert to Pandas (Spark -> Pandas)
        pandas_df = df.toPandas()

        if pandas_df.empty:
            logger.warning(f"⚠️ Skipping table {table}: no rows to insert.")
            continue

        logger.info(f"📤 Writing {len(pandas_df)} rows to MySQL table: {table}")
        # Write to MySQL and auto-create table
        pandas_df.to_sql(name=table, con=engine, if_exists='replace', index=False)

        logger.info(f"✅ Successfully inserted table: {table}")

    except Exception as e:
        logger.exception(f"❌ Failed to process table {table}: {e}")

# ---------- Job Completion ----------
logger.info("🏁 Glue job completed.")
job.commit()
