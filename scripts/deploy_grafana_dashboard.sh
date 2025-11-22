#!/bin/bash
# Deploy Grafana dashboard for data pipeline monitoring

set -e

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"
DASHBOARD_FILE="monitoring/grafana/dashboard.json"

echo "🚀 Deploying Grafana Dashboard..."

# Check if Grafana is accessible
if ! curl -s -f "${GRAFANA_URL}/api/health" > /dev/null; then
    echo "❌ Error: Grafana is not accessible at ${GRAFANA_URL}"
    echo "Please ensure Grafana is running: docker-compose up -d grafana"
    exit 1
fi

echo "✅ Grafana is accessible"

# Import dashboard
echo "📊 Importing dashboard from ${DASHBOARD_FILE}..."

response=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
    -d @"${DASHBOARD_FILE}" \
    "${GRAFANA_URL}/api/dashboards/db")

if echo "$response" | grep -q '"status":"success"'; then
    echo "✅ Dashboard deployed successfully!"
    echo "🌐 Access dashboard at: ${GRAFANA_URL}/dashboards"
else
    echo "⚠️  Dashboard deployment response: $response"
    echo "Note: Dashboard may already exist or require manual import"
fi

echo ""
echo "📝 Grafana Credentials:"
echo "   URL: ${GRAFANA_URL}"
echo "   Username: ${GRAFANA_USER}"
echo "   Password: ${GRAFANA_PASSWORD}"
