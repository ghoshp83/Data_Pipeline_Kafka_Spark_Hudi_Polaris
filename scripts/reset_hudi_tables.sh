#!/bin/bash

echo "🔄 Resetting Hudi Tables and Starting Fresh..."

# Stop any running Spark jobs (user needs to do this manually)
echo "⚠️  Please stop any running Spark streaming jobs (Ctrl+C) before continuing"
read -p "Press Enter when Spark jobs are stopped..."

# Clear Hudi tables from S3 (LocalStack)
echo "🗑️  Clearing Hudi tables from S3..."
docker exec localstack aws --endpoint-url=http://localhost:4566 s3 rm s3://hudi-tables/ --recursive 2>/dev/null || true

# Recreate the bucket
echo "📦 Recreating S3 bucket..."
docker exec localstack aws --endpoint-url=http://localhost:4566 s3 rb s3://hudi-tables --force 2>/dev/null || true
docker exec localstack aws --endpoint-url=http://localhost:4566 s3 mb s3://hudi-tables

# Clear Spark checkpoints
echo "🧹 Clearing Spark checkpoints..."
rm -rf /tmp/spark-streaming-checkpoints/ 2>/dev/null || true
rm -rf checkpoints/ 2>/dev/null || true

# Reset Kafka consumer group offsets (optional)
echo "🔄 Resetting Kafka consumer offsets..."
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group spark-streaming-group --reset-offsets --to-earliest --all-topics --execute 2>/dev/null || true

echo "✅ Reset complete! You can now restart your Spark streaming job:"
echo "   python src/streaming/spark_streaming_processor.py"