#!/usr/bin/env python3
"""
Real DuckDB Web UI - Downloads S3 files and queries locally
"""

from flask import Flask, render_template_string, request, jsonify
import duckdb
import boto3
import os
import subprocess
from pathlib import Path

app = Flask(__name__)

# Create data directory
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)


def download_s3_files():
    """Download Parquet files from LocalStack S3"""
    try:
        # Download all parquet files from S3
        cmd = [
            "aws",
            "--endpoint-url=http://localhost:4566",
            "s3",
            "sync",
            "s3://data-pipeline-bucket/hudi-tables/",
            str(DATA_DIR),
            "--exclude",
            "*",
            "--include",
            "*.parquet",
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False


def execute_query(query):
    """Execute DuckDB query on local files"""
    try:
        conn = duckdb.connect()
        result = conn.execute(query).fetchall()
        columns = [desc[0] for desc in conn.description] if conn.description else []
        conn.close()

        return {"success": True, "columns": columns, "data": result, "row_count": len(result)}
    except Exception as e:
        error_msg = str(e)
        # Handle "No files found" error gracefully
        if "No files found that match the pattern" in error_msg:
            return {
                "success": True,
                "columns": [],
                "data": [],
                "row_count": 0,
                "message": "No data files found for this topic yet",
            }
        return {"success": False, "error": error_msg, "columns": [], "data": [], "row_count": 0}


def get_table_stats():
    """Get file counts for each topic"""
    stats = {}
    topics = ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"]

    for topic in topics:
        topic_dir = DATA_DIR / topic
        if topic_dir.exists():
            parquet_files = list(topic_dir.rglob("*.parquet"))
            stats[topic] = len(parquet_files)
        else:
            stats[topic] = 0

    return stats


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Real DuckDB Query Interface</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .header { text-align: center; margin-bottom: 20px; color: #007cba; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-number { font-size: 24px; font-weight: bold; color: #007cba; }
        button { padding: 10px 15px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
        button:hover { background: #0056b3; }
        textarea { width: 100%; height: 100px; margin: 10px 0; font-family: monospace; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #007cba; color: white; }
        .success { background: #d4edda; color: #155724; padding: 10px; border-radius: 4px; margin: 10px 0; }
        .error { background: #f8d7da; color: #721c24; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦆 Real DuckDB Query Interface</h1>
            <p>Query your actual pipeline data</p>
        </div>

        <button onclick="downloadFiles()">📥 Download Latest Data from S3</button>
        <button onclick="refreshStats()">🔄 Refresh Stats</button>

        <div class="stats">
            {% for topic, count in stats.items() %}
            <div class="stat-card">
                <div class="stat-number">{{ count }}</div>
                <div>{{ topic.replace('_', ' ').title() }} Files</div>
            </div>
            {% endfor %}
        </div>

        <h3>Quick Queries</h3>
        <button onclick="runQuery('SELECT COUNT(*) as files FROM glob(\\'./data/**/*.parquet\\')')">Count All Files</button>
        <button onclick="runQuery('SELECT DISTINCT * FROM read_parquet(\\'./data/user_events/**/*.parquet\\') ORDER BY timestamp DESC LIMIT 10')">User Events</button>
        <button onclick="runQuery('SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY _hoodie_commit_time DESC) as rn FROM read_parquet(\\'./data/transactions/**/*.parquet\\')) WHERE rn = 1 ORDER BY timestamp DESC LIMIT 10')">Transactions</button>
        <button onclick="runQuery('SELECT DISTINCT * FROM read_parquet(\\'./data/sensor_data/**/*.parquet\\') ORDER BY timestamp DESC LIMIT 10')">Sensor Data</button>
        <button onclick="runQuery('SELECT DISTINCT * FROM read_parquet(\\'./data/log_events/**/*.parquet\\') ORDER BY timestamp DESC LIMIT 10')">Log Events</button>
        <button onclick="runQuery('SELECT DISTINCT * FROM read_parquet(\\'./data/bulk_upload/**/*.parquet\\') ORDER BY timestamp DESC LIMIT 10')">Bulk Upload</button>

        <h3>Custom Query</h3>
        <textarea id="queryInput" placeholder="Enter SQL query...">SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY _hoodie_commit_time DESC) as rn FROM read_parquet('./data/transactions/**/*.parquet')) WHERE rn = 1 ORDER BY timestamp DESC LIMIT 5;</textarea>
        <br>
        <button onclick="runCustomQuery()">Execute Query</button>
        <button onclick="clearResults()">Clear</button>

        <div id="results"></div>
    </div>

    <script>
        function downloadFiles() {
            document.getElementById('results').innerHTML = '<div class="success">Downloading files from S3...</div>';
            fetch('/download', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('results').innerHTML = '<div class="success">Files downloaded successfully!</div>';
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        document.getElementById('results').innerHTML = '<div class="error">Download failed: ' + data.error + '</div>';
                    }
                });
        }

        function runQuery(query) {
            document.getElementById('queryInput').value = query;
            executeQuery(query);
        }

        function runCustomQuery() {
            const query = document.getElementById('queryInput').value.trim();
            if (query) executeQuery(query);
        }

        function executeQuery(query) {
            document.getElementById('results').innerHTML = '<div class="success">Executing query...</div>';
            
            fetch('/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query: query})
            })
            .then(response => response.json())
            .then(data => displayResults(data, query));
        }

        function displayResults(data, query) {
            let html = '<h3>Results</h3>';
            html += '<div style="background: #f8f9fa; padding: 10px; margin: 10px 0;"><strong>Query:</strong> ' + query + '</div>';

            if (!data.success) {
                html += '<div class="error">Error: ' + data.error + '</div>';
            } else if (data.row_count === 0) {
                const message = data.message || 'No results found';
                html += '<div class="success">' + message + '</div>';
            } else {
                html += '<table><thead><tr>';
                data.columns.forEach(col => html += '<th>' + col + '</th>');
                html += '</tr></thead><tbody>';
                data.data.forEach(row => {
                    html += '<tr>';
                    row.forEach(cell => html += '<td>' + (cell || 'NULL') + '</td>');
                    html += '</tr>';
                });
                html += '</tbody></table>';
                html += '<div>' + data.row_count + ' rows returned</div>';
            }

            document.getElementById('results').innerHTML = html;
        }

        function refreshStats() { location.reload(); }
        function clearResults() { document.getElementById('results').innerHTML = ''; }
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    stats = get_table_stats()
    return render_template_string(HTML_TEMPLATE, stats=stats)


@app.route("/download", methods=["POST"])
def download():
    success = download_s3_files()
    return jsonify({"success": success, "error": "Failed to download" if not success else None})


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json()
    query = data.get("query", "")
    result = execute_query(query)
    return jsonify(result)


if __name__ == "__main__":
    print("🦆 Starting Real DuckDB UI...")
    print("🌐 Access at: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
