# 📊 Monitoring Quick Start Guide

Quick reference for testing monitoring locally with Prometheus and Grafana.

---

## 🚀 5-Minute Monitoring Test

### Step 1: Start Infrastructure
```bash
# Start all services
docker-compose up -d

# Wait for services to be ready
bash scripts/wait-for-services.sh

# Verify monitoring services are running
docker ps | grep -E "prometheus|grafana"
```

### Step 2: Deploy Grafana Dashboard
```bash
# Automated deployment
bash scripts/deploy_grafana_dashboard.sh

# OR manually import:
# 1. Open http://localhost:3000 (admin/admin)
# 2. Click "+" → Import
# 3. Upload monitoring/grafana/dashboard.json
```

### Step 3: Start Data Pipeline
```bash
# Terminal 1: Start Spark streaming
python src/streaming/spark_streaming_processor.py

# Terminal 2: Generate test data
python scripts/benchmark_pipeline.py --messages 5000
```

### Step 4: View Metrics
```bash
# Open Grafana dashboard
open http://localhost:3000

# Navigate to: Dashboards → Data Pipeline Monitoring
# Watch metrics update in real-time!
```

---

## 📈 What You'll See

### Grafana Dashboard (http://localhost:3000)
- ✅ **Kafka Messages/sec** - Real-time ingestion rate
- ✅ **Spark Processing Latency** - Batch processing time
- ✅ **Records Processed** - Per-topic throughput
- ✅ **Error Rate** - Processing failures
- ✅ **Consumer Lag** - Pipeline health
- ✅ **S3 Write Throughput** - Storage performance

### Prometheus (http://localhost:9090)
- ✅ Raw metrics and queries
- ✅ Target health status
- ✅ Metric exploration

---

## 🧪 Testing Scenarios

### Scenario 1: Normal Load
```bash
# Generate 1000 messages
python scripts/benchmark_pipeline.py --messages 1000

# Expected metrics:
# - Kafka: ~100-200 msg/sec
# - Spark: ~50-100ms latency
# - Consumer lag: < 50
```

### Scenario 2: High Load
```bash
# Generate 10000 messages
python scripts/benchmark_pipeline.py --messages 10000

# Expected metrics:
# - Kafka: ~500-1000 msg/sec
# - Spark: ~100-200ms latency
# - Consumer lag: < 200
```

### Scenario 3: Continuous Streaming
```bash
# Run continuous data generation
python scripts/send_sample_data.py

# Watch metrics stabilize over time
# Monitor for 5-10 minutes
```

---

## 🔍 Metric Queries (Prometheus)

Access http://localhost:9090 and try these queries:

### Kafka Metrics
```promql
# Message rate by topic
rate(kafka_server_brokertopicmetrics_messagesin_total[5m])

# Total messages
kafka_server_brokertopicmetrics_messagesin_total
```

### Spark Metrics
```promql
# Processing time
spark_streaming_batch_processing_time_ms

# Records processed
rate(records_processed_total[5m])
```

### System Health
```promql
# Check all targets are up
up

# Error rate
rate(processing_errors_total[5m])
```

---

## 🎯 Monitoring Checklist

Before testing:
- [ ] Docker services running (`docker ps`)
- [ ] Prometheus accessible (http://localhost:9090)
- [ ] Grafana accessible (http://localhost:3000)
- [ ] Dashboard imported in Grafana

During testing:
- [ ] Spark streaming job running
- [ ] Data being sent to Kafka
- [ ] Metrics updating in Grafana (10s refresh)
- [ ] No errors in Prometheus targets

After testing:
- [ ] All 6 dashboard panels showing data
- [ ] Consumer lag staying low
- [ ] No processing errors
- [ ] Throughput matches expected load

---

## 🐛 Troubleshooting

### No Metrics Showing
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# Check Grafana logs
docker logs grafana

# Restart services
docker-compose restart prometheus grafana
```

### Dashboard Not Loading
```bash
# Re-deploy dashboard
bash scripts/deploy_grafana_dashboard.sh

# Check Grafana data source
# Go to Configuration → Data Sources
# Verify Prometheus URL: http://prometheus:9090
```

### Metrics Delayed
- Wait 30 seconds (Prometheus scrape interval: 15s)
- Check Spark streaming is running
- Verify data is being sent to Kafka

---

## 📊 Dashboard Panels Explained

### Panel 1: Kafka Messages Per Second
- **What**: Message ingestion rate
- **Why**: Track data flow into pipeline
- **Alert if**: Rate drops to 0 unexpectedly

### Panel 2: Spark Processing Latency
- **What**: Time to process each batch
- **Why**: Identify performance bottlenecks
- **Alert if**: Latency > 5 seconds

### Panel 3: Records Processed by Topic
- **What**: Processing rate per topic
- **Why**: Compare topic activity
- **Alert if**: One topic stops processing

### Panel 4: Error Rate
- **What**: Processing failures over time
- **Why**: Detect issues early
- **Alert if**: Error rate > 1%

### Panel 5: Kafka Consumer Lag
- **What**: How far behind consumers are
- **Why**: Ensure pipeline keeps up
- **Alert if**: Lag > 1000 messages

### Panel 6: S3 Write Throughput
- **What**: Data write performance
- **Why**: Monitor storage layer
- **Alert if**: Throughput drops to 0

---

## 🎓 Learning Resources

### Prometheus
- Query language: https://prometheus.io/docs/prometheus/latest/querying/basics/
- Best practices: https://prometheus.io/docs/practices/naming/

### Grafana
- Dashboard guide: https://grafana.com/docs/grafana/latest/dashboards/
- Alerting: https://grafana.com/docs/grafana/latest/alerting/

---

## 🚀 Next Steps

1. **Customize Dashboard**: Add your own panels
2. **Set Up Alerts**: Configure email/Slack notifications
3. **Export Metrics**: Send to CloudWatch/Datadog
4. **Add Custom Metrics**: Instrument your code

See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for production monitoring setup.

---

**Quick Links:**
- 📊 Grafana: http://localhost:3000 (admin/admin)
- 📈 Prometheus: http://localhost:9090
- 🔄 Kafka UI: http://localhost:8080
- ⚡ Spark UI: http://localhost:4040 (when running)
