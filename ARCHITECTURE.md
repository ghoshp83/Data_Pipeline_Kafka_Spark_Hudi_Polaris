# System Architecture

## Overview

This document describes the architecture of the Kafka-Spark-Hudi-Polaris data pipeline, including component interactions, data flow, and design decisions.

## Architecture Diagram

```
┌─────────────────┐
│  Data Sources   │
│  (Streamlit UI) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Apache Kafka   │  ← Message Queue
│  (5 Topics)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Spark Stream   │  ← Real-time Processing
│  (PySpark)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Apache Hudi    │  ← ACID Transactions
│  (Data Lake)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  S3 Storage     │  ← Object Storage
│  (LocalStack)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DuckDB Query   │  ← Analytics Layer
│  Interface      │
└─────────────────┘
```

## Components

### 1. Data Input Layer

**Streamlit UI** (`src/ui/streamlit_app.py`)
- Interactive web interface for data input
- Supports 5 data topics
- Real-time data generation
- Form validation

**Python Scripts** (`examples/`, `scripts/`)
- Automated data generation
- Bulk data loading
- Testing utilities

### 2. Message Queue Layer

**Apache Kafka**
- **Topics**: user_events, transactions, sensor_data, log_events, bulk_upload
- **Partitions**: Configurable (default: 1)
- **Replication**: Configurable (default: 1)
- **Retention**: 7 days

**Configuration**:
```yaml
bootstrap.servers: localhost:9092
auto.create.topics.enable: true
```

### 3. Processing Layer

**Spark Streaming** (`src/streaming/spark_streaming_processor.py`)

**Key Features**:
- Real-time stream processing
- Micro-batch processing (10-second intervals)
- Data validation and enrichment
- Error handling and retry logic

**Processing Flow**:
1. Read from Kafka topic
2. Parse JSON with schema validation
3. Validate data quality
4. Add processing metadata
5. Write to Hudi table

**Configuration**:
```python
PipelineConfig:
  - kafka_bootstrap_servers
  - s3_endpoint
  - checkpoint_location
  - processing_time
  - shuffle_parallelism
```

### 4. Storage Layer

**Apache Hudi**
- **Table Type**: COPY_ON_WRITE (COW)
- **Index Type**: BLOOM
- **Operations**: INSERT, UPDATE (upsert), DELETE
- **Partitioning**: By date (yyyy-MM-dd)

**Hudi Configuration**:
```python
hoodie.table.name: {topic}_table
hoodie.datasource.write.operation: upsert
hoodie.datasource.write.precombine.field: timestamp
hoodie.index.type: BLOOM
```

**S3 Storage** (LocalStack)
- Bucket: `data-pipeline-bucket`
- Path: `s3://data-pipeline-bucket/hudi-tables/{topic}/`
- Format: Parquet with Hudi metadata

### 5. Query Layer

**DuckDB UI** (`src/ui/duckdb_ui.py`)
- Flask-based web interface
- Downloads data from S3
- SQL query interface
- Handles Hudi versioning

**Query Pattern**:
```sql
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY {record_key} 
    ORDER BY _hoodie_commit_time DESC
  ) as rn 
  FROM read_parquet('./data/{topic}/**/*.parquet')
) WHERE rn = 1
```

### 6. Monitoring Layer

**Prometheus + Grafana**
- Metrics collection
- Dashboards
- Alerting (configurable)

**Kafka UI**
- Topic monitoring
- Message inspection
- Consumer group tracking

## Data Flow

### 1. Data Ingestion
```
User Input → Streamlit → Kafka Producer → Kafka Topic
```

### 2. Stream Processing
```
Kafka Topic → Spark Streaming → Data Validation → Enrichment
```

### 3. Data Storage
```
Enriched Data → Hudi Writer → S3 Parquet Files
```

### 4. Data Query
```
S3 Files → DuckDB → SQL Query → Results
```

## Design Decisions

### Why Kafka?
- **Decoupling**: Separates data producers from consumers
- **Scalability**: Horizontal scaling with partitions
- **Reliability**: Message persistence and replication
- **Real-time**: Low-latency message delivery

### Why Spark Streaming?
- **Unified API**: Batch and streaming with same code
- **Fault Tolerance**: Checkpointing and recovery
- **Scalability**: Distributed processing
- **Integration**: Native Kafka and Hudi support

### Why Apache Hudi?
- **ACID Transactions**: Data consistency guarantees
- **Upserts**: Efficient updates and deletes
- **Time Travel**: Query historical data
- **Incremental Processing**: Only process changes

### Why LocalStack?
- **Local Development**: No AWS costs
- **Testing**: Isolated environment
- **Compatibility**: S3-compatible API

### Why DuckDB?
- **Embedded**: No separate database server
- **Fast**: Columnar storage and vectorized execution
- **SQL**: Standard SQL interface
- **Parquet**: Native Parquet support

## Scaling Considerations

### Horizontal Scaling

**Kafka**:
- Increase partitions per topic
- Add more brokers
- Configure replication factor

**Spark**:
- Increase executor count
- Adjust parallelism settings
- Use cluster mode (YARN/K8s)

**Storage**:
- Use production S3 (not LocalStack)
- Enable S3 versioning
- Configure lifecycle policies

### Vertical Scaling

**Spark**:
```python
spark.executor.memory: 4g → 8g
spark.driver.memory: 2g → 4g
spark.sql.shuffle.partitions: 200 → 400
```

**Kafka**:
```yaml
num.network.threads: 3 → 8
num.io.threads: 8 → 16
```

## Performance Tuning

### Spark Optimization
```python
# Enable Adaptive Query Execution
spark.sql.adaptive.enabled: true

# Optimize shuffle
spark.sql.shuffle.partitions: 200
spark.shuffle.compress: true

# Memory management
spark.memory.fraction: 0.6
spark.memory.storageFraction: 0.5
```

### Hudi Optimization
```python
# Compaction
hoodie.compact.inline: true
hoodie.compact.inline.max.delta.commits: 5

# Cleaning
hoodie.cleaner.policy: KEEP_LATEST_COMMITS
hoodie.cleaner.commits.retained: 10

# Indexing
hoodie.index.type: BLOOM
hoodie.bloom.index.parallelism: 100
```

### Kafka Optimization
```yaml
# Producer
compression.type: snappy
batch.size: 16384
linger.ms: 10

# Consumer
fetch.min.bytes: 1024
fetch.max.wait.ms: 500
```

## Security Considerations

### Production Deployment

**Kafka**:
- Enable SSL/TLS encryption
- Configure SASL authentication
- Set up ACLs for topics

**S3**:
- Use IAM roles (not access keys)
- Enable bucket encryption
- Configure bucket policies

**Spark**:
- Enable Spark authentication
- Use encrypted shuffle
- Configure network encryption

## Monitoring and Observability

### Metrics to Monitor

**Kafka**:
- Messages per second
- Consumer lag
- Partition distribution

**Spark**:
- Processing time per batch
- Records processed per second
- Failed batches

**Hudi**:
- Table size growth
- Compaction frequency
- Query latency

**System**:
- CPU usage
- Memory usage
- Disk I/O
- Network throughput

### Alerting Rules

```yaml
# High consumer lag
kafka_consumer_lag > 10000

# Slow processing
spark_batch_duration > 30s

# High error rate
error_rate > 5%

# Storage growth
storage_growth_rate > 100GB/day
```

## Disaster Recovery

### Backup Strategy
- Kafka: Enable topic replication
- S3: Enable versioning and cross-region replication
- Checkpoints: Regular backup of Spark checkpoints

### Recovery Procedures
1. Kafka failure: Switch to replica broker
2. Spark failure: Restart from last checkpoint
3. S3 failure: Restore from backup/replica

## Future Enhancements

### Short Term
- Add data quality monitoring
- Implement dead letter queues
- Add more comprehensive tests
- Enhance error notifications

### Long Term
- Kubernetes deployment
- Multi-region support
- Machine learning integration
- Real-time dashboards

## References

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Streaming Guide](https://spark.apache.org/docs/latest/streaming-programming-guide.html)
- [Apache Hudi Documentation](https://hudi.apache.org/docs/overview)
- [DuckDB Documentation](https://duckdb.org/docs/)
