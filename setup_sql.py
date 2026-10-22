import pandas as pd
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "olist_analysis.db"

files = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "products": "olist_products_dataset.csv"
}

conn = sqlite3.connect(DB_PATH)

try:
    for table_name, filename in files.items():
        file_path = BASE_DIR / filename

        # If the CSV name is actually a folder, find the file inside
        if file_path.is_dir():
            file_path = file_path / filename

        if not file_path.is_file():
            print(f"FILE NOT FOUND: {file_path}")
            continue

        df = pd.read_csv(file_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)

        print(f"{table_name}: {len(df)} rows loaded")

    print("\nDatabase setup finished!")

finally:
    conn.close()