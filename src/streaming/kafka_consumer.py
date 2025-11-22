#!/usr/bin/env python3
"""
Simple Kafka consumer to demonstrate real-time processing.
"""

import json
import logging
import signal
import sys
from datetime import datetime

from kafka import KafkaConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SimpleKafkaProcessor:
    def __init__(self):
        self.topics = ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"]
        self.consumer = None
        self.running = True

    def setup_consumer(self):
        """Setup Kafka consumer."""
        try:
            self.consumer = KafkaConsumer(
                *self.topics,
                bootstrap_servers=["localhost:9092"],
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="data-pipeline-processor",
            )
            logger.info("✅ Connected to Kafka consumer")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to setup Kafka consumer: {e}")
            return False

    def process_message(self, message):
        """Process individual message."""
        topic = message.topic
        data = message.value
        partition = message.partition
        offset = message.offset

        # Add processing metadata
        processed_data = {
            **data,
            "processing_time": datetime.now().isoformat(),
            "kafka_metadata": {"topic": topic, "partition": partition, "offset": offset},
        }

        # Simple processing based on topic
        if topic == "user_events":
            logger.info(f"👤 User Event: {data.get('user_id')} - {data.get('event_type')}")
        elif topic == "transactions":
            logger.info(
                f"💳 Transaction: {data.get('amount')} {data.get('currency')} - {data.get('user_id')}"
            )
        elif topic == "sensor_data":
            logger.info(
                f"🌡️ Sensor: {data.get('sensor_id')} - {data.get('temperature')}°C, {data.get('humidity')}%"
            )
        elif topic == "log_events":
            logger.info(
                f"📝 Log: [{data.get('log_level')}] {data.get('service')} - {data.get('message')}"
            )
        elif topic == "bulk_upload":
            logger.info(f"📦 Bulk: {data.get('record_count')} records - {data.get('data_type')}")

        return processed_data

    def signal_handler(self, signum, frame):
        """Handle shutdown signal."""
        logger.info("🛑 Received shutdown signal...")
        self.running = False

    def run(self):
        """Run the processor."""
        logger.info("🚀 Starting Kafka Stream Processor...")

        # Setup signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        if not self.setup_consumer():
            return

        logger.info(f"📊 Processing messages from topics: {', '.join(self.topics)}")
        logger.info("Press Ctrl+C to stop...")

        processed_count = 0

        try:
            for message in self.consumer:
                if not self.running:
                    break

                try:
                    self.process_message(message)
                    processed_count += 1

                    if processed_count % 10 == 0:
                        logger.info(f"📈 Processed {processed_count} messages so far...")

                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")

        except KeyboardInterrupt:
            logger.info("🛑 Keyboard interrupt received...")
        finally:
            if self.consumer:
                self.consumer.close()
            logger.info(f"✅ Processor stopped. Total messages processed: {processed_count}")


if __name__ == "__main__":
    processor = SimpleKafkaProcessor()
    processor.run()
