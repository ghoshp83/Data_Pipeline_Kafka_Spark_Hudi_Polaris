# Local Setup Guide

Complete guide to set up and run the Kafka-Spark-Hudi-Polaris data pipeline locally.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step 1: Python Environment Setup](#step-1-python-environment-setup)
3. [Step 2: Kafka Infrastructure Setup](#step-2-kafka-infrastructure-setup)
4. [Step 3: Spark Setup](#step-3-spark-setup)
5. [Step 4: LocalStack S3 & Hudi Setup](#step-4-localstack-s3--hudi-setup)
6. [Step 5: Data Input Methods](#step-5-data-input-methods)
7. [Step 6: Monitoring with Prometheus & Grafana](#step-6-monitoring-with-prometheus--grafana)
8. [Step 7: Query Data with DuckDB](#step-7-query-data-with-duckdb)
9. [Step 8: Snowflake Integration (Optional)](#step-8-snowflake-integration-optional)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Python 3.9-3.11** (Python 3.12 has compatibility issues)
- **Docker & Docker Compose**
- **Java 11+** (for Spark)
- **8GB+ RAM** recommended

### Quick Install (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv openjdk-11-jdk docker.io docker-compose
sudo usermod -aG docker $USER
# Logout and login for Docker group to take effect
```

---

## Step 1: Python Environment Setup

### 1.1 Clone Repository
```bash
git clone <repository-url>
cd Data-Pipeline-with-Kafka-Spark-Hudi-Polaris
```

### 1.2 Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

### 1.3 Install Python Dependencies
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**For Python 3.12 users:**
```bash
# Install numpy first, then pyspark
pip install numpy==1.26.4
pip install pyspark==3.5.0
pip install -r requirements.txt
```

---

## Step 2: Kafka Infrastructure Setup

### 2.1 Start Kafka and Related Services
```bash
# Start all infrastructure (Kafka, Zookeeper, LocalStack, Monitoring)
docker-compose up -d

# Wait for services to be ready (2-3 minutes)
bash scripts/wait-for-services.sh
```

### 2.2 Verify Kafka is Running
```bash
# Check running containers
docker ps

# You should see:
# - kafka
# - zookeeper
# - localstack
# - prometheus
# - grafana
```

### 2.3 Access Kafka UI
- **Kafka UI**: http://localhost:8080
- View topics, messages, and consumer groups

### 2.4 Create Kafka Topics (Optional - Auto-created)
Topics are automatically created when data is sent, but you can create them manually:
```bash
docker exec kafka kafka-topics --create --topic user_events --bootstrap-server localhost:9092
docker exec kafka kafka-topics --create --topic transactions --bootstrap-server localhost:9092
docker exec kafka kafka-topics --create --topic sensor_data --bootstrap-server localhost:9092
docker exec kafka kafka-topics --create --topic log_events --bootstrap-server localhost:9092
docker exec kafka kafka-topics --create --topic bulk_upload --bootstrap-server localhost:9092
```

---

## Step 3: Spark Setup

### 3.1 Install Apache Spark
```bash
# Download Spark 3.5.0
wget https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz
tar -xzf spark-3.5.0-bin-hadoop3.tgz
sudo mv spark-3.5.0-bin-hadoop3 /opt/spark
sudo chown -R $USER:$USER /opt/spark
```

### 3.2 Download Required JARs

**Kafka Connectors:**
```bash
wget https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/3.5.0/spark-sql-kafka-0-10_2.12-3.5.0.jar -P /opt/spark/jars/
wget https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar -P /opt/spark/jars/
wget https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/3.5.0/spark-token-provider-kafka-0-10_2.12-3.5.0.jar -P /opt/spark/jars/
wget https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar -P /opt/spark/jars/
```

**Hudi Connector:**
```bash
wget https://repo1.maven.org/maven2/org/apache/hudi/hudi-spark3-bundle_2.12/0.14.0/hudi-spark3-bundle_2.12-0.14.0.jar -P /opt/spark/jars/
```

### 3.3 Set Environment Variables
```bash
echo 'export SPARK_HOME=/opt/spark' >> ~/.bashrc
echo 'export PATH=$SPARK_HOME/bin:$PATH' >> ~/.bashrc
echo 'export PYTHONPATH=$SPARK_HOME/python:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc
```

### 3.4 Start Spark Streaming Processor
```bash
# This will listen to Kafka and write to Hudi tables
python src/streaming/spark_streaming_processor.py
```

**Keep this terminal running** - It processes data in real-time.

**Access Spark UI**: http://localhost:4040 (when streaming job is running)

---

## Step 4: LocalStack S3 & Hudi Setup

### 4.1 Verify LocalStack is Running
```bash
# LocalStack should already be running from Step 2
docker ps | grep localstack
```

### 4.2 Configure AWS CLI for LocalStack
```bash
# Install AWS CLI if not already installed
pip install awscli

# Configure for LocalStack
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

### 4.3 Verify S3 Bucket
```bash
# The bucket is auto-created by the Spark streaming processor
aws --endpoint-url=http://localhost:4566 s3 ls

# You should see: data-pipeline-bucket
```

### 4.4 Check Hudi Tables
```bash
# List Hudi tables in S3
aws --endpoint-url=http://localhost:4566 s3 ls s3://data-pipeline-bucket/hudi-tables/

# You should see directories for each topic:
# - user_events/
# - transactions/
# - sensor_data/
# - log_events/
# - bulk_upload/
```

---

## Step 5: Data Input Methods

Now that Kafka and Spark are running, you can send data using either method:

### Option A: Streamlit UI (Recommended)

**Start Streamlit App:**
```bash
# In a new terminal (keep Spark streaming running)
source .venv/bin/activate
streamlit run src/ui/streamlit_app.py
```

**Access UI**: http://localhost:8501

**Features:**
- Interactive forms for all 5 data topics
- User input preserved across submissions
- Real-time data generation
- Visual feedback on sent messages

**Usage:**
1. Select a data topic (user_events, transactions, etc.)
2. Fill in the form fields
3. Click "Send" button
4. Data is sent to Kafka → Spark → Hudi → S3

### Option B: Python Scripts

**Quick Start Example:**
```bash
python examples/quick_start_example.py
```

**Continuous Data Generation:**
```bash
python scripts/send_sample_data.py
```

**Send Custom Data:**
```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

data = {
    "user_id": "user_123",
    "event_type": "login",
    "timestamp": "2024-01-01T10:00:00",
    "properties": "{\"device\": \"mobile\"}"
}

producer.send('user_events', value=data)
producer.flush()
```

---

## Step 6: Monitoring with Prometheus & Grafana

### 6.1 Access Monitoring Services

Monitoring services are automatically started with `docker-compose up -d`:

- **Prometheus**: http://localhost:9090 - Metrics collection
- **Grafana**: http://localhost:3000 - Visualization dashboards

### 6.2 Login to Grafana

1. Open http://localhost:3000 in your browser
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin`
3. Skip password change (or set a new one)

### 6.3 Deploy Monitoring Dashboard

**Option A: Automated Deployment**
```bash
# Deploy the pre-configured dashboard
bash scripts/deploy_grafana_dashboard.sh
```

**Option B: Manual Import**
1. In Grafana, click **"+"** → **Import**
2. Click **Upload JSON file**
3. Select `monitoring/grafana/dashboard.json`
4. Click **Import**

### 6.4 Configure Prometheus Data Source

If not auto-configured:

1. Go to **Configuration** → **Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://prometheus:9090`
5. Click **Save & Test**

### 6.5 View Real-Time Metrics

Once the dashboard is imported, you'll see 6 panels:

#### Panel 1: Kafka Messages Per Second
- Shows message ingestion rate by topic
- Updates every 10 seconds
- Useful for: Tracking throughput

#### Panel 2: Spark Processing Latency
- Shows batch processing time in milliseconds
- Useful for: Identifying performance bottlenecks

#### Panel 3: Records Processed by Topic
- Shows processing rate per topic
- Useful for: Comparing topic activity

#### Panel 4: Error Rate
- Shows processing errors over time
- Useful for: Detecting issues early

#### Panel 5: Kafka Consumer Lag
- Shows how far behind consumers are
- Useful for: Ensuring pipeline keeps up

#### Panel 6: S3 Write Throughput
- Shows data write performance
- Useful for: Monitoring storage layer

### 6.6 Generate Test Data for Monitoring

To see metrics in action:

**Step 1: Start Spark Streaming** (if not already running)
```bash
python src/streaming/spark_streaming_processor.py
```

**Step 2: Send Test Data**
```bash
# Option A: Quick test with sample data
python examples/quick_start_example.py

# Option B: Continuous data generation
python scripts/send_sample_data.py

# Option C: Performance benchmark (generates load)
python scripts/benchmark_pipeline.py --messages 1000
```

**Step 3: Watch Metrics Update**
1. Open Grafana dashboard: http://localhost:3000
2. Navigate to **Data Pipeline Monitoring** dashboard
3. Watch metrics update in real-time (10-second refresh)

### 6.7 Verify Metrics Collection

**Check Prometheus Targets:**
1. Open http://localhost:9090
2. Go to **Status** → **Targets**
3. Verify all targets are **UP**:
   - Kafka exporter
   - Prometheus itself

**Query Metrics Directly:**
```promql
# In Prometheus UI (http://localhost:9090), try these queries:

# Kafka message rate
rate(kafka_server_brokertopicmetrics_messagesin_total[5m])

# Check if metrics are being collected
up
```

### 6.8 Monitoring Workflow (End-to-End Test)

**Complete monitoring test:**

```bash
# Terminal 1: Start infrastructure
docker-compose up -d
bash scripts/wait-for-services.sh

# Terminal 2: Start Spark streaming
python src/streaming/spark_streaming_processor.py

# Terminal 3: Generate test data
python scripts/benchmark_pipeline.py --messages 5000

# Browser: Open Grafana
# http://localhost:3000
# Watch metrics update in real-time!
```

**What you should see:**
- ✅ Kafka message rate increasing
- ✅ Spark processing latency metrics
- ✅ Records processed counter going up
- ✅ S3 write throughput showing activity
- ✅ Consumer lag staying low (< 100)

### 6.9 Troubleshooting Monitoring

**No metrics showing:**
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Check Grafana can reach Prometheus
docker logs grafana
```

**Dashboard not loading:**
```bash
# Restart Grafana
docker-compose restart grafana

# Re-deploy dashboard
bash scripts/deploy_grafana_dashboard.sh
```

**Metrics delayed:**
- Prometheus scrapes every 15 seconds by default
- Grafana refreshes every 10 seconds
- Allow 30 seconds for metrics to appear

### 6.10 Custom Metrics (Advanced)

To add custom application metrics:

```python
# In your Python code
from prometheus_client import Counter, Histogram, start_http_server

# Define metrics
records_processed = Counter('records_processed_total', 'Total records processed', ['topic'])
processing_time = Histogram('processing_time_seconds', 'Time to process record')

# Start metrics server
start_http_server(8000)

# Increment metrics
records_processed.labels(topic='user_events').inc()
```

Then configure Prometheus to scrape `localhost:8000`.

---

## Step 7: Query Data with DuckDB

### 7.1 Start DuckDB Web UI
```bash
# In a new terminal
python src/ui/duckdb_ui.py
```

**Access UI**: http://localhost:5000

### 7.2 Download Data from S3
1. Click "📥 Download Latest Data from S3" button
2. Wait for files to download to `./data/` directory

### 7.3 Query Data

**Quick Query Buttons:**
- **User Events** - View user interaction data
- **Transactions** - View financial transactions
- **Sensor Data** - View IoT sensor readings
- **Log Events** - View application logs
- **Bulk Upload** - View batch upload records

**Custom SQL Queries:**
```sql
-- View latest transactions (handles Hudi versioning)
SELECT * FROM (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY _hoodie_commit_time DESC) as rn 
  FROM read_parquet('./data/transactions/**/*.parquet')
) WHERE rn = 1 ORDER BY timestamp DESC LIMIT 10;

-- Count records by topic
SELECT COUNT(*) FROM read_parquet('./data/user_events/**/*.parquet');

-- Join transactions with user events
SELECT t.transaction_id, t.amount, u.event_type
FROM read_parquet('./data/transactions/**/*.parquet') t
JOIN read_parquet('./data/user_events/**/*.parquet') u
ON t.user_id = u.user_id;
```

**Note**: The queries use `ROW_NUMBER()` with `_hoodie_commit_time` to handle Hudi's versioning and show only the latest version of each record.

---

## Step 8: Snowflake Integration (Optional)

### 8.1 Prerequisites
- Snowflake account
- AWS S3 bucket (for production, not LocalStack)
- Snowflake credentials

### 8.2 Create Snowflake Database
```sql
-- Create database and schema
CREATE DATABASE data_pipeline;
CREATE SCHEMA data_pipeline.streaming;
USE SCHEMA data_pipeline.streaming;
```

### 8.3 Create External Stage
```sql
-- Create external stage pointing to S3
CREATE STAGE data_pipeline_stage
  URL='s3://your-production-bucket/hudi-tables/'
  CREDENTIALS=(
    AWS_KEY_ID='your-aws-key'
    AWS_SECRET_KEY='your-aws-secret'
  );
```

### 8.4 Create External Tables
```sql
-- User Events Table
CREATE EXTERNAL TABLE user_events (
  user_id STRING,
  event_type STRING,
  timestamp TIMESTAMP,
  properties VARIANT
)
LOCATION=@data_pipeline_stage/user_events/
FILE_FORMAT=(TYPE=PARQUET);

-- Transactions Table
CREATE EXTERNAL TABLE transactions (
  transaction_id STRING,
  user_id STRING,
  amount DECIMAL(10,2),
  currency STRING,
  timestamp TIMESTAMP
)
LOCATION=@data_pipeline_stage/transactions/
FILE_FORMAT=(TYPE=PARQUET);

-- Sensor Data Table
CREATE EXTERNAL TABLE sensor_data (
  sensor_id STRING,
  location STRING,
  temperature FLOAT,
  humidity FLOAT,
  timestamp TIMESTAMP
)
LOCATION=@data_pipeline_stage/sensor_data/
FILE_FORMAT=(TYPE=PARQUET);
```

### 7.5 Query Data in Snowflake
```sql
-- Query user events
SELECT * FROM user_events LIMIT 10;

-- Aggregate transactions
SELECT currency, SUM(amount) as total_amount
FROM transactions
GROUP BY currency;

-- Join tables
SELECT u.user_id, u.event_type, t.amount
FROM user_events u
LEFT JOIN transactions t ON u.user_id = t.user_id;
```

---

## Troubleshooting

### Kafka Issues

**Kafka not starting:**
```bash
docker-compose down
docker-compose up -d
bash scripts/wait-for-services.sh
```

**Check Kafka logs:**
```bash
docker logs kafka
```

**List topics:**
```bash
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Spark Issues

**commons-pool2 error:**
```bash
wget https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar -P /opt/spark/jars/
```

**Spark UI not accessible:**
- Spark UI only runs when streaming job is active
- Check if `spark_streaming_processor.py` is running

**Checkpoint errors:**
```bash
# Clear checkpoints and restart
rm -rf checkpoints/
python src/streaming/spark_streaming_processor.py
```

### Python/Streamlit Issues

**kafka-python import error (Python 3.12):**
```bash
pip uninstall kafka-python
pip install kafka-python-ng
```

**Streamlit form not capturing input:**
- Make sure you're using the latest version of the code
- Forms now use session state to preserve input

### LocalStack/S3 Issues

**Cannot access S3:**
```bash
# Verify LocalStack is running
docker ps | grep localstack

# Test S3 access
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
aws --endpoint-url=http://localhost:4566 s3 ls
```

**Bucket not found:**
```bash
# Create bucket manually
aws --endpoint-url=http://localhost:4566 s3 mb s3://data-pipeline-bucket
```

### DuckDB Issues

**No data showing:**
1. Make sure Spark streaming is running
2. Send data via Streamlit or scripts
3. Click "Download Latest Data from S3" in DuckDB UI
4. Wait for download to complete

**Duplicate records:**
- Use the provided queries with `ROW_NUMBER()` to handle Hudi versioning
- The quick query buttons already include this logic

### Port Conflicts

If ports are already in use, modify `docker-compose.yml`:
- Kafka: 9092
- Kafka UI: 8080
- Grafana: 3000
- Prometheus: 9090
- LocalStack: 4566
- Streamlit: 8501
- DuckDB UI: 5000

---

## Service URLs Summary

| Service | URL | Description |
|---------|-----|-------------|
| Kafka UI | http://localhost:8080 | Monitor Kafka topics and messages |
| Spark UI | http://localhost:4040 | Monitor streaming jobs (when running) |
| Streamlit | http://localhost:8501 | Data input interface |
| DuckDB UI | http://localhost:5000 | Query interface for Hudi data |
| Grafana | http://localhost:3000 | Monitoring dashboards (admin/admin) |
| Prometheus | http://localhost:9090 | Metrics collection |
| LocalStack | http://localhost:4566 | Local AWS S3 endpoint |

---

## Quick Start Summary

```bash
# 1. Setup Python environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Start Kafka infrastructure
docker-compose up -d
bash scripts/wait-for-services.sh

# 3. Start Spark streaming (keep running)
python src/streaming/spark_streaming_processor.py

# 4. Send data (new terminal)
streamlit run src/ui/streamlit_app.py
# OR
python examples/quick_start_example.py

# 5. Query data (new terminal)
python src/ui/duckdb_ui.py
```

---

## Next Steps

1. ✅ Send test data via Streamlit UI
2. ✅ Monitor data flow in Kafka UI
3. ✅ Check Spark UI for processing metrics
4. ✅ Query data with DuckDB UI
5. ✅ Set up Grafana dashboards for monitoring
6. ✅ Integrate with Snowflake for analytics (optional)

---

## Additional Resources

- **Architecture Details**: [ARCHITECTURE.md](ARCHITECTURE.md) - System design and technical decisions
- **Production Deployment**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - AWS setup and production best practices
- **Project Overview**: [README.md](README.md) - Features and quick start guide

---

**Ready for Production?** See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for complete deployment guide.
