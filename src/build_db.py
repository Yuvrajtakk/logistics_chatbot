import sqlite3
import pandas as pd

DB_PATH = "data/olist.db"


CSV_FILES = [
    "olist_customers_dataset.csv",
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]

conn = sqlite3.connect(DB_PATH) 


for filename in CSV_FILES:
    table_name = filename.replace(".csv", "")
    df = pd.read_csv(f"data/raw/{filename}")
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    print(f"Loaded {table_name} — {len(df)} rows")

conn.close()
print("\nAll 9 tables loaded into data/olist.db")

conn = sqlite3.connect(DB_PATH)


result = conn.execute("""
SELECT COUNT(*) 
FROM olist_orders_dataset
WHERE order_status = 'delivered'
""")

print(result.fetchall())

result = conn.execute("""
SELECT
    customer_state,
    COUNT(*) AS customer_count
FROM olist_customers_dataset
GROUP BY customer_state
ORDER BY customer_count DESC
LIMIT 5;
""")

print(result.fetchall())
# What is the average payment_value across all payments?
result = conn.execute("""
SELECT
    AVG(payment_value) AS average_payment_value
FROM olist_order_payments_dataset
""")

print(result.fetchall())

# How many distinct seller_id values are in olist_sellers_dataset?
result = conn.execute("""
SELECT COUNT(DISTINCT seller_id) AS distinct_seller_count
FROM olist_sellers_dataset
""")

print(result.fetchall())

# Which payment_type is used most often, and how many times?
result = conn.execute("""
SELECT payment_type , COUNT(*) AS payment_count
FROM olist_order_payments_dataset
GROUP BY payment_type
ORDER BY payment_count DESC
LIMIT 1
""")
print(result.fetchall())

conn.close()