"""
DAG: olist_batch_ingestion
Pulls the Olist orders, order_items, and products datasets and lands them
into the Bronze layer (raw landing zone) as CSV and Parquet respectively.

Data source: Olist Brazilian E-Commerce Public Dataset (Kaggle)
https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

For this first version, we assume the raw Kaggle CSVs have already been
manually downloaded into /opt/airflow/data/raw/ (see README for download
instructions). A later iteration could automate the Kaggle API download
directly inside this DAG.
"""

from datetime import datetime
import pandas as pd
import os

from airflow import DAG
from airflow.operators.python import PythonOperator

RAW_DATA_DIR = "/opt/airflow/data/raw"
BRONZE_DATA_DIR = "/opt/airflow/data/bronze"

default_args = {
    "owner": "karan",
    "retries": 1,
}


def land_orders_and_items():
    """
    Reads the raw Olist orders and order_items CSVs, does a light merge
    on order_id (so Bronze already has one useful combined table),
    and writes the result as CSV into Bronze. This is intentionally
    NOT cleaned or deduplicated yet -- that's Silver's job. Bronze
    just needs to reliably land the raw shape of the data.
    """
    orders_path = os.path.join(RAW_DATA_DIR, "olist_orders_dataset.csv")
    items_path = os.path.join(RAW_DATA_DIR, "olist_order_items_dataset.csv")

    orders_df = pd.read_csv(orders_path)
    items_df = pd.read_csv(items_path)

    print(f"Loaded {len(orders_df)} orders and {len(items_df)} order items")

    os.makedirs(BRONZE_DATA_DIR, exist_ok=True)
    orders_df.to_csv(os.path.join(BRONZE_DATA_DIR, "orders_bronze.csv"), index=False)
    items_df.to_csv(os.path.join(BRONZE_DATA_DIR, "order_items_bronze.csv"), index=False)

    print("Landed orders and order_items into Bronze (CSV)")


def land_products_as_parquet():
    """
    Reads the raw Olist products CSV and writes it out as Parquet into
    Bronze. Products is reference/dimension data -- read often, written
    rarely -- so Parquet's columnar format is a natural fit here, unlike
    the fast-moving orders/order_items fact data above.
    """
    products_path = os.path.join(RAW_DATA_DIR, "olist_products_dataset.csv")
    products_df = pd.read_csv(products_path)

    print(f"Loaded {len(products_df)} products")

    os.makedirs(BRONZE_DATA_DIR, exist_ok=True)
    products_df.to_parquet(
        os.path.join(BRONZE_DATA_DIR, "products_bronze.parquet"), index=False
    )

    print("Landed products into Bronze (Parquet)")


with DAG(
    dag_id="olist_batch_ingestion",
    description="Land Olist orders/order_items (CSV) and products (Parquet) into Bronze",
    default_args=default_args,
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["bronze", "ingestion", "batch"],
) as dag:

    ingest_orders_and_items = PythonOperator(
        task_id="land_orders_and_items",
        python_callable=land_orders_and_items,
    )

    ingest_products = PythonOperator(
        task_id="land_products_as_parquet",
        python_callable=land_products_as_parquet,
    )

    # Both can run in parallel -- they're independent sources
    [ingest_orders_and_items, ingest_products]
