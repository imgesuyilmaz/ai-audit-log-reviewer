
import streamlit as st
import pandas as pd
import difflib
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer

st.set_page_config(page_title="AI Audit Log Reviewer (Flexible)", layout="wide")

st.title("🛡️ Adaptive AI Audit Log Reviewer")
st.write("Upload any format of audit trail (CSV) and let the app auto-map fields and analyze anomalies using TF-IDF + Isolation Forest.")

# Auto-column mapping using fuzzy logic
def auto_map_columns(columns, expected_fields):
    mapping = {}
    for expected in expected_fields:
        closest = difflib.get_close_matches(expected.lower(), [col.lower() for col in columns], n=1, cutoff=0.6)
        if closest:
            match = next(col for col in columns if col.lower() == closest[0])
            mapping[expected] = match
        else:
            mapping[expected] = None
    return mapping

# Combine mapped fields to form a single text column
def combine_fields(df, mapping):
    fields = [v for v in mapping.values() if v is not None]
    if not fields:
        return df.astype(str).agg(' '.join, axis=1)
    return df[fields].astype(str).agg(' '.join, axis=1)

# Explain anomaly logic
def explain_anomaly(row):
    message = row['combined_text'].lower()
    reasons = []

    if 'override' in message:
        reasons.append("manual override")
    if 'alarm' in message or 'fault' in message:
        reasons.append("system alarm or fault")
    if 'shutdown' in message:
        reasons.append("unexpected shutdown")
    if 'deviation' in message:
        reasons.append("procedure deviation")
    if 'emergency' in message:
        reasons.append("emergency condition")

    if 'Hour' in row and pd.notnull(row['Hour']):
        if row['Hour'] < 6 or row['Hour'] > 20:
            reasons.append("outside standard hours")

    if not reasons:
        reasons.append("unusual pattern detected")

    return ", ".join(reasons)

# Upload file
uploaded_file = st.file_uploader("📂 Upload Audit Log File (.csv)", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.subheader("🔍 Raw Log Preview")
        st.dataframe(df.head(10))

        # Auto-map columns
        expected_fields = ['Timestamp', 'User', 'EventType', 'Message']
        mapping = auto_map_columns(df.columns, expected_fields)

        st.markdown("### 🔁 Auto-Mapped Columns")
        for k, v in mapping.items():
            st.write(f"**{k}** → `{v if v else 'Not Found'}`")

        # Add Hour column if Timestamp is present
        if mapping.get('Timestamp') and mapping['Timestamp'] in df.columns:
            df['Hour'] = pd.to_datetime(df[mapping['Timestamp']], errors='coerce').dt.hour

        # Combine fields for NLP
        df['combined_text'] = combine_fields(df, mapping)

        # TF-IDF vectorization (text → numbers)
        tfidf = TfidfVectorizer(max_features=500)
        X = tfidf.fit_transform(df['combined_text'])

        # Isolation Forest for anomaly detection
        model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        preds = model.fit_predict(X)
        df['AI_Anomaly'] = preds

        # Filter and explain anomalies
        anomalies = df[df['AI_Anomaly'] == -1].copy()
        anomalies['AnomalyReason'] = anomalies.apply(explain_anomaly, axis=1)

        # Show detected anomalies
        st.subheader("⚠️ AI-Detected Anomalies")
        if not anomalies.empty:
            cols_to_show = ['AnomalyReason']
            for col in [mapping.get('Timestamp'), mapping.get('EventType'), mapping.get('User')]:
                if col in anomalies.columns:
                    cols_to_show.insert(0, col)
            st.dataframe(anomalies[cols_to_show].head(10))
            st.warning(f"{len(anomalies)} anomalies detected out of {len(df)} entries.")
        else:
            st.success("✅ No anomalies detected.")

        # Summary Report
        st.subheader("📄 Summary Report")
        summary_lines = [f"AI detected {len(anomalies)} anomalies out of {len(df)} records."]
        for _, row in anomalies.iterrows():
            timestamp = row.get(mapping.get('Timestamp'), 'unknown time')
            reason = row.get('AnomalyReason', 'unexplained anomaly')
            summary_lines.append(f"- {timestamp}: {reason}")
        summary_text = "\n".join(summary_lines)
        st.text_area("Compliance Summary", summary_text.strip(), height=200)

    except Exception as e:
        st.error(f"❌ Error reading or processing file: {e}")
