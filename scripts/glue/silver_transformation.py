# Full implementation with disambiguated column names to avoid duplicate errors
import sys
import os
import logging
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job
from pyspark.sql.functions import col, year, month, dayofmonth

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Get Arguments ----------
args = getResolvedOptions(sys.argv, [
    'JOB_NAME',
    'DELTA_PATH',
    'OUTPUT_PATH',
    'DELTA_TABLES'
])

BASE_PATH = args['DELTA_PATH']
OUTPUT_PATH = args['OUTPUT_PATH']
TABLES = args['DELTA_TABLES'].split(",")

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

# ---------- Load Delta Tables ----------
delta_tables = {}
for table in TABLES:
    path = os.path.join(BASE_PATH, table)
    try:
        delta_tables[table] = spark.read.format("delta").load(path)
        logger.info(f"Loaded table: {table}")
    except Exception as e:
        logger.error(f"Failed to load table {table}: {e}")

# ---------- Transform: Users ----------
required_user_tables = ['users', 'address']
if all(tbl in delta_tables for tbl in required_user_tables):
    users = delta_tables['users']
    address = delta_tables['address']

    user_silver = users.alias("u") \
        .join(address.alias("a"), col("u.id") == col("a.user_id"), "left") \
        .withColumn("user_year", year(col("u.created_at"))) \
        .withColumn("user_month", month(col("u.created_at"))) \
        .withColumn("user_day", dayofmonth(col("u.created_at"))) \
        .select(
            col("u.id").alias("user_id"),
            col("u.full_name").alias("user_full_name"),
            col("u.email").alias("user_email"),
            col("u.phone_number").alias("user_phone"),
            col("u.gender").alias("user_gender"),
            col("u.role").alias("user_role"),
            col("u.provider").alias("user_provider"),
            col("u.is_verified").alias("user_verified"),
            col("u.is_enabled").alias("user_enabled"),
            col("u.created_at").alias("user_created_at"),
            col("u.updated_at").alias("user_updated_at"),
            col("a.id").alias("address_id"),
            col("a.city").alias("address_city"),
            col("a.region").alias("address_region"),
            col("a.country").alias("address_country"),
            col("a.zip_code").alias("address_zip"),
            col("a.is_default").alias("address_is_default"),
            col("user_year"), col("user_month"), col("user_day")
        ).dropDuplicates(["user_id", "address_id"])

    user_silver.repartition("user_year", "user_month", "user_day") \
        .sortWithinPartitions("address_country", "user_role") \
        .write.format("delta").mode("overwrite") \
        .partitionBy("user_year", "user_month", "user_day") \
        .save(os.path.join(OUTPUT_PATH, "users_data"))

    logger.info("✅ Users transformation complete.")
else:
    logger.warning("⚠️ Skipping Users transformation - missing required tables.")

# ---------- Transform: Orders with column disambiguation ----------
required_order_tables = ['orders', 'order_items', 'carts', 'cart_items', 'shipping_info']
if all(tbl in delta_tables for tbl in required_order_tables):
    orders = delta_tables['orders']
    order_items = delta_tables['order_items']
    carts = delta_tables['carts']
    cart_items = delta_tables['cart_items']
    shipping = delta_tables['shipping_info']

    orders_silver = orders.alias("o") \
        .join(order_items.alias("oi"), col("o.id") == col("oi.order_id"), "left") \
        .join(carts.alias("c"), col("o.user_id") == col("c.customer_id"), "left") \
        .join(cart_items.alias("ci"), col("c.id") == col("ci.cart_id"), "left") \
        .join(shipping.alias("s"), col("o.id") == col("s.order_id"), "left") \
        .select(
            col("o.id").alias("order_id"),
            col("o.user_id"),
            col("o.status").alias("order_status"),
            col("o.total_amount"),
            col("o.order_date"),
            col("oi.id").alias("order_item_id"),
            col("oi.product_id").alias("order_product_id"),
            col("oi.quantity").alias("order_item_quantity"),
            col("oi.unit_price").alias("order_item_unit_price"),
            col("c.id").alias("cart_id"),
            col("c.created_at").alias("cart_created_at"),
            col("ci.id").alias("cart_item_id"),
            col("ci.product_variant_id"),
            col("ci.quantity").alias("cart_item_quantity"),
            col("ci.unit_price").alias("cart_item_unit_price"),
            col("s.address").alias("shipping_address"),
            col("s.city").alias("shipping_city"),
            col("s.delivery_fee"),
            col("s.is_express"),
            col("s.delivered_at")
        )

    orders_silver = orders_silver \
        .withColumn("order_year", year("order_date")) \
        .withColumn("order_month", month("order_date")) \
        .withColumn("order_day", dayofmonth("order_date"))

    orders_silver.repartition("order_year", "order_month", "order_day") \
        .sortWithinPartitions("order_status") \
        .write.format("delta").mode("overwrite") \
        .partitionBy("order_year", "order_month", "order_day") \
        .save(os.path.join(OUTPUT_PATH, "orders_data"))

    logger.info("✅ Orders transformation complete.")
else:
    logger.warning("⚠️ Skipping Orders transformation - missing required tables.")

# ---------- Transform: Payments ----------
required_payment_tables = ['payments', 'orders']
if all(tbl in delta_tables for tbl in required_payment_tables):
    payments = delta_tables['payments']
    orders = delta_tables['orders']

    payment_orders = payments.alias("p") \
        .join(orders.alias("o"), col("p.order_id") == col("o.id"), "inner") \
        .select(
            col("p.id").alias("payment_id"),
            col("p.order_id"),
            col("p.payment_method"),
            col("p.transaction_id"),
            col("p.amount"),
            col("p.status").alias("payment_status"),
            col("p.paid_at"),
            col("o.user_id").alias("order_user_id"),
            col("o.total_amount").alias("order_total_amount")
        ) \
        .withColumn("payment_year", year("p.paid_at")) \
        .withColumn("payment_month", month("p.paid_at")) \
        .withColumn("payment_day", dayofmonth("p.paid_at"))

    payment_orders.repartition("payment_year", "payment_month", "payment_day") \
        .sortWithinPartitions("payment_method") \
        .write.format("delta").mode("overwrite") \
        .partitionBy("payment_year", "payment_month", "payment_day") \
        .save(os.path.join(OUTPUT_PATH, "payments_data"))

    logger.info("✅ Payments transformation complete.")
else:
    logger.warning("⚠️ Skipping Payments transformation - missing required tables.")

# ---------- Transform: Returns ----------
if 'returns' in delta_tables:
    returns = delta_tables['returns']
    returns = returns.withColumn("return_year", year("request_at")) \
                     .withColumn("return_month", month("request_at")) \
                     .withColumn("return_day", dayofmonth("request_at"))

    returns.repartition("return_year", "return_month", "return_day") \
        .sortWithinPartitions("status") \
        .write.format("delta").mode("overwrite") \
        .partitionBy("return_year", "return_month", "return_day") \
        .save(os.path.join(OUTPUT_PATH, "returns_data"))

    logger.info("✅ Returns transformation complete.")
else:
    logger.warning("⚠️ Skipping Returns transformation - returns table not available.")

# ---------- Transform: Discounts ----------
if 'discounts' in delta_tables:
    discounts = delta_tables['discounts']
    discounts = discounts.withColumn("discount_year", year("created_at")) \
                         .withColumn("discount_month", month("created_at")) \
                         .withColumn("discount_day", dayofmonth("created_at"))

    discounts.repartition("discount_year", "discount_month", "discount_day") \
        .sortWithinPartitions("type") \
        .write.format("delta").mode("overwrite") \
        .partitionBy("discount_year", "discount_month", "discount_day") \
        .save(os.path.join(OUTPUT_PATH, "discounts_data"))

    logger.info("✅ Discounts transformation complete.")
else:
    logger.warning("⚠️ Skipping Discounts transformation - table not available.")


# ---------- Transform: Vendor Applications ----------
if 'vendor_applications' in delta_tables:
    vendor_app = delta_tables['vendor_applications']
    vendor_app = vendor_app.withColumn("app_year", year("created_at")) \
                           .withColumn("app_month", month("created_at")) \
                           .withColumn("app_day", dayofmonth("created_at"))

    vendor_app.repartition("app_year", "app_month", "app_day") \
        .sortWithinPartitions("business_account_type", "status") \
        .write.format("delta").mode("overwrite") \
        .partitionBy("app_year", "app_month", "app_day") \
        .save(os.path.join(OUTPUT_PATH, "vendor_applications_data"))

    logger.info("✅ Vendor Applications transformation complete.")
else:
    logger.warning("⚠️ Skipping Vendor Applications transformation - table not available.")


# ---------- Transform: Products ----------
if all(tbl in delta_tables for tbl in ['products', 'categories', 'product_variants', 'product_images', 'reviews']):
    products = delta_tables['products']
    categories = delta_tables['categories']
    prod_var = delta_tables['product_variants']
    prod_img = delta_tables['product_images']
    reviews = delta_tables['reviews']

    product_silver = products.alias("p") \
        .join(categories.alias("c"), col("p.id") == col("c.id"), "left") \
        .join(prod_var.alias("v"), col("p.id") == col("v.product_id"), "left") \
        .join(prod_img.alias("img"), col("p.id") == col("img.product_id"), "left") \
        .join(reviews.alias("r"), col("p.id") == col("r.product_id"), "left") \
        .select(
            col("p.id").alias("product_id"),
            col("p.name").alias("product_name"),
            col("p.description").alias("product_description"),
            col("p.sku").alias("product_sku"),
            col("p.price").alias("product_price"),
            col("p.stock_quantity").alias("product_stock_quantity"),
            col("p.weight").alias("product_weight"),
            col("p.status").alias("product_status"),
            col("p.vendor_id").alias("product_vendor_id"),
            col("p.low_stock_threshold").alias("product_low_stock_threshold"),
            col("p.min_order_quantity").alias("product_min_order_quantity"),
            col("p.average_rating").alias("product_average_rating"),
            col("p.thumbnail_url").alias("product_thumbnail_url"),
            col("p.image_urls").alias("product_image_urls"),
            col("p.is_active").alias("product_is_active"),
            col("p.created_at").alias("product_created_at"),
            col("p.updated_at").alias("product_updated_at"),
            col("c.id").alias("category_id"),
            col("c.name").alias("category_name"),
            col("v.id").alias("variant_id"),
            col("v.variant_key").alias("variant_key"),
            col("v.value").alias("variant_value"),
            col("v.stock_quantity").alias("variant_stock_quantity"),
            col("img.id").alias("image_id"),
            col("img.alt_text").alias("image_alt_text"),
            col("img.file_size").alias("image_file_size"),
            col("img.is_main").alias("image_is_main"),
            col("img.object_key").alias("image_object_key"),
            col("img.image_order").alias("image_order"),
            col("r.id").alias("review_id"),
            col("r.user_id").alias("review_user_id"),
            col("r.rating").alias("review_rating"),
            col("r.comment").alias("review_comment"),
            col("r.created_at").alias("review_created_at")
        ).dropDuplicates(["product_id", "variant_id", "image_id", "review_id"])

    df = product_silver.withColumn("Product_year", year("product_created_at")) \
       .withColumn("Product_month", month("product_created_at")) \
       .withColumn("Product_day", dayofmonth("product_created_at"))

    partition_values = df.select("Product_year", "Product_month", "Product_day").distinct().collect()[0]
    year = partition_values["Product_year"]
    month = partition_values["Product_month"]
    day = partition_values["Product_day"]

    df_filtered = df.filter(
        (col("Product_year") == year) &
        (col("Product_month") == month) &
        (col("Product_day") == day)
    )

    df_sorted = df_filtered.repartition(1).sortWithinPartitions("category_name", "product_status")

    df_sorted.write.format("delta").mode("overwrite") \
        .partitionBy("Product_year", "Product_month", "Product_day") \
        .save(os.path.join(OUTPUT_PATH, "products_data"))

    logger.info("✅ Products transformation complete.")
else:
    logger.warning("⚠️ Skipping Products transformation - required tables not available.")

# ---------- Finalize Glue Job ----------
job.commit()
logger.info("🎉 Glue Delta Silver transformation job complete and committed.")
