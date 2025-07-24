import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime

# Initialize Spark and Glue contexts
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job arguments
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SILVER_PATH', 'GOLD_PATH'])
job.init(args['JOB_NAME'], args)

# Configuration
SILVER_PATH = args['SILVER_PATH']
GOLD_PATH = args['GOLD_PATH']

# Configure Delta Lake
spark.conf.set("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
spark.conf.set("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

# Read Silver Tables
def read_silver_table(table_name):
    return spark.read.format("delta").load(f"{SILVER_PATH}/{table_name}")

orders_silver = read_silver_table("orders_data")
payments_silver = read_silver_table("payments_data")
products_silver = read_silver_table("products_data")
users_silver = read_silver_table("users_data")
vendor_applications_silver = read_silver_table("vendor_applications_data")
returns_silver = read_silver_table("returns_data")

# 1. Sales & Revenue KPIs
def compute_sales_metrics():
    # Daily Sales Metrics
    daily_sales = orders_silver.groupBy("order_year", "order_month", "order_day") \
        .agg(
            sum("order_total_amount").alias("daily_gmv"),
            countDistinct("order_id").alias("order_count"),
            sum(when(col("order_status") == "COMPLETED", 1).otherwise(0)).alias("completed_orders"),
            avg("order_total_amount").alias("average_order_value")
        )
    
    # Payment Method Breakdown
    payment_method_metrics = payments_silver.groupBy("payment_method", "payment_year", "payment_month") \
        .agg(
            sum("amount").alias("total_payment_value"),
            countDistinct("payment_id").alias("payment_count"),
            avg("amount").alias("average_payment_amount")
        )
    
    # Monthly Revenue Trends
    monthly_revenue = payments_silver.groupBy("payment_year", "payment_month") \
        .agg(
            sum("amount").alias("monthly_revenue"),
            countDistinct("order_id").alias("paid_orders_count"),
            (sum("amount") / countDistinct("order_id")).alias("revenue_per_order")
        )
    
    return daily_sales, payment_method_metrics, monthly_revenue

# 2. Product Performance KPIs
def compute_product_metrics():
    # Product Sales Performance
    product_sales = orders_silver.join(products_silver, 
        orders_silver.order_product_id == products_silver.product_id, "left") \
        .groupBy("product_id", "product_name", "category_name") \
        .agg(
            sum("order_item_quantity").alias("total_units_sold"),
            sum(col("order_item_quantity") * col("order_item_unit_price")).alias("total_revenue"),
            avg("review_rating").alias("average_rating"),
            countDistinct("review_id").alias("review_count")
        )
    
    # Inventory Health Metrics
    inventory_metrics = products_silver.groupBy("category_name") \
        .agg(
            sum("product_stock_quantity").alias("total_inventory"),
            sum(when(col("product_stock_quantity") < col("product_low_stock_threshold"), 1).otherwise(0)).alias("low_stock_items"),
            avg("product_stock_quantity").alias("average_stock_level")
        )
    
    return product_sales, inventory_metrics

# 3. Customer Insights KPIs
def compute_customer_metrics():
    # Customer Segmentation Metrics
    customer_segments = users_silver.groupBy("user_gender", "user_role", "address_country") \
        .agg(
            countDistinct("user_id").alias("customer_count"),
            avg(when(col("user_verified") == True, 1).otherwise(0)).alias("verification_rate")
        )
    
    # Customer Lifetime Value (CLV)
    customer_clv = orders_silver.join(users_silver, 
        orders_silver.user_id == users_silver.user_id, "left") \
        .groupBy("user_id", "user_full_name", "user_email", "address_country") \
        .agg(
            sum("order_total_amount").alias("total_order_amount"),
            countDistinct("order_id").alias("order_count"),
            min("order_date").alias("first_order_date"),
            max("order_date").alias("last_order_date")
        )
    
    return customer_segments, customer_clv

# 4. Vendor Performance KPIs
def compute_vendor_metrics():
    # Vendor Application Metrics
    vendor_app_metrics = vendor_applications_silver.groupBy("business_account_type", "status") \
        .agg(
            countDistinct("id").alias("application_count"),
            avg("app_year").alias("average_application_year")
        )
    
    # Vendor Sales Performance
    vendor_sales = products_silver.join(orders_silver, 
        products_silver.product_id == orders_silver.order_product_id) \
        .groupBy("product_vendor_id") \
        .agg(
            sum("order_item_quantity").alias("total_units_sold"),
            sum(col("order_item_quantity") * col("order_item_unit_price")).alias("total_sales"),
            countDistinct("order_id").alias("order_count")
        )
    
    return vendor_app_metrics, vendor_sales

# 5. Operational Efficiency KPIs
def compute_operational_metrics():
    # Return Rate Analysis
    return_analysis = returns_silver.groupBy("status", "return_year", "return_month") \
        .agg(
            countDistinct("id").alias("return_count")
        )
    
    # Shipping Performance
    shipping_performance = orders_silver.groupBy("shipping_city", "is_express") \
        .agg(
            avg("delivery_fee").alias("average_delivery_fee"),
            countDistinct("order_id").alias("shipment_count"),
            avg(datediff(col("delivered_at"), col("order_date"))).alias("average_delivery_days")
        )
    
    return return_analysis, shipping_performance

# 6. Executive Dashboard Metrics
def compute_executive_dashboard():
    # Compute all metrics first
    daily_sales, _, _ = compute_sales_metrics()
    product_sales, _ = compute_product_metrics()
    customer_segments, _ = compute_customer_metrics()
    vendor_app_metrics, _ = compute_vendor_metrics()
    
    # Register temporary views
    daily_sales.createOrReplaceTempView("daily_sales")
    product_sales.createOrReplaceTempView("product_sales")
    customer_segments.createOrReplaceTempView("customer_segments")
    vendor_app_metrics.createOrReplaceTempView("vendor_app_metrics")
    
    # Executive Summary Metrics
    executive_dashboard = spark.sql("""
        SELECT
            current_date() as report_date,
            (SELECT sum(daily_gmv) FROM daily_sales WHERE order_year = year(current_date())) as ytd_revenue,
            (SELECT sum(order_count) FROM daily_sales WHERE order_year = year(current_date())) as ytd_orders,
            (SELECT sum(total_units_sold) FROM product_sales) as total_units_sold,
            (SELECT sum(customer_count) FROM customer_segments WHERE user_role = 'CUSTOMER') as total_customers,
            (SELECT sum(application_count) FROM vendor_app_metrics WHERE status = 'APPROVED') as active_vendors,
            (SELECT avg(average_rating) FROM product_sales WHERE review_count > 10) as avg_product_rating
    """)
    
    return executive_dashboard

# Write Gold Tables to S3
def write_gold_table(df, table_name, partition_cols=None):
    writer = df.write.format("delta").mode("overwrite")
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
    writer.save(f"{GOLD_PATH}/{table_name}")

# Main Execution
def main():
    # Compute all metrics
    daily_sales, payment_method_metrics, monthly_revenue = compute_sales_metrics()
    product_sales, inventory_metrics = compute_product_metrics()
    customer_segments, customer_clv = compute_customer_metrics()
    vendor_app_metrics, vendor_sales = compute_vendor_metrics()
    return_analysis, shipping_performance = compute_operational_metrics()
    executive_dashboard = compute_executive_dashboard()
    
    # Write all gold tables
    write_gold_table(daily_sales, "daily_sales_metrics", ["order_year", "order_month"])
    write_gold_table(payment_method_metrics, "payment_method_metrics", ["payment_year", "payment_month"])
    write_gold_table(monthly_revenue, "monthly_revenue_metrics", ["payment_year", "payment_month"])
    write_gold_table(product_sales, "product_sales_metrics")
    write_gold_table(inventory_metrics, "inventory_metrics")
    write_gold_table(customer_segments, "customer_segments")
    write_gold_table(customer_clv, "customer_lifetime_value")
    write_gold_table(vendor_app_metrics, "vendor_application_metrics")
    write_gold_table(vendor_sales, "vendor_sales_metrics")
    write_gold_table(return_analysis, "return_analysis_metrics", ["return_year", "return_month"])
    write_gold_table(shipping_performance, "shipping_performance_metrics")
    write_gold_table(executive_dashboard, "executive_dashboard_metrics")
    
    # Optimize tables for query performance
    for table in ["daily_sales_metrics", "product_sales_metrics", "customer_lifetime_value"]:
        spark.sql(f"OPTIMIZE delta.`{GOLD_PATH}/{table}` ZORDER BY (order_year, order_month)")

if __name__ == "__main__":
    main()
    job.commit()