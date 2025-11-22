"""Integration tests for Kafka connectivity."""

import pytest
import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
import time


@pytest.fixture(scope="module")
def kafka_producer():
    """Create Kafka producer for testing."""
    try:
        producer = KafkaProducer(
            bootstrap_servers=["localhost:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=5000,
        )
        yield producer
        producer.close()
    except NoBrokersAvailable:
        pytest.skip("Kafka broker not available")


@pytest.fixture(scope="module")
def kafka_consumer():
    """Create Kafka consumer for testing."""
    try:
        consumer = KafkaConsumer(
            bootstrap_servers=["localhost:9092"],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
            consumer_timeout_ms=5000,
        )
        yield consumer
        consumer.close()
    except NoBrokersAvailable:
        pytest.skip("Kafka broker not available")


def test_kafka_connection(kafka_producer):
    """Test basic Kafka connection."""
    assert kafka_producer is not None
    assert kafka_producer.bootstrap_connected()


def test_send_and_receive_message(kafka_producer, kafka_consumer):
    """Test sending and receiving a message through Kafka."""
    topic = "test_topic"
    test_message = {"test_key": "test_value", "timestamp": "2024-01-01T00:00:00"}

    # Send message
    future = kafka_producer.send(topic, value=test_message)
    kafka_producer.flush()
    result = future.get(timeout=10)

    assert result is not None
    assert result.topic == topic

    # Receive message
    kafka_consumer.subscribe([topic])
    time.sleep(2)  # Wait for message to be available

    messages = []
    for message in kafka_consumer:
        messages.append(message.value)
        break

    assert len(messages) > 0
    assert messages[0]["test_key"] == "test_value"


def test_user_events_schema(kafka_producer):
    """Test sending user_events with correct schema."""
    topic = "user_events"
    message = {
        "user_id": "test_user_123",
        "event_type": "login",
        "timestamp": "2024-01-01T10:00:00",
        "properties": '{"device": "mobile"}',
        "_operation": "insert",
    }

    future = kafka_producer.send(topic, value=message)
    kafka_producer.flush()
    result = future.get(timeout=10)

    assert result is not None
    assert result.topic == topic


def test_transactions_schema(kafka_producer):
    """Test sending transactions with correct schema."""
    topic = "transactions"
    message = {
        "transaction_id": "txn_123",
        "user_id": "user_456",
        "amount": "99.99",
        "currency": "USD",
        "timestamp": "2024-01-01T10:00:00",
        "_operation": "insert",
    }

    future = kafka_producer.send(topic, value=message)
    kafka_producer.flush()
    result = future.get(timeout=10)

    assert result is not None
    assert result.topic == topic
