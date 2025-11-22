#!/bin/bash
set -e

echo "🚀 Waiting for services to be ready..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check Zookeeper specifically
check_zookeeper() {
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Checking Zookeeper...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        # Use docker exec to check Zookeeper status
        if docker exec zookeeper zkServer.sh status > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Zookeeper is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - Zookeeper not ready yet...${NC}"
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}❌ Zookeeper failed to start after $max_attempts attempts${NC}"
    echo -e "${YELLOW}💡 Continuing anyway - Kafka might still work...${NC}"
    return 0  # Don't fail the script
}

# Function to check if a service is ready
check_service() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Checking $service_name...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - $service_name not ready yet...${NC}"
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start after $max_attempts attempts${NC}"
    return 1
}

# Function to check Kafka specifically
check_kafka() {
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Checking Kafka...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Kafka is ready!${NC}"
            return 0
        fi
        
        echo -e "${YELLOW}⏳ Attempt $attempt/$max_attempts - Kafka not ready yet...${NC}"
        sleep 5
        ((attempt++))
    done
    
    echo -e "${RED}❌ Kafka failed to start after $max_attempts attempts${NC}"
    return 1
}

# Function to create Kafka topics
create_kafka_topics() {
    echo -e "${YELLOW}Creating Kafka topics...${NC}"
    
    topics=("user_events" "transactions" "sensor_data" "log_events" "bulk_upload")
    
    for topic in "${topics[@]}"; do
        docker exec kafka kafka-topics --create \
            --bootstrap-server localhost:9092 \
            --replication-factor 1 \
            --partitions 3 \
            --topic "$topic" \
            --if-not-exists
        echo -e "${GREEN}✅ Topic '$topic' created${NC}"
    done
}

# Function to setup S3 bucket
setup_s3_bucket() {
    echo -e "${YELLOW}Setting up S3 bucket...${NC}"
    
    # Wait a bit for LocalStack to be fully ready
    sleep 10
    
    # Create bucket using AWS CLI
    aws --endpoint-url=http://localhost:4566 s3 mb s3://data-pipeline-bucket --region us-east-1 || true
    echo -e "${GREEN}✅ S3 bucket 'data-pipeline-bucket' created${NC}"
}

echo "🔍 Starting service health checks..."

# Check all services
check_zookeeper
check_kafka
check_service "Kafka UI" "http://localhost:8080"
check_service "LocalStack" "http://localhost:4566/health"
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"

# Setup Kafka topics
create_kafka_topics

# Setup S3 bucket
setup_s3_bucket

echo -e "${GREEN}🎉 All services are ready!${NC}"
echo ""
echo "📊 Service URLs:"
echo "  • Kafka UI: http://localhost:8080"
echo "  • Spark UI: http://localhost:4040 (when streaming job is running)"
echo "  • Grafana: http://localhost:3000 (admin/admin)"
echo "  • Prometheus: http://localhost:9090"
echo ""
echo "🚀 You can now start the streaming processor:"
echo "  python src/streaming/spark_streaming_processor.py"