
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


# OLIST E-COMMERCE DATA ANALYST PROJECT
# PART 1: PYTHON DATA ANALYSIS


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

FILE_NAME = "olist_orders_dataset.csv"

# 1. LOAD DATA
# Supports both CSV folder structures.
possible_paths = [
    BASE_DIR / FILE_NAME / FILE_NAME,
    BASE_DIR / FILE_NAME,
]

csv_path = next(
    (path for path in possible_paths if path.is_file()),
    None
)

if csv_path is None:
    raise FileNotFoundError(
        f"Cannot find {FILE_NAME}. Check the CSV file location."
    )

df = pd.read_csv(csv_path)

print("=" * 55)
print("OLIST E-COMMERCE DATA ANALYSIS")
print("=" * 55)

print("\nDataset shape:", df.shape)
print("\nColumn names:")
print(df.columns.tolist())

# 2. DATA QUALITY CHECKS
print("\n--- ORDER STATUS COUNTS ---")
print(df["order_status"].value_counts())

print("\n--- MISSING VALUES ---")
missing_values = df.isnull().sum()
print(missing_values)

missing_values.to_csv(
    OUTPUT_DIR / "missing_values_report.csv",
    header=["missing_count"]
)

print("\nDuplicate order IDs:", df["order_id"].duplicated().sum())

print("\n--- MISSING DELIVERY DATES BY STATUS ---")
missing_delivery_by_status = (
    df.groupby("order_status")["order_delivered_customer_date"]
    .apply(lambda col: col.isna().sum())
)
print(missing_delivery_by_status)

# 3. CONVERT DATE COLUMNS
date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

for col in date_columns:
    df[col] = pd.to_datetime(df[col], errors="coerce")

print("\n--- DATE DATA TYPES ---")
print(df[date_columns].dtypes)

# 4. CHECK INVALID DELIVERY DATES
invalid_dates = df[
    df["order_delivered_customer_date"].notna()
    & (
        df["order_delivered_customer_date"]
        < df["order_purchase_timestamp"]
    )
]

print("\nInvalid delivery dates:", len(invalid_dates))

invalid_dates.to_csv(
    OUTPUT_DIR / "invalid_delivery_dates.csv",
    index=False
)

# 5. DELIVERY TIME ANALYSIS
delivered_orders = df[
    (df["order_status"] == "delivered")
    & df["order_delivered_customer_date"].notna()
    & df["order_purchase_timestamp"].notna()
].copy()

delivered_orders["delivery_days"] = (
    delivered_orders["order_delivered_customer_date"]
    - delivered_orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

print("\n--- DELIVERY TIME ANALYSIS ---")
print("Eligible delivered orders:", len(delivered_orders))
print(
    "Average delivery days:",
    round(delivered_orders["delivery_days"].mean(), 2)
)
print(
    "Median delivery days:",
    round(delivered_orders["delivery_days"].median(), 2)
)

# 6. DELIVERY PERFORMANCE AGAINST ESTIMATED DATE
delivery_kpi_orders = delivered_orders[
    delivered_orders["order_estimated_delivery_date"].notna()
].copy()

delivery_kpi_orders["delay_days"] = (
    delivery_kpi_orders["order_delivered_customer_date"]
    - delivery_kpi_orders["order_estimated_delivery_date"]
).dt.total_seconds() / 86400

delivery_kpi_orders["delivery_result"] = (
    delivery_kpi_orders["delay_days"]
    .apply(
        lambda days: (
            "Late" if days > 0
            else "On Time or Early"
        )
    )
)

print("\n--- DELIVERY PERFORMANCE ---")
print(delivery_kpi_orders["delivery_result"].value_counts())

print(
    "Average estimated delivery days:",
    round(
        (
            delivery_kpi_orders["order_estimated_delivery_date"]
            - delivery_kpi_orders["order_purchase_timestamp"]
        ).dt.total_seconds().div(86400).mean(),
        2
    )
)

print(
    "Average delay days:",
    round(delivery_kpi_orders["delay_days"].mean(), 2)
)

late_percentage = (
    delivery_kpi_orders["delivery_result"].eq("Late").mean() * 100
)

print("Late delivery percentage:", round(late_percentage, 2), "%")

delivery_kpi_orders.to_csv(
    OUTPUT_DIR / "delivery_performance.csv",
    index=False
)

# 7. MONTHLY ORDER ANALYSIS
df["order_month"] = (
    df["order_purchase_timestamp"].dt.to_period("M")
)

monthly_orders = (
    df.groupby("order_month")["order_id"]
    .count()
    .reset_index(name="total_orders")
)

monthly_orders["order_month"] = (
    monthly_orders["order_month"].astype(str)
)

print("\n--- MONTHLY ORDER ANALYSIS ---")
print(monthly_orders.to_string(index=False))

monthly_orders.to_csv(
    OUTPUT_DIR / "monthly_orders.csv",
    index=False
)

best_month = monthly_orders.loc[
    monthly_orders["total_orders"].idxmax()
]

print("\nMonth with highest orders:", best_month["order_month"])
print("Orders in that month:", best_month["total_orders"])

# 8. ORDER STATUS REPORT
status_summary = (
    df.groupby("order_status")["order_id"]
    .count()
    .reset_index(name="total_orders")
    .sort_values("total_orders", ascending=False)
)

status_summary.to_csv(
    OUTPUT_DIR / "order_status_summary.csv",
    index=False
)

# 9. MONTHLY ORDERS LINE CHART
monthly_orders["order_month"] = pd.to_datetime(
    monthly_orders["order_month"]
)

plt.figure(figsize=(12, 6))
plt.plot(
    monthly_orders["order_month"],
    monthly_orders["total_orders"],
    marker="o"
)

plt.title("Monthly Order Trend")
plt.xlabel("Month")
plt.ylabel("Number of Orders")
plt.xticks(rotation=45)
plt.grid(True, alpha=0.3)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "monthly_order_trend.png",
    dpi=150
)
plt.close()

# 10. ORDER STATUS BAR CHART
plt.figure(figsize=(10, 6))
plt.bar(
    status_summary["order_status"],
    status_summary["total_orders"]
)

plt.title("Orders by Status")
plt.xlabel("Order Status")
plt.ylabel("Number of Orders")
plt.xticks(rotation=45)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR / "orders_by_status.png",
    dpi=150
)
plt.close()

# 11. EXPORT CLEANED ORDERS DATA
df.to_csv(
    OUTPUT_DIR / "orders_analyzed.csv",
    index=False
)

print("\n" + "=" * 55)
print("PYTHON ANALYSIS COMPLETED SUCCESSFULLY")
print("Reports and charts saved in:", OUTPUT_DIR)
print("=" * 55)



