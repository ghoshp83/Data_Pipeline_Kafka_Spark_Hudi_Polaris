#!/usr/bin/env python3
"""
Quick start example for the Data Pipeline.
Demonstrates basic usage of all components.
"""

import json
import time
import uuid
from datetime import datetime
from kafka import KafkaProducer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_data():
    """Create sample data for all topics."""
    return {
        "user_events": {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "event_type": "page_view",
            "timestamp": datetime.now().isoformat(),
            "properties": json.dumps(
                {"page": "/dashboard", "device": "desktop", "session_id": str(uuid.uuid4())[:8]}
            ),
        },
        "transactions": {
            "transaction_id": str(uuid.uuid4()),
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "amount": 149.99,
            "currency": "USD",
            "timestamp": datetime.now().isoformat(),
        },
        "sensor_data": {
            "sensor_id": f"sensor_{uuid.uuid4().hex[:8]}",
            "location": "warehouse_a",
            "temperature": 23.5,
            "humidity": 42.0,
            "timestamp": datetime.now().isoformat(),
        },
        "log_events": {
            "log_level": "INFO",
            "message": "User authentication successful",
            "service": "api-gateway",
            "timestamp": datetime.now().isoformat(),
        },
        "bulk_upload": {
            "batch_id": str(uuid.uuid4()),
            "record_count": 5000,
            "data_type": "customer_data",
            "timestamp": datetime.now().isoformat(),
        },
    }


def main():
    """Run the quick start example."""
    logger.info("🚀 Starting Data Pipeline Quick Start Example")

    # Create Kafka producer
    try:
        producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        logger.info("✅ Connected to Kafka")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Kafka: {e}")
        logger.info("💡 Make sure to run: docker-compose up -d")
        return

    # Send sample data to all topics
    sample_data = create_sample_data()

    for topic, data in sample_data.items():
        try:
            # Use appropriate key for each topic
            key_field = {
                "user_events": "user_id",
                "transactions": "transaction_id",
                "sensor_data": "sensor_id",
                "log_events": "service",
                "bulk_upload": "batch_id",
            }

            key = data.get(key_field[topic], "default")

            # Send message
            future = producer.send(topic, value=data, key=key)
            result = future.get(timeout=10)

            logger.info(f"✅ Sent to {topic}: {data}")
            logger.info(f"   📍 Partition: {result.partition}, Offset: {result.offset}")

            time.sleep(1)  # Small delay between topics

        except Exception as e:
            logger.error(f"❌ Failed to send to {topic}: {e}")

    producer.close()

    logger.info("🎉 Quick start example completed!")
    logger.info("📊 Check the following URLs:")
    logger.info("   • Kafka UI: http://localhost:8080")
    logger.info("   • Spark UI: http://localhost:4040 (when streaming job is running)")
    logger.info("   • Grafana: http://localhost:3000")
    logger.info(
        "🚀 Start the streaming processor: python src/streaming/spark_streaming_processor.py"
    )


if __name__ == "__main__":
    main()
