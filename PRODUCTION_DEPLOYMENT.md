# Production Deployment Guide

Complete guide for deploying the Kafka-Spark-Hudi-Polaris data pipeline to production environments.

---

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [AWS Production Setup](#aws-production-setup)
3. [Infrastructure Configuration](#infrastructure-configuration)
4. [Security & Compliance](#security--compliance)
5. [Performance Tuning](#performance-tuning)
6. [Monitoring & Alerting](#monitoring--alerting)
7. [Disaster Recovery](#disaster-recovery)
8. [Cost Optimization](#cost-optimization)
9. [Deployment Steps](#deployment-steps)

---

## Pre-Deployment Checklist

### Infrastructure Requirements
- [ ] AWS account with appropriate permissions
- [ ] VPC with public/private subnets configured
- [ ] Security groups and network ACLs defined
- [ ] IAM roles and policies created
- [ ] SSL/TLS certificates provisioned
- [ ] Domain names and DNS configured

### Application Requirements
- [ ] Code reviewed and tested
- [ ] CI/CD pipeline configured
- [ ] Environment variables documented
- [ ] Secrets stored in AWS Secrets Manager
- [ ] Backup and recovery procedures defined
- [ ] Runbooks created for common issues

### Monitoring Requirements
- [ ] CloudWatch dashboards created
- [ ] Alarms configured for critical metrics
- [ ] Log aggregation set up
- [ ] PagerDuty/OpsGenie integration
- [ ] Data quality monitoring enabled

### Security Requirements
- [ ] Encryption at rest enabled
- [ ] Encryption in transit configured
- [ ] Authentication mechanisms implemented
- [ ] Authorization policies defined
- [ ] Audit logging enabled
- [ ] Vulnerability scanning scheduled

---

## AWS Production Setup

### 1. Amazon MSK (Managed Kafka)

**Create MSK Cluster:**
```bash
aws kafka create-cluster \
  --cluster-name data-pipeline-prod \
  --broker-node-group-info file://broker-config.json \
  --kafka-version 3.4.0 \
  --number-of-broker-nodes 3 \
  --encryption-info "EncryptionAtRest={DataVolumeKMSKeyId=arn:aws:kms:us-east-1:xxx:key/xxx},EncryptionInTransit={ClientBroker=TLS,InCluster=true}" \
  --enhanced-monitoring PER_TOPIC_PER_BROKER
```

**broker-config.json:**
```json
{
  "InstanceType": "kafka.m5.large",
  "ClientSubnets": [
    "subnet-xxx",
    "subnet-yyy",
    "subnet-zzz"
  ],
  "SecurityGroups": ["sg-xxx"],
  "StorageInfo": {
    "EbsStorageInfo": {
      "VolumeSize": 1000
    }
  }
}
```

**Get Bootstrap Servers:**
```bash
aws kafka get-bootstrap-brokers --cluster-arn <cluster-arn>
```

**Update Configuration:**
```bash
export KAFKA_BOOTSTRAP_SERVERS="b-1.datapipeline.xxx.kafka.us-east-1.amazonaws.com:9092"
```

### 2. Amazon S3

**Create Production Bucket:**
```bash
aws s3 mb s3://data-pipeline-prod-bucket --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket data-pipeline-prod-bucket \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket data-pipeline-prod-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Configure lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket data-pipeline-prod-bucket \
  --lifecycle-configuration file://lifecycle.json
```

**lifecycle.json:**
```json
{
  "Rules": [
    {
      "Id": "archive-old-data",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 180,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

### 3. Amazon EMR (Spark)

**Create EMR Cluster:**
```bash
aws emr create-cluster \
  --name "Data Pipeline Spark Cluster" \
  --release-label emr-6.10.0 \
  --applications Name=Spark Name=Hadoop \
  --ec2-attributes KeyName=my-key,InstanceProfile=EMR_EC2_DefaultRole,SubnetId=subnet-xxx \
  --instance-groups InstanceGroupType=MASTER,InstanceCount=1,InstanceType=m5.xlarge \
                    InstanceGroupType=CORE,InstanceCount=2,InstanceType=m5.2xlarge \
  --service-role EMR_DefaultRole \
  --log-uri s3://data-pipeline-prod-bucket/emr-logs/ \
  --configurations file://spark-config.json
```

**spark-config.json:**
```json
[
  {
    "Classification": "spark-defaults",
    "Properties": {
      "spark.executor.memory": "8g",
      "spark.driver.memory": "4g",
      "spark.executor.cores": "4",
      "spark.sql.shuffle.partitions": "400",
      "spark.streaming.backpressure.enabled": "true",
      "spark.streaming.kafka.maxRatePerPartition": "1000"
    }
  }
]
```

**Submit Spark Job:**
```bash
aws emr add-steps \
  --cluster-id j-xxxxx \
  --steps Type=Spark,Name="Streaming Processor",ActionOnFailure=CONTINUE,Args=[--deploy-mode,cluster,--master,yarn,s3://data-pipeline-prod-bucket/code/spark_streaming_processor.py]
```

### 4. IAM Roles and Policies

**EMR EC2 Role Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::data-pipeline-prod-bucket",
        "arn:aws:s3:::data-pipeline-prod-bucket/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kafka:DescribeCluster",
        "kafka:GetBootstrapBrokers"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:xxx:secret:data-pipeline/*"
    }
  ]
}
```

---

## Infrastructure Configuration

### VPC Setup

**Network Architecture:**
```
VPC (10.0.0.0/16)
├── Public Subnet 1 (10.0.1.0/24) - AZ1
├── Public Subnet 2 (10.0.2.0/24) - AZ2
├── Private Subnet 1 (10.0.11.0/24) - AZ1 (MSK, EMR)
├── Private Subnet 2 (10.0.12.0/24) - AZ2 (MSK, EMR)
└── Private Subnet 3 (10.0.13.0/24) - AZ3 (MSK)
```

**Security Groups:**

*MSK Security Group:*
- Inbound: Port 9092 from EMR security group
- Outbound: All traffic

*EMR Security Group:*
- Inbound: Port 22 from bastion host
- Inbound: Port 8088 (YARN UI) from VPN
- Outbound: All traffic

### Environment Variables

**Production .env:**
```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=b-1.datapipeline.xxx.kafka.us-east-1.amazonaws.com:9092
KAFKA_SECURITY_PROTOCOL=SSL
KAFKA_SSL_TRUSTSTORE_LOCATION=/etc/kafka/truststore.jks
KAFKA_SSL_TRUSTSTORE_PASSWORD=<from-secrets-manager>

# S3 Configuration
S3_BUCKET=data-pipeline-prod-bucket
S3_ENDPOINT=https://s3.us-east-1.amazonaws.com
AWS_REGION=us-east-1

# Spark Configuration
SPARK_MASTER=yarn
SPARK_DEPLOY_MODE=cluster
SPARK_EXECUTOR_MEMORY=8g
SPARK_DRIVER_MEMORY=4g

# Hudi Configuration
HUDI_TABLE_TYPE=COPY_ON_WRITE
HUDI_PRECOMBINE_FIELD=timestamp
HUDI_COMPACTION_STRATEGY=org.apache.hudi.table.action.compact.strategy.LogFileSizeBasedCompactionStrategy

# Monitoring
PROMETHEUS_ENDPOINT=https://prometheus.example.com
GRAFANA_ENDPOINT=https://grafana.example.com
CLOUDWATCH_NAMESPACE=DataPipeline/Production
```

---

## Security & Compliance

### 1. Encryption

**At Rest:**
- S3: Server-side encryption with AES-256 or KMS
- MSK: EBS volumes encrypted with KMS
- EMR: EBS volumes encrypted with KMS

**In Transit:**
- MSK: TLS 1.2+ for client-broker communication
- S3: HTTPS only
- Internal: TLS for all service communication

### 2. Authentication & Authorization

**MSK SASL/SCRAM:**
```bash
# Create secret in Secrets Manager
aws secretsmanager create-secret \
  --name AmazonMSK_kafka_credentials \
  --secret-string '{"username":"admin","password":"<strong-password>"}'

# Associate with MSK cluster
aws kafka update-cluster-configuration \
  --cluster-arn <cluster-arn> \
  --configuration-info file://sasl-config.json
```

**IAM Policies:**
- Principle of least privilege
- Separate roles for different services
- Regular access reviews

### 3. Audit Logging

**Enable CloudTrail:**
```bash
aws cloudtrail create-trail \
  --name data-pipeline-audit \
  --s3-bucket-name audit-logs-bucket \
  --is-multi-region-trail
```

**MSK Logging:**
```bash
aws kafka update-monitoring \
  --cluster-arn <cluster-arn> \
  --current-version <version> \
  --logging-info '{
    "BrokerLogs": {
      "CloudWatchLogs": {
        "Enabled": true,
        "LogGroup": "/aws/msk/data-pipeline"
      },
      "S3": {
        "Enabled": true,
        "Bucket": "data-pipeline-logs"
      }
    }
  }'
```

### 4. Compliance

**Data Retention:**
- Kafka: 7 days retention
- S3: Lifecycle policies for archival
- Logs: 90 days in CloudWatch, then S3

**Data Privacy:**
- PII masking in logs
- Encryption for sensitive data
- Access controls and audit trails

---

## Performance Tuning

### 1. Kafka Optimization

**Broker Configuration:**
```properties
# Throughput
num.network.threads=8
num.io.threads=16
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400

# Retention
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000

# Replication
default.replication.factor=3
min.insync.replicas=2
```

**Producer Configuration:**
```python
producer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'acks': 'all',
    'compression.type': 'snappy',
    'batch.size': 32768,
    'linger.ms': 10,
    'buffer.memory': 67108864,
    'max.in.flight.requests.per.connection': 5
}
```

**Consumer Configuration:**
```python
consumer_config = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'spark-streaming-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'max.poll.records': 500,
    'fetch.min.bytes': 1024,
    'fetch.max.wait.ms': 500
}
```

### 2. Spark Optimization

**Executor Configuration:**
```python
spark_config = {
    'spark.executor.instances': '10',
    'spark.executor.cores': '4',
    'spark.executor.memory': '8g',
    'spark.driver.memory': '4g',
    'spark.memory.fraction': '0.8',
    'spark.memory.storageFraction': '0.3'
}
```

**Streaming Configuration:**
```python
streaming_config = {
    'spark.streaming.backpressure.enabled': 'true',
    'spark.streaming.kafka.maxRatePerPartition': '1000',
    'spark.streaming.stopGracefullyOnShutdown': 'true',
    'spark.streaming.receiver.writeAheadLog.enable': 'true'
}
```

**Shuffle Configuration:**
```python
shuffle_config = {
    'spark.sql.shuffle.partitions': '400',
    'spark.shuffle.compress': 'true',
    'spark.shuffle.spill.compress': 'true',
    'spark.io.compression.codec': 'snappy'
}
```

### 3. Hudi Optimization

**Write Configuration:**
```python
hudi_write_config = {
    'hoodie.insert.shuffle.parallelism': '400',
    'hoodie.upsert.shuffle.parallelism': '400',
    'hoodie.bulkinsert.shuffle.parallelism': '400',
    'hoodie.delete.shuffle.parallelism': '400',
    'hoodie.combine.before.insert': 'true',
    'hoodie.combine.before.upsert': 'true'
}
```

**Compaction Configuration:**
```python
hudi_compaction_config = {
    'hoodie.compact.inline': 'false',
    'hoodie.compact.inline.max.delta.commits': '5',
    'hoodie.compact.schedule.inline': 'true',
    'hoodie.compaction.strategy': 'org.apache.hudi.table.action.compact.strategy.LogFileSizeBasedCompactionStrategy',
    'hoodie.compaction.target.io': '512000'
}
```

**Clustering Configuration:**
```python
hudi_clustering_config = {
    'hoodie.clustering.inline': 'true',
    'hoodie.clustering.inline.max.commits': '4',
    'hoodie.clustering.plan.strategy.target.file.max.bytes': '1073741824',
    'hoodie.clustering.plan.strategy.small.file.limit': '629145600'
}
```

### 4. S3 Optimization

**Multipart Upload:**
```python
s3_config = {
    'fs.s3a.multipart.size': '104857600',  # 100MB
    'fs.s3a.multipart.threshold': '209715200',  # 200MB
    'fs.s3a.fast.upload': 'true',
    'fs.s3a.fast.upload.buffer': 'disk'
}
```

**Connection Pooling:**
```python
s3_connection_config = {
    'fs.s3a.connection.maximum': '100',
    'fs.s3a.threads.max': '64',
    'fs.s3a.connection.establish.timeout': '5000',
    'fs.s3a.connection.timeout': '200000'
}
```

---

## Monitoring & Alerting

### 1. CloudWatch Metrics

**Key Metrics to Monitor:**

*Kafka (MSK):*
- `BytesInPerSec` - Incoming data rate
- `BytesOutPerSec` - Outgoing data rate
- `MessagesInPerSec` - Message rate
- `UnderReplicatedPartitions` - Replication health
- `OfflinePartitionsCount` - Availability

*Spark (EMR):*
- `AppsRunning` - Active applications
- `AppsPending` - Queued applications
- `ContainerAllocated` - Resource utilization
- `MemoryAvailableMB` - Available memory
- `YARNMemoryAvailablePercentage` - Memory usage

*Custom Application Metrics:*
- Processing latency
- Records processed per second
- Error rate
- Data quality metrics

### 2. CloudWatch Alarms

**Critical Alarms:**
```bash
# High error rate
aws cloudwatch put-metric-alarm \
  --alarm-name data-pipeline-high-error-rate \
  --alarm-description "Error rate > 5%" \
  --metric-name ErrorRate \
  --namespace DataPipeline/Production \
  --statistic Average \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:xxx:alerts

# Processing lag
aws cloudwatch put-metric-alarm \
  --alarm-name data-pipeline-processing-lag \
  --alarm-description "Processing lag > 5 minutes" \
  --metric-name ProcessingLag \
  --namespace DataPipeline/Production \
  --statistic Average \
  --period 300 \
  --threshold 300 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:us-east-1:xxx:alerts
```

### 3. Grafana Dashboards

**Dashboard Components:**
- Real-time throughput graphs
- Latency percentiles (p50, p95, p99)
- Error rate trends
- Resource utilization
- Data quality metrics

**Import Dashboard:**
```bash
# Use provided dashboard JSON
curl -X POST http://grafana.example.com/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana-dashboard.json
```

### 4. Log Aggregation

**CloudWatch Logs Insights Queries:**

*Error Analysis:*
```
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)
```

*Performance Analysis:*
```
fields @timestamp, processingTime
| stats avg(processingTime), max(processingTime), min(processingTime) by bin(5m)
```

---

## Disaster Recovery

### 1. Backup Strategy

**Kafka:**
- MSK automatic backups enabled
- Topic configuration backed up
- Consumer offsets tracked

**S3:**
- Versioning enabled
- Cross-region replication configured
- Lifecycle policies for archival

**Metadata:**
- Hudi metadata backed up daily
- Schema registry backed up
- Configuration files in version control

### 2. Recovery Procedures

**Kafka Cluster Failure:**
```bash
# 1. Create new MSK cluster
aws kafka create-cluster --cli-input-json file://cluster-config.json

# 2. Restore topic configurations
for topic in user_events transactions sensor_data log_events bulk_upload; do
  aws kafka create-configuration --name $topic-config --kafka-versions "3.4.0"
done

# 3. Update application configuration
export KAFKA_BOOTSTRAP_SERVERS=<new-bootstrap-servers>

# 4. Restart Spark streaming jobs
```

**S3 Data Loss:**
```bash
# Restore from versioned backup
aws s3api list-object-versions --bucket data-pipeline-prod-bucket
aws s3api restore-object --bucket data-pipeline-prod-bucket --key <object-key> --version-id <version-id>

# Or restore from cross-region replica
aws s3 sync s3://data-pipeline-backup-bucket s3://data-pipeline-prod-bucket
```

**Spark Job Failure:**
```bash
# Spark streaming automatically recovers from checkpoints
# Manual restart if needed:
aws emr add-steps --cluster-id j-xxxxx --steps file://spark-step.json
```

### 3. RTO/RPO Targets

**Recovery Time Objective (RTO):**
- Critical services: < 1 hour
- Non-critical services: < 4 hours

**Recovery Point Objective (RPO):**
- Kafka: < 5 minutes (replication lag)
- S3: < 1 hour (versioning + replication)
- Metadata: < 24 hours (daily backups)

### 4. Testing

**Disaster Recovery Drills:**
- Quarterly failover tests
- Annual full disaster recovery simulation
- Document lessons learned
- Update runbooks

---

## Cost Optimization

### 1. Right-Sizing

**MSK:**
- Start with kafka.m5.large
- Monitor CPU and network utilization
- Scale up only when consistently > 70%

**EMR:**
- Use Spot instances for core nodes (60-70% cost savings)
- Reserved instances for master node
- Auto-scaling based on YARN metrics

**S3:**
- Use Intelligent-Tiering for unknown access patterns
- Lifecycle policies to move to cheaper storage classes
- Delete incomplete multipart uploads

### 2. Cost Monitoring

**Set Up Budgets:**
```bash
aws budgets create-budget \
  --account-id <account-id> \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

**Cost Allocation Tags:**
```bash
aws resourcegroupstaggingapi tag-resources \
  --resource-arn-list <resource-arn> \
  --tags Project=DataPipeline,Environment=Production,CostCenter=Engineering
```

### 3. Optimization Tips

- Use compression (Snappy for Kafka, Parquet for S3)
- Batch small files to reduce S3 requests
- Schedule compaction during off-peak hours
- Use S3 Select for query pushdown
- Enable S3 Transfer Acceleration for cross-region

**Estimated Monthly Costs (Medium Scale):**
- MSK (3 kafka.m5.large): ~$600
- EMR (1 m5.xlarge + 2 m5.2xlarge): ~$800
- S3 (10TB storage + requests): ~$250
- Data Transfer: ~$150
- **Total: ~$1,800/month**

---

## Deployment Steps

### Phase 1: Infrastructure Setup (Week 1)

1. **Create VPC and Networking**
   ```bash
   aws cloudformation create-stack --stack-name data-pipeline-vpc --template-body file://vpc-template.yaml
   ```

2. **Deploy MSK Cluster**
   ```bash
   aws kafka create-cluster --cli-input-json file://msk-config.json
   ```

3. **Create S3 Buckets**
   ```bash
   bash scripts/create-s3-buckets.sh
   ```

4. **Set Up IAM Roles**
   ```bash
   aws cloudformation create-stack --stack-name data-pipeline-iam --template-body file://iam-template.yaml
   ```

### Phase 2: Application Deployment (Week 2)

1. **Deploy Spark Application to S3**
   ```bash
   aws s3 cp src/ s3://data-pipeline-prod-bucket/code/ --recursive
   ```

2. **Create EMR Cluster**
   ```bash
   aws emr create-cluster --cli-input-json file://emr-config.json
   ```

3. **Submit Spark Streaming Job**
   ```bash
   aws emr add-steps --cluster-id j-xxxxx --steps file://spark-step.json
   ```

### Phase 3: Monitoring Setup (Week 3)

1. **Configure CloudWatch Alarms**
   ```bash
   bash scripts/create-cloudwatch-alarms.sh
   ```

2. **Deploy Grafana Dashboards**
   ```bash
   bash scripts/deploy-grafana-dashboards.sh
   ```

3. **Set Up Log Aggregation**
   ```bash
   bash scripts/configure-logging.sh
   ```

### Phase 4: Testing & Validation (Week 4)

1. **Run Integration Tests**
   ```bash
   pytest tests/integration/ --env=production
   ```

2. **Load Testing**
   ```bash
   python scripts/load_test.py --duration=1h --rate=1000
   ```

3. **Failover Testing**
   ```bash
   bash scripts/test-failover.sh
   ```

### Phase 5: Go-Live

1. **Gradual Traffic Migration**
   - Start with 10% traffic
   - Monitor for 24 hours
   - Increase to 50% if stable
   - Full cutover after 48 hours

2. **Post-Deployment Monitoring**
   - 24/7 monitoring for first week
   - Daily reviews for first month
   - Weekly reviews thereafter

---

## Production Checklist

### Pre-Launch
- [ ] All infrastructure provisioned
- [ ] Security configurations verified
- [ ] Monitoring and alerting active
- [ ] Backup and recovery tested
- [ ] Load testing completed
- [ ] Runbooks documented
- [ ] Team trained on operations

### Launch Day
- [ ] Traffic migration plan executed
- [ ] Real-time monitoring active
- [ ] On-call team available
- [ ] Rollback plan ready
- [ ] Stakeholders notified

### Post-Launch
- [ ] Performance metrics reviewed
- [ ] Cost analysis completed
- [ ] Incident retrospectives conducted
- [ ] Documentation updated
- [ ] Optimization opportunities identified

---

## Support & Resources

- **AWS Documentation**: https://docs.aws.amazon.com/
- **Apache Kafka**: https://kafka.apache.org/documentation/
- **Apache Spark**: https://spark.apache.org/docs/latest/
- **Apache Hudi**: https://hudi.apache.org/docs/overview
- **Architecture Guide**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Local Setup**: [LOCAL_SETUP.md](LOCAL_SETUP.md)

---

**Need Help?** Contact the platform team or create an issue in the repository.
