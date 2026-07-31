import pandas as pd

checks = {
    "olist_orders_dataset.csv": ["order_status"],
    "olist_order_payments_dataset.csv": ["payment_type"],
    "olist_customers_dataset.csv": ["customer_state"],
    "olist_sellers_dataset.csv": ["seller_state"],
    "olist_products_dataset.csv": ["product_category_name"],
}

for filename, cols in checks.items():
    df = pd.read_csv(f"data/raw/{filename}")
    for col in cols:
        print(f"\n--- {filename} :: {col} ---")
        print(sorted(df[col].dropna().unique().tolist()))