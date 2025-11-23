#!/usr/bin/env python3
"""
Unit tests for the Spark streaming processor.
"""

import json
import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from pyspark.sql.types import StringType, StructField, StructType, TimestampType

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from streaming.spark_streaming_processor import DataPipelineProcessor


class TestDataPipelineProcessor:
    @pytest.fixture
    def processor(self):
        """Create a processor instance for testing."""
        with patch("streaming.spark_streaming_processor.SparkSession"):
            processor = DataPipelineProcessor()
            processor.spark = Mock()
            return processor

    def test_schema_definition(self, processor):
        """Test that schemas are properly defined for all topics."""
        schemas = processor.schemas

        # Check all topics have schemas
        expected_topics = [
            "user_events",
            "transactions",
            "sensor_data",
            "log_events",
            "bulk_upload",
        ]
        assert set(schemas.keys()) == set(expected_topics)

        # Check user_events schema
        user_events_schema = schemas["user_events"]
        assert isinstance(user_events_schema, StructType)
        field_names = [field.name for field in user_events_schema.fields]
        assert "user_id" in field_names
        assert "event_type" in field_names
        assert "timestamp" in field_names
        assert "properties" in field_names

    def test_get_record_key(self, processor):
        """Test record key mapping for different topics."""
        assert processor._get_record_key("user_events") == "user_id"
        assert processor._get_record_key("transactions") == "transaction_id"
        assert processor._get_record_key("sensor_data") == "sensor_id"
        assert processor._get_record_key("log_events") == "service"
        assert processor._get_record_key("bulk_upload") == "batch_id"
        assert processor._get_record_key("unknown_topic") == "timestamp"

    @patch("streaming.spark_streaming_processor.boto3")
    def test_setup_s3_bucket(self, mock_boto3, processor):
        """Test S3 bucket setup."""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client

        processor.setup_s3_bucket()

        # Verify S3 client was created with correct parameters
        mock_boto3.client.assert_called_once_with(
            "s3",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )

        # Verify bucket creation was attempted
        mock_s3_client.create_bucket.assert_called_once_with(Bucket="data-pipeline-bucket")

    @patch("streaming.spark_streaming_processor.boto3")
    def test_setup_s3_bucket_already_exists(self, mock_boto3, processor):
        """Test S3 bucket setup when bucket already exists."""
        mock_s3_client = Mock()
        mock_boto3.client.return_value = mock_s3_client
        mock_s3_client.create_bucket.side_effect = Exception("BucketAlreadyExists")

        # Should not raise exception
        processor.setup_s3_bucket()

        mock_s3_client.create_bucket.assert_called_once()

    def test_topics_list(self, processor):
        """Test that all expected topics are defined."""
        expected_topics = [
            "user_events",
            "transactions",
            "sensor_data",
            "log_events",
            "bulk_upload",
        ]
        assert processor.topics == expected_topics

    @patch("streaming.spark_streaming_processor.SparkSession")
    def test_create_spark_session(self, mock_spark_session):
        """Test Spark session creation with proper configuration."""
        mock_builder = Mock()
        mock_spark_session.builder = mock_builder
        mock_builder.appName.return_value = mock_builder
        mock_builder.config.return_value = mock_builder
        mock_builder.getOrCreate.return_value = Mock()

        processor = DataPipelineProcessor()

        # Verify Spark session was configured correctly
        mock_builder.appName.assert_called_with("DataPipelineStreaming")

        # Check that Hudi configurations were set
        config_calls = [call[0] for call in mock_builder.config.call_args_list]
        assert any("hudi" in str(call).lower() for call in config_calls)


if __name__ == "__main__":
    pytest.main([__file__])
