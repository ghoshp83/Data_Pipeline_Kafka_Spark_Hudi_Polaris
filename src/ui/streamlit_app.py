#!/usr/bin/env python3
"""
Streamlit UI for the Data Pipeline.
Provides interface to send data and monitor the pipeline.
"""

import streamlit as st
import json
import pandas as pd
from datetime import datetime
from kafka import KafkaProducer
import uuid
import plotly.express as px

from typing import Dict, Any

# Page config
st.set_page_config(
    page_title="Data Pipeline Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)


class StreamlitDataPipeline:
    def __init__(self):
        self.producer = self._get_kafka_producer()

    @st.cache_resource
    def _get_kafka_producer(_self):
        """Create Kafka producer with caching."""
        try:
            return KafkaProducer(
                bootstrap_servers=["localhost:9092"],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
            )
        except Exception as e:
            st.error(f"Failed to connect to Kafka: {e}")
            return None

    def send_to_kafka(self, topic: str, data: Dict[str, Any], key: str = None):
        """Send data to Kafka topic."""
        if not self.producer:
            st.error("Kafka producer not available")
            return False

        try:
            self.producer.send(topic, value=data, key=key)
            self.producer.flush()
            return True
        except Exception as e:
            st.error(f"Failed to send data: {e}")
            return False


def main():
    st.title("🚀 Data Pipeline Dashboard")
    st.markdown("**Real-time Kafka-Spark-Hudi-Polaris Data Pipeline**")

    pipeline = StreamlitDataPipeline()

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Data Input", "Pipeline Status", "Monitoring"])

    if page == "Data Input":
        show_data_input_page(pipeline)
    elif page == "Pipeline Status":
        show_pipeline_status_page()
    elif page == "Monitoring":
        show_monitoring_page()


def show_data_input_page(pipeline):
    """Show data input interface."""
    st.header("📊 Data Input Interface")

    # Topic selection
    topic = st.selectbox(
        "Select Data Topic",
        ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"],
    )

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Send data to: {topic}")

        if topic == "user_events":
            show_user_events_form(pipeline)
        elif topic == "transactions":
            show_transactions_form(pipeline)
        elif topic == "sensor_data":
            show_sensor_data_form(pipeline)
        elif topic == "log_events":
            show_log_events_form(pipeline)
        elif topic == "bulk_upload":
            show_bulk_upload_form(pipeline)

    with col2:
        st.subheader("Quick Actions")

        if st.button("🎲 Send Random Data"):
            data = generate_random_data(topic)
            if pipeline.send_to_kafka(topic, data):
                st.success(f"✅ Sent random data to {topic}")
                st.json(data)

        if st.button("🔄 Send 10 Random Records"):
            success_count = 0
            for i in range(10):
                data = generate_random_data(topic)
                if pipeline.send_to_kafka(topic, data):
                    success_count += 1
            st.success(f"✅ Sent {success_count}/10 records to {topic}")


def show_user_events_form(pipeline):
    """Show user events input form."""
    # Initialize session state for form values
    if "ue_user_id" not in st.session_state:
        st.session_state.ue_user_id = f"user_{uuid.uuid4().hex[:8]}"
    if "ue_event_type" not in st.session_state:
        st.session_state.ue_event_type = "login"
    if "ue_page" not in st.session_state:
        st.session_state.ue_page = "/home"
    if "ue_device" not in st.session_state:
        st.session_state.ue_device = "mobile"

    with st.form("user_events_form"):
        user_id = st.text_input(
            "User ID", value=st.session_state.ue_user_id, help="Enter custom user ID"
        )
        event_type = st.selectbox(
            "Event Type",
            ["login", "logout", "page_view", "click", "purchase", "search"],
            index=["login", "logout", "page_view", "click", "purchase", "search"].index(
                st.session_state.ue_event_type
            ),
        )
        page = st.text_input(
            "Page", value=st.session_state.ue_page, help="Enter the page URL or path"
        )
        device = st.selectbox(
            "Device",
            ["mobile", "desktop", "tablet"],
            index=["mobile", "desktop", "tablet"].index(st.session_state.ue_device),
        )

        submitted = st.form_submit_button("Send User Event")

        if submitted:
            # Update session state with current values
            st.session_state.ue_user_id = user_id
            st.session_state.ue_event_type = event_type
            st.session_state.ue_page = page
            st.session_state.ue_device = device

            # Validate inputs
            if not user_id.strip():
                st.error("User ID cannot be empty")
                return

            data = {
                "user_id": user_id.strip(),
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "properties": json.dumps(
                    {"page": page.strip(), "device": device, "session_id": str(uuid.uuid4())[:8]}
                ),
            }

            if pipeline.send_to_kafka("user_events", data, user_id.strip()):
                st.success("✅ User event sent successfully!")
                st.json(data)
                st.info(
                    "💡 Values preserved. Modify and submit again or click 'New Event' to reset."
                )
            else:
                st.error("❌ Failed to send user event. Check Kafka connection.")

    # Add reset button outside the form
    if st.button("🔄 New Event", key="reset_ue"):
        st.session_state.ue_user_id = f"user_{uuid.uuid4().hex[:8]}"
        st.session_state.ue_event_type = "login"
        st.session_state.ue_page = "/home"
        st.session_state.ue_device = "mobile"
        st.rerun()


def show_transactions_form(pipeline):
    """Show transactions input form."""
    # Initialize session state for form values
    if "trans_user_id" not in st.session_state:
        st.session_state.trans_user_id = f"user_{uuid.uuid4().hex[:8]}"
    if "trans_amount" not in st.session_state:
        st.session_state.trans_amount = 100.0
    if "trans_currency" not in st.session_state:
        st.session_state.trans_currency = "USD"

    with st.form("transactions_form"):
        operation = st.selectbox(
            "Operation", ["INSERT/UPDATE", "DELETE"], help="Select operation type"
        )
        user_id = st.text_input(
            "User ID", value=st.session_state.trans_user_id, help="Enter custom user ID"
        )
        amount = st.number_input(
            "Amount",
            min_value=0.01,
            value=st.session_state.trans_amount,
            step=0.01,
            help="Enter transaction amount",
        )
        currency = st.selectbox(
            "Currency",
            ["USD", "EUR", "GBP", "JPY"],
            index=["USD", "EUR", "GBP", "JPY"].index(st.session_state.trans_currency),
        )

        submitted = st.form_submit_button("Send Transaction")

        if submitted:
            # Update session state with current values
            st.session_state.trans_user_id = user_id
            st.session_state.trans_amount = amount
            st.session_state.trans_currency = currency

            # Validate inputs
            if not user_id.strip():
                st.error("User ID cannot be empty")
                return

            if amount <= 0:
                st.error("Amount must be greater than 0")
                return

            transaction_id = str(uuid.uuid4())
            data = {
                "transaction_id": transaction_id,
                "user_id": user_id.strip(),
                "amount": float(amount),
                "currency": currency,
                "timestamp": datetime.now().isoformat(),
                "_operation": "delete" if operation == "DELETE" else "upsert",
            }

            if pipeline.send_to_kafka("transactions", data, transaction_id):
                st.success("✅ Transaction sent successfully!")
                st.json(data)
                st.info(
                    "💡 Values preserved. Modify and submit again or click 'New Transaction' to reset."
                )
            else:
                st.error("❌ Failed to send transaction. Check Kafka connection.")

    # Add reset button outside the form
    if st.button("🔄 New Transaction", key="reset_trans"):
        st.session_state.trans_user_id = f"user_{uuid.uuid4().hex[:8]}"
        st.session_state.trans_amount = 100.0
        st.session_state.trans_currency = "USD"
        st.rerun()


def show_sensor_data_form(pipeline):
    """Show sensor data input form."""
    with st.form("sensor_data_form"):
        default_sensor_id = f"sensor_{uuid.uuid4().hex[:8]}"
        sensor_id = st.text_input(
            "Sensor ID",
            value=default_sensor_id,
            help="Enter custom sensor ID or use the generated one",
        )
        location = st.selectbox(
            "Location", ["warehouse_a", "warehouse_b", "office_1", "factory_floor", "server_room"]
        )
        temperature = st.slider(
            "Temperature (°C)",
            min_value=-10.0,
            max_value=50.0,
            value=22.0,
            step=0.1,
            help="Adjust temperature reading",
        )
        humidity = st.slider(
            "Humidity (%)",
            min_value=0.0,
            max_value=100.0,
            value=45.0,
            step=0.1,
            help="Adjust humidity reading",
        )

        submitted = st.form_submit_button("Send Sensor Data")

        if submitted:
            # Validate inputs
            if not sensor_id.strip():
                st.error("Sensor ID cannot be empty")
                return

            data = {
                "sensor_id": sensor_id.strip(),
                "location": location,
                "temperature": float(temperature),
                "humidity": float(humidity),
                "timestamp": datetime.now().isoformat(),
            }

            if pipeline.send_to_kafka("sensor_data", data, sensor_id.strip()):
                st.success("✅ Sensor data sent successfully!")
                st.json(data)
                st.info("💡 Form will reset after submission. Modify values above and submit again.")
            else:
                st.error("❌ Failed to send sensor data. Check Kafka connection.")


def show_log_events_form(pipeline):
    """Show log events input form."""
    with st.form("log_events_form"):
        log_level = st.selectbox("Log Level", ["INFO", "WARN", "ERROR", "DEBUG"])
        service = st.selectbox(
            "Service", ["api-gateway", "user-service", "payment-service", "notification-service"]
        )
        message = st.text_area(
            "Message",
            value="Request processed successfully",
            help="Enter custom log message",
            height=100,
        )

        submitted = st.form_submit_button("Send Log Event")

        if submitted:
            # Validate inputs
            if not message.strip():
                st.error("Log message cannot be empty")
                return

            data = {
                "log_level": log_level,
                "message": message.strip(),
                "service": service,
                "timestamp": datetime.now().isoformat(),
            }

            if pipeline.send_to_kafka("log_events", data, service):
                st.success("✅ Log event sent successfully!")
                st.json(data)
                st.info("💡 Form will reset after submission. Modify values above and submit again.")
            else:
                st.error("❌ Failed to send log event. Check Kafka connection.")


def show_bulk_upload_form(pipeline):
    """Show bulk upload input form."""
    with st.form("bulk_upload_form"):
        data_type = st.selectbox(
            "Data Type", ["customer_data", "product_catalog", "inventory_update", "sales_report"]
        )
        record_count = st.number_input(
            "Record Count",
            min_value=1,
            value=1000,
            step=1,
            help="Enter number of records to upload",
        )

        submitted = st.form_submit_button("Send Bulk Upload Event")

        if submitted:
            batch_id = str(uuid.uuid4())
            data = {
                "batch_id": batch_id,
                "record_count": int(record_count),  # Ensure it's an integer
                "data_type": data_type,
                "timestamp": datetime.now().isoformat(),
            }

            if pipeline.send_to_kafka("bulk_upload", data, batch_id):
                st.success("✅ Bulk upload event sent successfully!")
                st.json(data)
                st.info("💡 Form will reset after submission. Modify values above and submit again.")
            else:
                st.error("❌ Failed to send bulk upload event. Check Kafka connection.")


def generate_random_data(topic: str) -> Dict[str, Any]:
    """Generate random data for a topic."""
    import random

    generators = {
        "user_events": lambda: {
            "user_id": f"user_{random.randint(1, 1000)}",
            "event_type": random.choice(["login", "logout", "page_view", "click", "purchase"]),
            "timestamp": datetime.now().isoformat(),
            "properties": json.dumps(
                {
                    "page": f"/page_{random.randint(1, 10)}",
                    "device": random.choice(["mobile", "desktop"]),
                }
            ),
        },
        "transactions": lambda: {
            "transaction_id": str(uuid.uuid4()),
            "user_id": f"user_{random.randint(1, 1000)}",
            "amount": round(random.uniform(10.0, 1000.0), 2),
            "currency": random.choice(["USD", "EUR", "GBP"]),
            "timestamp": datetime.now().isoformat(),
        },
        "sensor_data": lambda: {
            "sensor_id": f"sensor_{random.randint(1, 100)}",
            "location": random.choice(["warehouse_a", "warehouse_b", "office_1"]),
            "temperature": round(random.uniform(15.0, 35.0), 1),
            "humidity": round(random.uniform(30.0, 80.0), 1),
            "timestamp": datetime.now().isoformat(),
        },
        "log_events": lambda: {
            "log_level": random.choice(["INFO", "WARN", "ERROR"]),
            "message": random.choice(["Request processed", "Database error", "Cache miss"]),
            "service": random.choice(["api-gateway", "user-service"]),
            "timestamp": datetime.now().isoformat(),
        },
        "bulk_upload": lambda: {
            "batch_id": str(uuid.uuid4()),
            "record_count": random.randint(100, 10000),
            "data_type": random.choice(["customer_data", "product_catalog"]),
            "timestamp": datetime.now().isoformat(),
        },
    }

    return generators[topic]()


def show_pipeline_status_page():
    """Show pipeline status and health."""
    st.header("🔍 Pipeline Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Kafka Status", "🟢 Running", "Connected")

    with col2:
        st.metric("Spark Status", "🟢 Running", "5 streams active")

    with col3:
        st.metric("Storage Status", "🟢 Healthy", "S3 + Hudi")

    st.subheader("Service URLs")
    services = {
        "Kafka UI": "http://localhost:8080",
        "Spark UI": "http://localhost:4040",
        "Grafana": "http://localhost:3000",
        "Prometheus": "http://localhost:9090",
    }

    for service, url in services.items():
        st.markdown(f"• **{service}**: [{url}]({url})")


def show_monitoring_page():
    """Show monitoring and metrics."""
    st.header("📈 Monitoring Dashboard")

    # Mock data for demonstration
    import numpy as np

    # Generate sample metrics
    times = pd.date_range(start="2024-01-01", periods=24, freq="H")
    throughput = np.random.randint(100, 1000, 24)
    latency = np.random.uniform(10, 100, 24)

    col1, col2 = st.columns(2)

    with col1:
        fig_throughput = px.line(
            x=times,
            y=throughput,
            title="Messages per Hour",
            labels={"x": "Time", "y": "Messages/Hour"},
        )
        st.plotly_chart(fig_throughput, use_container_width=True)

    with col2:
        fig_latency = px.line(
            x=times,
            y=latency,
            title="Processing Latency",
            labels={"x": "Time", "y": "Latency (ms)"},
        )
        st.plotly_chart(fig_latency, use_container_width=True)

    # Topic distribution
    topics = ["user_events", "transactions", "sensor_data", "log_events", "bulk_upload"]
    message_counts = np.random.randint(50, 500, 5)

    fig_pie = px.pie(values=message_counts, names=topics, title="Message Distribution by Topic")
    st.plotly_chart(fig_pie, use_container_width=True)


if __name__ == "__main__":
    main()
