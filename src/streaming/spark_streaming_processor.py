#!/usr/bin/env python3
"""
Real-time Spark Streaming processor for Kafka-Spark-Hudi-Polaris pipeline.
Processes multiple data topics and stores in Hudi format with support for INSERT/UPDATE/DELETE operations.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import boto3
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (col, current_timestamp, date_format,
                                   from_json)
from pyspark.sql.types import (DecimalType, FloatType, IntegerType, StringType,
                               StructField, StructType, TimestampType)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Centralized configuration management for the data pipeline."""

    # Kafka Configuration
    kafka_bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    kafka_starting_offsets: str = os.getenv("KAFKA_STARTING_OFFSETS", "latest")

    # S3 Configuration
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "http://localhost:4566")
    s3_bucket: str = os.getenv("S3_BUCKET", "data-pipeline-bucket")
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "test")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
    aws_region: str = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    # Spark Configuration
    checkpoint_location: str = os.getenv("SPARK_CHECKPOINT_LOCATION", "./checkpoints")
    processing_time: str = os.getenv("SPARK_STREAMING_BATCH_DURATION", "10 seconds")
    shuffle_parallelism: int = int(os.getenv("SPARK_SHUFFLE_PARALLELISM", "2"))

    # Hudi Configuration
    hudi_table_type: str = os.getenv("HUDI_TABLE_TYPE", "COPY_ON_WRITE")
    hudi_index_type: str = os.getenv("HUDI_INDEX_TYPE", "BLOOM")

    def get_s3_path(self, topic: str) -> str:
        """Get S3 path for a topic."""
        return f"s3a://{self.s3_bucket}/hudi-tables/{topic}"

    def get_checkpoint_path(self, topic: str) -> str:
        """Get checkpoint path for a topic."""
        return f"{self.checkpoint_location}/{topic}"


class DataPipelineProcessor:
    """Main data pipeline processor with configuration management."""

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the data pipeline processor.

        Args:
            config: Pipeline configuration. If None, uses default configuration.
        """
        self.config = config or PipelineConfig()
        self.spark = self._create_spark_session()
        self.topics = ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"]
        self.schemas = self._define_schemas()
        logger.info(
            f"Initialized DataPipelineProcessor with config: "
            f"Kafka={self.config.kafka_bootstrap_servers}, S3={self.config.s3_bucket}"
        )

    def _create_spark_session(self) -> SparkSession:
        """Create optimized Spark session with Hudi and Kafka configurations.

        Returns:
            SparkSession: Configured Spark session with Hudi and Kafka support
        """
        return (
            SparkSession.builder.appName("DataPipelineStreaming")
            .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
            .config(
                "spark.sql.catalog.spark_catalog", "org.apache.spark.sql.hudi.catalog.HoodieCatalog"
            )
            .config("spark.sql.extensions", "org.apache.spark.sql.hudi.HoodieSparkSessionExtension")
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
            .config("spark.sql.shuffle.partitions", "200")
            .config("spark.sql.streaming.metricsEnabled", "true")
            .config(
                "spark.sql.streaming.stateStore.providerClass",
                "org.apache.spark.sql.execution.streaming.state.HDFSBackedStateStoreProvider",
            )
            .config("spark.streaming.stopGracefullyOnShutdown", "true")
            .config("spark.streaming.backpressure.enabled", "true")
            .getOrCreate()
        )

    def _define_schemas(self) -> Dict[str, StructType]:
        """Define schemas for each data topic including operation field for DELETE support."""
        return {
            "user_events": StructType(
                [
                    StructField("user_id", StringType(), True),
                    StructField("event_type", StringType(), True),
                    StructField("timestamp", TimestampType(), True),
                    StructField("properties", StringType(), True),
                    StructField("_operation", StringType(), True),  # For DELETE support
                ]
            ),
            "transactions": StructType(
                [
                    StructField("transaction_id", StringType(), True),
                    StructField("user_id", StringType(), True),
                    StructField("amount", DecimalType(10, 2), True),
                    StructField("currency", StringType(), True),
                    StructField("timestamp", TimestampType(), True),
                    StructField("_operation", StringType(), True),  # For DELETE support
                ]
            ),
            "sensor_data": StructType(
                [
                    StructField("sensor_id", StringType(), True),
                    StructField("location", StringType(), True),
                    StructField("temperature", FloatType(), True),
                    StructField("humidity", FloatType(), True),
                    StructField("timestamp", TimestampType(), True),
                    StructField("_operation", StringType(), True),
                ]
            ),
            "log_events": StructType(
                [
                    StructField("log_level", StringType(), True),
                    StructField("message", StringType(), True),
                    StructField("service", StringType(), True),
                    StructField("timestamp", TimestampType(), True),
                    StructField("_operation", StringType(), True),
                ]
            ),
            "bulk_upload": StructType(
                [
                    StructField("batch_id", StringType(), True),
                    StructField("record_count", IntegerType(), True),
                    StructField("data_type", StringType(), True),
                    StructField("timestamp", TimestampType(), True),
                    StructField("_operation", StringType(), True),
                ]
            ),
        }

    def _get_operation_type(self, topic: str) -> str:
        """Determine Hudi operation type based on topic.

        Args:
            topic: Kafka topic name

        Returns:
            Hudi operation type (upsert, insert, bulk_insert, delete)
        """
        operation_mapping = {
            "user_events": "upsert",
            "transactions": "upsert",  # Supports DELETE via _operation field
            "sensor_data": "upsert",
            "log_events": "insert",
            "bulk_upload": "bulk_insert",
        }
        return operation_mapping.get(topic, "upsert")

    def validate_data(self, df: DataFrame, topic: str) -> DataFrame:
        """Validate data quality before writing to Hudi.

        Args:
            df: Input DataFrame
            topic: Topic name for validation rules

        Returns:
            Validated DataFrame with invalid records filtered out
        """
        record_key = self._get_record_key(topic)

        # Basic validation: non-null timestamp and record key
        validated_df = df.filter(
            col("timestamp").isNotNull() & col(record_key).isNotNull() & (col(record_key) != "")
        )

        # Log validation metrics
        original_count = df.count() if not df.isStreaming else "streaming"
        logger.info(f"Data validation for {topic}: Original records={original_count}")

        return validated_df

    def process_stream(self, topic: str) -> Optional[Any]:
        """Process streaming data for a specific topic with error handling.

        Args:
            topic: Kafka topic name

        Returns:
            StreamingQuery object or None if failed

        Raises:
            ValueError: If topic is not supported
        """
        if topic not in self.topics:
            raise ValueError(f"Unsupported topic: {topic}. Supported topics: {self.topics}")

        logger.info(f"Starting stream processing for topic: {topic}")

        try:
            # Read from Kafka
            df = (
                self.spark.readStream.format("kafka")
                .option("kafka.bootstrap.servers", self.config.kafka_bootstrap_servers)
                .option("subscribe", topic)
                .option("startingOffsets", self.config.kafka_starting_offsets)
                .load()
            )

            # Parse JSON and apply schema
            parsed_df = df.select(
                from_json(col("value").cast("string"), self.schemas[topic]).alias("data"),
                col("timestamp").alias("kafka_timestamp"),
            ).select("data.*", "kafka_timestamp")

            # Validate data quality
            validated_df = self.validate_data(parsed_df, topic)

            # Add processing metadata
            enriched_df = validated_df.withColumn(
                "processing_time", current_timestamp()
            ).withColumn("date_partition", date_format(col("timestamp"), "yyyy-MM-dd"))

            # Write to Hudi with DELETE support
            query = (
                enriched_df.writeStream.format("hudi")
                .option("hoodie.table.name", f"{topic}_table")
                .option("hoodie.datasource.write.recordkey.field", self._get_record_key(topic))
                .option("hoodie.datasource.write.partitionpath.field", "date_partition")
                .option("hoodie.datasource.write.table.name", f"{topic}_table")
                .option("hoodie.datasource.write.operation", self._get_operation_type(topic))
                .option("hoodie.datasource.write.precombine.field", "timestamp")
                .option(
                    "hoodie.datasource.write.payload.class",
                    "org.apache.hudi.common.model.DefaultHoodieRecordPayload",
                )
                .option("hoodie.upsert.shuffle.parallelism", str(self.config.shuffle_parallelism))
                .option("hoodie.insert.shuffle.parallelism", str(self.config.shuffle_parallelism))
                .option("hoodie.delete.shuffle.parallelism", str(self.config.shuffle_parallelism))
                .option("hoodie.table.type", self.config.hudi_table_type)
                .option("hoodie.index.type", self.config.hudi_index_type)
                .option("hoodie.compact.inline", "true")
                .option("hoodie.compact.inline.max.delta.commits", "5")
                .option("hoodie.cleaner.policy", "KEEP_LATEST_COMMITS")
                .option("hoodie.cleaner.commits.retained", "10")
                .option("hoodie.metadata.enable", "true")
                .option("path", self.config.get_s3_path(topic))
                .option("checkpointLocation", self.config.get_checkpoint_path(topic))
                .trigger(processingTime=self.config.processing_time)
                .start()
            )

            logger.info(f"Successfully started streaming query for topic: {topic}")
            return query

        except Exception as e:
            logger.error(f"Failed to process stream for topic {topic}: {e}", exc_info=True)
            return None

    def _get_record_key(self, topic: str) -> str:
        """Get the record key field for each topic.

        Args:
            topic: Kafka topic name

        Returns:
            str: Record key field name for the topic
        """
        key_mapping = {
            "user_events": "user_id",
            "transactions": "transaction_id",
            "sensor_data": "sensor_id",
            "log_events": "service",
            "bulk_upload": "batch_id",
        }
        return key_mapping.get(topic, "timestamp")

    def setup_s3_bucket(self) -> bool:
        """Setup S3 bucket for data storage with retry logic.

        Returns:
            bool: True if bucket setup successful, False otherwise
        """
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                s3_client = boto3.client(
                    "s3",
                    endpoint_url=self.config.s3_endpoint,
                    aws_access_key_id=self.config.aws_access_key_id,
                    aws_secret_access_key=self.config.aws_secret_access_key,
                    region_name=self.config.aws_region,
                )

                bucket_name = self.config.s3_bucket

                try:
                    s3_client.create_bucket(Bucket=bucket_name)
                    logger.info(f"Created S3 bucket: {bucket_name}")
                    return True
                except Exception as e:
                    if "BucketAlreadyExists" in str(e) or "BucketAlreadyOwnedByYou" in str(e):
                        logger.info(f"S3 bucket {bucket_name} already exists")
                        return True
                    else:
                        raise e

            except Exception as e:
                logger.error(
                    f"Attempt {attempt + 1}/{max_retries} - Failed to setup S3 bucket: {e}"
                )
                if attempt < max_retries - 1:
                    import time

                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to setup S3 bucket after all retries")
                    return False

        return False

    def run_pipeline(self):
        """Run the complete streaming pipeline with error handling."""
        logger.info("Starting Data Pipeline Processor...")

        try:
            # Setup infrastructure
            if not self.setup_s3_bucket():
                logger.error("Failed to setup S3 bucket. Exiting...")
                return

            # Start streaming for all topics
            queries = []
            for topic in self.topics:
                try:
                    query = self.process_stream(topic)
                    if query:
                        queries.append(query)
                        logger.info(f"Successfully started processing stream for {topic}")
                    else:
                        logger.warning(
                            f"Failed to start stream for {topic}, continuing with other topics"
                        )
                except Exception as e:
                    logger.error(f"Error starting stream for {topic}: {e}", exc_info=True)
                    continue

            if not queries:
                logger.error("No streaming queries started successfully. Exiting...")
                return

            logger.info(f"Successfully started {len(queries)}/{len(self.topics)} streaming queries")

            # Wait for all streams to terminate
            try:
                for query in queries:
                    query.awaitTermination()
            except KeyboardInterrupt:
                logger.info("Received shutdown signal. Stopping streaming pipeline...")
                for query in queries:
                    try:
                        query.stop()
                        logger.info(f"Stopped query: {query.name}")
                    except Exception as e:
                        logger.error(f"Error stopping query: {e}")
                self.spark.stop()
                logger.info("Pipeline shutdown complete")

        except Exception as e:
            logger.error(f"Fatal error in pipeline: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    processor = DataPipelineProcessor()
    processor.run_pipeline()
