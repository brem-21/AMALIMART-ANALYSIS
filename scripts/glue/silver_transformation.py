import sys
import os
import logging
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, year, month, dayofmonth

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Job Params ----------
args = getResolvedOptions(sys.argv, ['JOB_NAME'])
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

# ---------- Config ----------
BASE_PATH = os.environ.get("DELTA_LAKE_BASE", "s3://your-bucket/delta")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "s3://your-bucket/silver")

TABLES = [
    "order_items", "orders", "product_variants", "user_audit", "support_messages",
    "wishlist_items", "products", "cities", "business_representatives", "cart_items",
    "stores", "payments", "order_status_history", "discounts", "product_tags",
    "returns", "carts", "messages", "wishlists", "reviews", "shipping_info",
    "businesses", "tags", "vendor_applications", "support_tickets", "users",
    "address", "categories", "product_images"
]

# ---------- Load Tables ----------
logger.info("📦 Loading Delta Tables...")
delta_tables = {}
for table in TABLES:
    try:
        df = spark.read.format("delta").load(f"{BASE_PATH}/{table}")
        delta_tables[table] = df
        logger.info(f"✅ Loaded: {table}")
    except Exception as e:
        logger.error(f"❌ Failed loading {table}: {e}")

# ---------- Transform: Products ----------
products = delta_tables["products"]
categories = delta_tables["categories"]
prod_var = delta_tables["product_variants"]
prod_img = delta_tables["product_images"]
reviews = delta_tables["reviews"]

product_silver = products.alias("p") \
    .join(categories.alias("c"), col("p.id") == col("c.id"), "left") \
    .join(prod_var.alias("v"), col("p.id") == col("v.product_id"), "left") \
    .join(prod_img.alias("img"), col("p.id") == col("img.product_id"), "left") \
    .join(reviews.alias("r"), col("p.id") == col("r.product_id"), "left") \
    .select(
        col("p.id").alias("product_id"), col("p.name").alias("product_name"),
        col("p.description").alias("product_description"), col("p.sku").alias("product_sku"),
        col("p.price").alias("product_price"), col("p.stock_quantity").alias("product_stock_quantity"),
        col("p.weight").alias("product_weight"), col("p.status").alias("product_status"),
        col("p.vendor_id").alias("product_vendor_id"), col("p.low_stock_threshold").alias("product_low_stock_threshold"),
        col("p.min_order_quantity").alias("product_min_order_quantity"), col("p.average_rating").alias("product_average_rating"),
        col("p.thumbnail_url").alias("product_thumbnail_url"), col("p.image_urls").alias("product_image_urls"),
        col("p.is_active").alias("product_is_active"), col("p.created_at").alias("product_created_at"),
        col("p.updated_at").alias("product_updated_at"), col("c.id").alias("category_id"),
        col("c.name").alias("category_name"), col("v.id").alias("variant_id"),
        col("v.variant_key").alias("variant_key"), col("v.value").alias("variant_value"),
        col("v.stock_quantity").alias("variant_stock_quantity"), col("img.id").alias("image_id"),
        col("img.alt_text").alias("image_alt_text"), col("img.file_size").alias("image_file_size"),
        col("img.is_main").alias("image_is_main"), col("img.object_key").alias("image_object_key"),
        col("img.image_order").alias("image_order"), col("r.id").alias("review_id"),
        col("r.user_id").alias("review_user_id"), col("r.rating").alias("review_rating"),
        col("r.comment").alias("review_comment"), col("r.created_at").alias("review_created_at")
    ) \
    .dropDuplicates(["product_id", "variant_id", "image_id", "review_id"]) \
    .withColumn("Product_year", year("product_created_at")) \
    .withColumn("Product_month", month("product_created_at")) \
    .withColumn("Product_day", dayofmonth("product_created_at"))

product_silver.repartition("Product_year", "Product_month", "Product_day") \
    .sortWithinPartitions("category_name", "product_status") \
    .write.format("delta").mode("overwrite") \
    .partitionBy("Product_year", "Product_month", "Product_day") \
    .save(f"{OUTPUT_PATH}/products_silver")

# ---------- Transform: Users ----------
users = delta_tables["users"]
address = delta_tables["address"]
user_silver = users.alias("u") \
    .join(address.alias("a"), col("u.id") == col("a.user_id"), "inner") \
    .withColumn("user_year", year(col("u.created_at"))) \
    .withColumn("user_month", month(col("u.created_at"))) \
    .withColumn("user_day", dayofmonth(col("u.created_at"))) \
    .select(
        col("u.id").alias("user_id"), col("u.full_name").alias("user_full_name"),
        col("u.email").alias("user_email"), col("u.phone_number").alias("user_phone"),
        col("u.gender").alias("user_gender"), col("u.role").alias("user_role"),
        col("u.provider").alias("user_provider"), col("u.is_verified").alias("user_verified"),
        col("u.is_enabled").alias("user_enabled"), col("u.created_at").alias("user_created_at"),
        col("u.updated_at").alias("user_updated_at"), col("a.id").alias("address_id"),
        col("a.city").alias("address_city"), col("a.region").alias("address_region"),
        col("a.country").alias("address_country"), col("a.zip_code").alias("address_zip"),
        col("a.is_default").alias("address_is_default"), col("a.created_at").alias("address_created_at"),
        col("a.updated_at").alias("address_updated_at"), col("user_year"), col("user_month"), col("user_day")
    ) \
    .dropDuplicates(["user_id", "address_id"])

user_silver.repartition("user_year", "user_month", "user_day") \
    .sortWithinPartitions("address_country", "address_region", "user_role", "user_provider") \
    .write.format("delta").mode("overwrite") \
    .partitionBy("user_year", "user_month", "user_day") \
    .save(f"{OUTPUT_PATH}/users_silver")

# ---------- Transform: Orders & Payments ----------
orders = delta_tables["orders"]
order_items = delta_tables["order_items"]
carts = delta_tables["carts"]
cart_items = delta_tables["cart_items"]
shipping = delta_tables["shipping_info"]

orders_silver = orders.alias("o") \
    .join(order_items.alias("oi"), col("o.id") == col("oi.order_id"), "left") \
    .join(carts.alias("c"), col("o.user_id") == col("c.customer_id"), "left") \
    .join(cart_items.alias("ci"), col("c.id") == col("ci.cart_id"), "left") \
    .join(shipping.alias("s"), col("o.id") == col("s.order_id"), "left") \
    .select(
        col("o.id").alias("order_id"), col("o.user_id").alias("order_user_id"),
        col("o.order_date").alias("order_date"), col("o.status").alias("order_status"),
        col("o.total_amount").alias("order_total_amount"), col("o.tracking_number").alias("order_tracking_number"),
        col("o.dispatch_date").alias("order_dispatch_date"), col("oi.id").alias("order_item_id"),
        col("oi.product_id").alias("order_product_id"), col("oi.quantity").alias("order_item_quantity"),
        col("oi.unit_price").alias("order_item_unit_price"), col("oi.total_price").alias("order_item_total_price"),
        col("c.id").alias("cart_id"), col("c.session_id").alias("cart_session_id"), col("c.created_at").alias("cart_created_at"),
        col("ci.id").alias("cart_item_id"), col("ci.product_id").alias("cart_item_product_id"),
        col("ci.product_variant_id").alias("cart_item_variant_id"), col("ci.quantity").alias("cart_item_quantity"),
        col("ci.unit_price").alias("cart_item_unit_price"), col("s.address").alias("shipping_address"),
        col("s.city").alias("shipping_city"), col("s.delivery_fee").alias("shipping_delivery_fee"),
        col("s.is_express").alias("shipping_is_express"), col("s.delivered_at").alias("shipping_delivered_at")
    ) \
    .dropDuplicates(["order_id", "order_item_id", "cart_id", "cart_item_id"]) \
    .withColumn("order_year", year("order_date")) \
    .withColumn("order_month", month("order_date")) \
    .withColumn("order_day", dayofmonth("order_date"))

orders_silver.repartition("order_year", "order_month", "order_day") \
    .sortWithinPartitions("order_status") \
    .write.format("delta").mode("overwrite") \
    .partitionBy("order_year", "order_month", "order_day") \
    .save(f"{OUTPUT_PATH}/orders_silver")

# Payments + Orders Join
payments = delta_tables["payments"]
order_cols = orders.columns

payments_orders = payments.alias("p") \
    .join(orders.alias("o"), col("p.order_id") == col("o.id"), "inner") \
    .select(
        col("p.id").alias("payment_id"), col("p.order_id"), col("p.payment_method"),
        col("p.transaction_id"), col("p.amount").alias("payment_amount"),
        col("p.status").alias("payment_status"), col("p.paid_at").alias("payment_paid_at"),
        *[col("o." + c).alias("order_" + c) for c in order_cols]
    ) \
    .withColumn("payment_year", year("payment_paid_at")) \
    .withColumn("payment_month", month("payment_paid_at")) \
    .withColumn("payment_day", dayofmonth("payment_paid_at"))

payments_orders.repartition("payment_year", "payment_month", "payment_day") \
    .sortWithinPartitions("payment_method") \
    .write.format("delta").mode("overwrite") \
    .partitionBy("payment_year", "payment_month", "payment_day") \
    .save(f"{OUTPUT_PATH}/payments_orders_silver")

# ---------- Transform: Returns ----------
returns = delta_tables["returns"]
returns_partitioned = returns \
    .withColumn("return_year", year("request_at")) \
    .withColumn("return_month", month("request_at")) \
    .withColumn("return_day", dayofmonth("request_at"))

returns_partitioned.repartition("return_year", "return_month", "return_day") \
    .sortWithinPartitions("status") \
    .write.format("delta").mode("overwrite") \
    .partitionBy("return_year", "return_month", "return_day") \
    .save(f"{OUTPUT_PATH}/returns_silver")

logger.info("🎉 Glue Delta Silver job complete.")
job.commit()
