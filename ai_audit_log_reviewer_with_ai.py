
import streamlit as st
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from datetime import datetime

st.set_page_config(page_title="AI Audit Log Reviewer", layout="wide")

st.title("🛡️ AI-Powered Audit Log Reviewer")
st.write("Upload a system audit log (.csv) to review and analyze compliance anomalies using AI-based detection.")

uploaded_file = st.file_uploader("📂 Upload CSV File", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.subheader("🔍 Raw Audit Log Preview")
        st.dataframe(df.head(20))

        # Normalize timestamps
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')

        # Combine relevant fields into a single text field
        df['combined_text'] = df.astype(str).agg(' '.join, axis=1)

        # TF-IDF vectorization of combined log entries
        vectorizer = TfidfVectorizer(max_features=300)
        X = vectorizer.fit_transform(df['combined_text'])

        # Isolation Forest for unsupervised anomaly detection
        model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        preds = model.fit_predict(X)
        df['Anomaly'] = preds

        # Filter anomalies
        anomaly_df = df[df['Anomaly'] == -1]

        # Display anomalies
        st.subheader("⚠️ AI-Detected Anomalies")
        if not anomaly_df.empty:
            st.dataframe(anomaly_df[['Timestamp', 'EventType', 'User', 'Message'] if all(c in anomaly_df.columns for c in ['EventType', 'User', 'Message']) else anomaly_df.columns.tolist()])
            st.warning(f"Detected {len(anomaly_df)} anomalous log entries using AI.")
        else:
            st.success("✅ No anomalies detected by the AI model.")

        # Compliance summary
        st.subheader("📄 Compliance Summary")
        summary_text = f"AI detected {len(anomaly_df)} anomalies out of {len(df)} total records." if not anomaly_df.empty else "No anomalies detected."
        st.text_area("Summary", summary_text, height=150)

    except Exception as e:
        st.error(f"Error processing file: {e}")
