#!/usr/bin/env python3
"""
Sample data generator for testing the data pipeline.
Sends realistic test data to all Kafka topics.
"""

import json
import random
import time
from datetime import datetime, timedelta
from kafka import KafkaProducer
from typing import Dict, Any
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SampleDataGenerator:
    def __init__(self):
        self.producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )

    def generate_user_events(self) -> Dict[str, Any]:
        """Generate sample user events."""
        events = ["login", "logout", "page_view", "click", "purchase", "search"]
        return {
            "user_id": f"user_{random.randint(1, 1000)}",
            "event_type": random.choice(events),
            "timestamp": datetime.now().isoformat(),
            "properties": json.dumps(
                {
                    "page": f"/page_{random.randint(1, 10)}",
                    "session_id": str(uuid.uuid4())[:8],
                    "device": random.choice(["mobile", "desktop", "tablet"]),
                }
            ),
        }

    def generate_transactions(self) -> Dict[str, Any]:
        """Generate sample transaction data."""
        currencies = ["USD", "EUR", "GBP", "JPY"]
        return {
            "transaction_id": str(uuid.uuid4()),
            "user_id": f"user_{random.randint(1, 1000)}",
            "amount": round(random.uniform(10.0, 1000.0), 2),
            "currency": random.choice(currencies),
            "timestamp": datetime.now().isoformat(),
        }

    def generate_sensor_data(self) -> Dict[str, Any]:
        """Generate sample IoT sensor data."""
        locations = ["warehouse_a", "warehouse_b", "office_1", "factory_floor", "server_room"]
        return {
            "sensor_id": f"sensor_{random.randint(1, 100)}",
            "location": random.choice(locations),
            "temperature": round(random.uniform(15.0, 35.0), 1),
            "humidity": round(random.uniform(30.0, 80.0), 1),
            "timestamp": datetime.now().isoformat(),
        }

    def generate_log_events(self) -> Dict[str, Any]:
        """Generate sample log events."""
        levels = ["INFO", "WARN", "ERROR", "DEBUG"]
        services = ["api-gateway", "user-service", "payment-service", "notification-service"]
        messages = [
            "Request processed successfully",
            "Database connection established",
            "Cache miss for key",
            "Authentication failed",
            "Rate limit exceeded",
            "Service health check passed",
        ]
        return {
            "log_level": random.choice(levels),
            "message": random.choice(messages),
            "service": random.choice(services),
            "timestamp": datetime.now().isoformat(),
        }

    def generate_bulk_upload(self) -> Dict[str, Any]:
        """Generate sample bulk upload events."""
        data_types = ["customer_data", "product_catalog", "inventory_update", "sales_report"]
        return {
            "batch_id": str(uuid.uuid4()),
            "record_count": random.randint(100, 10000),
            "data_type": random.choice(data_types),
            "timestamp": datetime.now().isoformat(),
        }

    def send_sample_data(self, topic: str, count: int = 10):
        """Send sample data to a specific topic."""
        generators = {
            "user_events": self.generate_user_events,
            "transactions": self.generate_transactions,
            "sensor_data": self.generate_sensor_data,
            "log_events": self.generate_log_events,
            "bulk_upload": self.generate_bulk_upload,
        }

        if topic not in generators:
            logger.error(f"Unknown topic: {topic}")
            return

        logger.info(f"Sending {count} messages to topic: {topic}")

        for i in range(count):
            data = generators[topic]()
            key = (
                data.get("user_id") or data.get("transaction_id") or data.get("sensor_id") or str(i)
            )

            self.producer.send(topic, value=data, key=key)
            logger.info(f"Sent message {i+1}/{count} to {topic}: {data}")
            time.sleep(0.1)  # Small delay between messages

        self.producer.flush()
        logger.info(f"Completed sending {count} messages to {topic}")

    def send_continuous_data(self, duration_minutes: int = 5):
        """Send continuous data to all topics for testing."""
        topics = ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"]
        end_time = datetime.now() + timedelta(minutes=duration_minutes)

        logger.info(f"Starting continuous data generation for {duration_minutes} minutes...")

        while datetime.now() < end_time:
            topic = random.choice(topics)
            self.send_sample_data(topic, count=1)
            time.sleep(random.uniform(0.5, 2.0))  # Random delay between messages

        logger.info("Continuous data generation completed")

    def close(self):
        """Close the Kafka producer."""
        self.producer.close()


def main():
    generator = SampleDataGenerator()

    try:
        # Send sample data to all topics
        topics = ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"]

        for topic in topics:
            generator.send_sample_data(topic, count=5)
            time.sleep(1)

        # Optionally run continuous generation
        print("\n🔄 Starting continuous data generation (Ctrl+C to stop)...")
        generator.send_continuous_data(duration_minutes=10)

    except KeyboardInterrupt:
        logger.info("Stopping data generation...")
    finally:
        generator.close()


if __name__ == "__main__":
    main()
