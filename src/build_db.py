import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

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

def build_database():
    """Loads all 9 CSV files into the SQLite database."""
    conn = sqlite3.connect(DB_PATH) 

    for filename in CSV_FILES:
        table_name = filename.replace(".csv", "")
        df = pd.read_csv(f"data/raw/{filename}")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"Loaded {table_name} — {len(df)} rows")

    conn.close()
    print("\nAll 9 tables loaded into data/olist.db")

if __name__ == "__main__":
    build_database()