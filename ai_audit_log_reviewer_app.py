
import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="AI Audit Log Reviewer", layout="wide")

st.title("🛡️ AI-Powered Audit Log Reviewer")
st.write("Upload a system audit log (.csv) to review and analyze compliance anomalies.")

uploaded_file = st.file_uploader("📂 Upload CSV File", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.subheader("🔍 Raw Audit Log Preview")
        st.dataframe(df.head(20))

        # Normalize timestamps if present
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        # Add example anomaly detection
        anomalies = []
        if 'EventType' in df.columns:
            # Detect override events
            override_events = df[df['EventType'].str.contains("override", case=False, na=False)]
            if not override_events.empty:
                anomalies.append(f"⚠️ Found {len(override_events)} override events.")

            # Detect logins outside business hours
            if 'Timestamp' in df.columns:
                df['Hour'] = df['Timestamp'].dt.hour
                odd_logins = df[(df['EventType'].str.contains("login", case=False, na=False)) &
                                ((df['Hour'] < 6) | (df['Hour'] > 20))]
                if not odd_logins.empty:
                    anomalies.append(f"⏰ Detected {len(odd_logins)} logins outside business hours.")

        # Display anomaly summary
        st.subheader("⚠️ Anomaly Summary")
        if anomalies:
            for anomaly in anomalies:
                st.warning(anomaly)
        else:
            st.success("✅ No major anomalies detected.")

        # Show compliance summary
        st.subheader("📄 Compliance Summary")
        summary_text = "\n".join(anomalies) if anomalies else "No anomalies detected."
        st.text_area("Summary", summary_text, height=150)

    except Exception as e:
        st.error(f"Failed to process file: {e}")
