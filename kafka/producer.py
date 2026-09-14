"""
Simulates a live order event stream by replaying historical Olist order
data into a Kafka topic, at an accelerated pace. This is NOT a live
production feed -- it's a standard, honest technique for demonstrating
streaming architecture on top of batch-shaped historical data.
"""

import json
import time
import pandas as pd
from kafka import KafkaProducer

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
TOPIC_NAME = "order_events"
BRONZE_ORDERS_PATH = "data/bronze/orders_bronze.csv"

def main():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
    )

    orders_df = pd.read_csv(BRONZE_ORDERS_PATH)
    orders_df = orders_df.sort_values("order_purchase_timestamp")

    print(f"Replaying {len(orders_df)} orders into Kafka topic '{TOPIC_NAME}'...")

    for _, row in orders_df.iterrows():
        event = {
            "order_id": row["order_id"],
            "customer_id": row["customer_id"],
            "order_status": row["order_status"],
            "order_purchase_timestamp": row["order_purchase_timestamp"],
        }
        producer.send(TOPIC_NAME, value=event)

        # Accelerated replay: small delay so we can actually observe
        # the stream and Flink's windowed output in real time, rather
        # than dumping 99k events instantly.
        time.sleep(0.05)

    producer.flush()
    print("Finished replaying all orders.")

if __name__ == "__main__":
    main()