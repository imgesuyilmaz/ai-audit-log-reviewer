
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

        # Combine fields for NLP
        df['combined_text'] = combine_fields(df, mapping)

        # TF-IDF vectorization (text → numbers)
        tfidf = TfidfVectorizer(max_features=500)
        X = tfidf.fit_transform(df['combined_text'])

        # Isolation Forest for anomaly detection
        model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        preds = model.fit_predict(X)
        df['AI_Anomaly'] = preds

        # Show detected anomalies
        anomalies = df[df['AI_Anomaly'] == -1]
        st.subheader("⚠️ AI-Detected Anomalies")
        if not anomalies.empty:
            st.dataframe(anomalies.head(10))
            st.warning(f"{len(anomalies)} anomalies detected out of {len(df)} entries.")
        else:
            st.success("✅ No anomalies detected.")

        # Summary Report
        st.subheader("📄 Summary Report")
        summary_text = f"AI detected {len(anomalies)} anomalies out of {len(df)} records.\n"
        for field, col in mapping.items():
            summary_text += f"- {field} mapped to column `{col}`\n"
        st.text_area("Compliance Summary", summary_text.strip(), height=200)

    except Exception as e:
        st.error(f"❌ Error reading or processing file: {e}")
