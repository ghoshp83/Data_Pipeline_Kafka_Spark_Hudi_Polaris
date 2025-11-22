#!/usr/bin/env python3
"""Performance benchmarking script for the data pipeline."""

import time
import json
from kafka import KafkaProducer
from datetime import datetime
import argparse
import statistics


def benchmark_throughput(
    bootstrap_servers: str, topic: str, num_messages: int, batch_size: int = 100
):
    """Benchmark message throughput to Kafka.

    Args:
        bootstrap_servers: Kafka bootstrap servers
        topic: Topic to send messages to
        num_messages: Total number of messages to send
        batch_size: Number of messages per batch
    """
    producer = KafkaProducer(
        bootstrap_servers=[bootstrap_servers],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        compression_type="snappy",
        batch_size=32768,
        linger_ms=10,
    )

    latencies = []
    start_time = time.time()

    print(f"📊 Benchmarking {num_messages} messages to topic '{topic}'...")

    for i in range(num_messages):
        message = {
            "user_id": f"user_{i}",
            "event_type": "benchmark",
            "timestamp": datetime.now().isoformat(),
            "properties": '{"test": "benchmark"}',
            "_operation": "insert",
        }

        msg_start = time.time()
        future = producer.send(topic, value=message)

        if i % batch_size == 0:
            producer.flush()
            msg_end = time.time()
            latencies.append((msg_end - msg_start) * 1000)  # Convert to ms

        if (i + 1) % 1000 == 0:
            print(f"  Sent {i + 1}/{num_messages} messages...")

    producer.flush()
    producer.close()

    end_time = time.time()
    duration = end_time - start_time

    # Calculate metrics
    throughput = num_messages / duration
    avg_latency = statistics.mean(latencies) if latencies else 0
    p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else 0
    p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else 0

    print("\n" + "=" * 60)
    print("📈 Benchmark Results")
    print("=" * 60)
    print(f"Total Messages:     {num_messages:,}")
    print(f"Duration:           {duration:.2f} seconds")
    print(f"Throughput:         {throughput:.2f} messages/sec")
    print(f"Avg Latency:        {avg_latency:.2f} ms")
    print(f"P95 Latency:        {p95_latency:.2f} ms")
    print(f"P99 Latency:        {p99_latency:.2f} ms")
    print("=" * 60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Benchmark data pipeline performance")
    parser.add_argument(
        "--bootstrap-servers",
        default="localhost:9092",
        help="Kafka bootstrap servers",
    )
    parser.add_argument("--topic", default="user_events", help="Kafka topic to benchmark")
    parser.add_argument("--messages", type=int, default=10000, help="Number of messages to send")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for flushing")

    args = parser.parse_args()

    benchmark_throughput(args.bootstrap_servers, args.topic, args.messages, args.batch_size)


if __name__ == "__main__":
    main()
