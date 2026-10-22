import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "olist_analysis.db"
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

if not DB_PATH.is_file():
    raise FileNotFoundError(f"Database not found: {DB_PATH}. Run setup_sql.py first.")

queries = {
    "order_overview": """
        SELECT
            COUNT(*) AS total_orders,
            COUNT(DISTINCT customer_id) AS unique_customers,
            SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
            SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_orders
        FROM orders;
    """,
    "monthly_orders": """
        SELECT
            STRFTIME('%Y-%m', order_purchase_timestamp) AS order_month,
            COUNT(*) AS total_orders,
            SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
            SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_orders
        FROM orders
        WHERE order_purchase_timestamp IS NOT NULL
        GROUP BY STRFTIME('%Y-%m', order_purchase_timestamp)
        ORDER BY order_month;
    """,
    "order_status": """
        SELECT order_status, COUNT(*) AS total_orders,
               ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM orders), 2) AS pct_of_orders
        FROM orders
        GROUP BY order_status
        ORDER BY total_orders DESC;
    """,
    "payment_types": """
        SELECT payment_type, COUNT(*) AS payment_records,
               ROUND(SUM(payment_value), 2) AS total_payment_value,
               ROUND(AVG(payment_value), 2) AS avg_payment_value
        FROM payments
        GROUP BY payment_type
        ORDER BY total_payment_value DESC;
    """,
    "payment_installments": """
        SELECT payment_installments, COUNT(*) AS payment_records,
               ROUND(SUM(payment_value), 2) AS total_payment_value
        FROM payments
        GROUP BY payment_installments
        ORDER BY payment_installments;
    """,
    "top_products_by_items": """
        SELECT oi.product_id, p.product_category_name,
               COUNT(*) AS items_sold,
               ROUND(SUM(oi.price), 2) AS item_sales_value,
               ROUND(SUM(oi.freight_value), 2) AS freight_value
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.product_id
        GROUP BY oi.product_id, p.product_category_name
        ORDER BY items_sold DESC
        LIMIT 20;
    """,
    "top_categories": """
        SELECT COALESCE(p.product_category_name, 'unknown') AS product_category,
               COUNT(*) AS items_sold,
               ROUND(SUM(oi.price), 2) AS item_sales_value,
               ROUND(SUM(oi.freight_value), 2) AS freight_value
        FROM order_items oi
        LEFT JOIN products p ON oi.product_id = p.product_id
        GROUP BY COALESCE(p.product_category_name, 'unknown')
        ORDER BY item_sales_value DESC
        LIMIT 20;
    """,
    "customer_states": """
        SELECT c.customer_state, COUNT(DISTINCT c.customer_unique_id) AS unique_customers,
               COUNT(o.order_id) AS orders_placed
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_state
        ORDER BY orders_placed DESC;
    """,
    "repeat_customers": """
        SELECT
            COUNT(*) AS customer_count,
            SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) AS customers_with_multiple_orders,
            ROUND(100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_with_multiple_orders
        FROM (
            SELECT customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            GROUP BY customer_unique_id
        );
    """,
    "delivery_performance": """
        SELECT
            COUNT(*) AS delivered_orders_with_dates,
            ROUND(AVG((julianday(order_delivered_customer_date) -
                       julianday(order_purchase_timestamp))), 2) AS avg_delivery_days,
            ROUND(AVG(CASE
                WHEN julianday(order_delivered_customer_date) >
                     julianday(order_estimated_delivery_date) THEN 1.0
                ELSE 0.0 END) * 100, 2) AS late_delivery_pct,
            ROUND(AVG(CASE
                WHEN julianday(order_delivered_customer_date) <=
                     julianday(order_estimated_delivery_date) THEN 1.0
                ELSE 0.0 END) * 100, 2) AS on_time_or_early_pct
        FROM orders
        WHERE order_status = 'delivered'
          AND order_purchase_timestamp IS NOT NULL
          AND order_delivered_customer_date IS NOT NULL
          AND order_estimated_delivery_date IS NOT NULL;
    """,
    "monthly_delivery": """
        SELECT STRFTIME('%Y-%m', order_purchase_timestamp) AS order_month,
               COUNT(*) AS delivered_orders,
               ROUND(AVG(julianday(order_delivered_customer_date) -
                         julianday(order_purchase_timestamp)), 2) AS avg_delivery_days,
               ROUND(AVG(CASE
                   WHEN julianday(order_delivered_customer_date) >
                        julianday(order_estimated_delivery_date) THEN 1.0
                   ELSE 0.0 END) * 100, 2) AS late_delivery_pct
        FROM orders
        WHERE order_status = 'delivered'
          AND order_purchase_timestamp IS NOT NULL
          AND order_delivered_customer_date IS NOT NULL
          AND order_estimated_delivery_date IS NOT NULL
        GROUP BY STRFTIME('%Y-%m', order_purchase_timestamp)
        ORDER BY order_month;
    """,
    "top_sellers_by_item_value": """
        SELECT oi.seller_id, COUNT(*) AS items_sold,
               ROUND(SUM(oi.price), 2) AS item_sales_value
        FROM order_items oi
        GROUP BY oi.seller_id
        ORDER BY item_sales_value DESC
        LIMIT 20;
    """,
    "orders_per_customer_distribution": """
        SELECT order_count, COUNT(*) AS customers
        FROM (
            SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS order_count
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            GROUP BY c.customer_unique_id
        )
        GROUP BY order_count
        ORDER BY order_count;
    """,
    "data_quality_checks": """
        SELECT
            (SELECT COUNT(*) FROM orders) AS orders_rows,
            (SELECT COUNT(DISTINCT order_id) FROM orders) AS distinct_order_ids,
            (SELECT COUNT(*) FROM orders WHERE order_purchase_timestamp IS NULL) AS missing_purchase_dates,
            (SELECT COUNT(*) FROM orders WHERE order_status = 'delivered'
                AND order_delivered_customer_date IS NULL) AS delivered_missing_delivery_date,
            (SELECT COUNT(*) FROM order_items WHERE price IS NULL) AS missing_item_prices,
            (SELECT COUNT(*) FROM payments WHERE payment_value IS NULL) AS missing_payment_values;
    """
}

conn = sqlite3.connect(DB_PATH)
results = {}

try:
    for name, query in queries.items():
        df = pd.read_sql_query(query, conn)
        results[name] = df
        print(f"\n{'=' * 72}\n{name.upper().replace('_', ' ')}\n{'=' * 72}")
        print(df.head(15).to_string(index=False))
        print(f"Rows returned: {len(df)}")

    excel_path = OUTPUT_DIR / "sql_analysis_results.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for name, df in results.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)

    print(f"\nSUCCESS: SQL analysis complete.")
    print(f"Excel results saved to: {excel_path}")

except Exception as exc:
    print(f"\nERROR during SQL analysis: {exc}")
    raise
finally:
    conn.close()