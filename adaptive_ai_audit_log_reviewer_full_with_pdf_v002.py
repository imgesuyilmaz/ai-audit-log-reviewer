
import streamlit as st
import pandas as pd
import difflib
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer

st.set_page_config(page_title="AI Audit Log Reviewer (Flexible)", layout="wide")

st.title("🛡️ Adaptive AI Audit Log Reviewer")
st.write("Upload any format of audit trail (CSV) and let the app auto-map fields and analyze anomalies using TF-IDF + Isolation Forest.")

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

def combine_fields(df, mapping):
    fields = [v for v in mapping.values() if v is not None]
    if not fields:
        return df.astype(str).agg(' '.join, axis=1)
    return df[fields].astype(str).agg(' '.join, axis=1)

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

uploaded_file = st.file_uploader("📂 Upload Audit Log File (.csv)", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        st.subheader("🔍 Raw Log Preview")
        st.dataframe(df.head(10))

        expected_fields = ['Timestamp', 'User', 'EventType', 'Message']
        mapping = auto_map_columns(df.columns, expected_fields)

        st.markdown("### 🔁 Auto-Mapped Columns")
        for k, v in mapping.items():
            st.write(f"**{k}** → `{v if v else 'Not Found'}`")

        if mapping.get('Timestamp') and mapping['Timestamp'] in df.columns:
            df['Hour'] = pd.to_datetime(df[mapping['Timestamp']], errors='coerce').dt.hour

        df['combined_text'] = combine_fields(df, mapping)

        tfidf = TfidfVectorizer(max_features=500)
        X = tfidf.fit_transform(df['combined_text'])

        model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        preds = model.fit_predict(X)
        df['AI_Anomaly'] = preds

        anomalies = df[df['AI_Anomaly'] == -1].copy()
        anomalies['AnomalyReason'] = anomalies.apply(explain_anomaly, axis=1)

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

        st.subheader("📄 Summary Report")
        summary_lines = [f"AI detected {len(anomalies)} anomalies out of {len(df)} records."]
        for _, row in anomalies.iterrows():
            timestamp = row.get(mapping.get('Timestamp'), 'unknown time')
            reason = row.get('AnomalyReason', 'unexplained anomaly')
            summary_lines.append(f"- {timestamp}: {reason}")
        summary_text = "\n".join(summary_lines)
        st.text_area("Compliance Summary", summary_text.strip(), height=200)

        # PDF Export
        from fpdf import FPDF
        from io import BytesIO

        st.subheader("🧾 Export Report as PDF")
        if st.button("Download PDF Report"):
            try:
                class PDF(FPDF):
                    def header(self):
                        self.set_font("Arial", "B", 12)
                        self.cell(0, 10, "AI Audit Log Reviewer Report", 0, 1, "C")

                    def chapter_title(self, title):
                        self.set_font("Arial", "B", 11)
                        self.cell(0, 10, title, 0, 1, "L")
                        self.ln(1)

                    def chapter_body(self, text):
                        self.set_font("Arial", "", 10)
                        self.multi_cell(0, 10, text)
                        self.ln()

                pdf = PDF()
                pdf.add_page()
                pdf.chapter_title("Compliance Summary")
                pdf.chapter_body(summary_text)

                pdf.chapter_title("Top Anomalies")
                for _, row in anomalies.head(10).iterrows():
                    ts = row.get(mapping.get('Timestamp'), 'unknown')
                    ev = row.get(mapping.get('EventType'), '')
                    usr = row.get(mapping.get('User'), '')
                    reason = row.get("AnomalyReason", "unknown reason")
                    line = f"- {ts} | {usr} | {ev} | {reason}"
                    pdf.chapter_body(line)

                pdf_data = pdf.output(dest='S').encode('latin-1')  # Convert to bytes
                st.download_button("📄 Download PDF", data=pdf_data, file_name="audit_log_report.pdf", mime="application/pdf")

                pdf_buffer.seek(0)

                st.download_button("📄 Download PDF", data=pdf_buffer, file_name="audit_log_report.pdf", mime="application/pdf")
                st.success("PDF report generated successfully!")

            except Exception as e:
                st.error(f"❌ Failed to generate PDF: {e}")

    except Exception as e:
        st.error(f"❌ Error reading or processing file: {e}")
