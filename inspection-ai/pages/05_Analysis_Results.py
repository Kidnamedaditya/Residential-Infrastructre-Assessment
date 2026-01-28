import streamlit as st
import pandas as pd
from utils.db import run_query
from utils.ui import load_custom_css, header, require_login, card, render_sidebar

st.set_page_config(page_title="Analysis Results", page_icon="📈", layout="wide")
load_custom_css()
require_login()
render_sidebar()

if 'current_property_id' not in st.session_state:
    st.warning("Please select a property first.")
    st.stop()

prop_id = st.session_state.current_property_id

# Fetch Data
summary_df = run_query(f"""
    SELECT * FROM PROPERTY_INSPECTION_SUMMARY WHERE property_id = '{prop_id}'
""")

score_df = run_query(f"""
    SELECT * FROM PROPERTY_RISK_SCORES WHERE property_id = '{prop_id}'
""")

rooms_df = run_query(f"""
    SELECT * FROM ROOM_RISK_SCORES WHERE property_id = '{prop_id}'
""")

findings_df = run_query(f"""
    SELECT f.*, r.room_name 
    FROM INSPECTION_FINDINGS f 
    JOIN ROOMS r ON f.room_id = r.room_id 
    WHERE f.property_id = '{prop_id}' 
    ORDER BY f.severity
""")

# Fetch Inspector Info
inspector_df = run_query(f"""
    SELECT ir.report_id, ir.inspector_id, u.full_name as inspector_name, u.user_id as inspector_user_id
    FROM INSPECTOR_REPORTS ir
    JOIN INSPECTOR_PROFILES ip ON ir.inspector_id = ip.inspector_id
    JOIN USERS u ON ip.user_id = u.user_id
    WHERE ir.property_id = '{prop_id}'
    LIMIT 1
""")

if summary_df.empty:
    st.info("No inspection data available yet.")
    st.stop()

summary = summary_df.iloc[0]
score = score_df.iloc[0]
inspector_info = inspector_df.iloc[0] if not inspector_df.empty else None

header(f"Report: {summary['property_name']}")
if inspector_info:
    st.markdown(f"**Inspected By:** 👨‍🔧 {inspector_info['inspector_name']}")

# Top Metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Risk Score", f"{score['property_risk_score']:.0f}/100")
with col2:
    st.metric("Risk Rating", score['risk_rating'])
with col3:
    st.metric("Critical Issues", score['critical_findings'])
with col4:
    st.metric("Total Findings", score['total_findings'])

st.divider()

st.divider()

# Document Analysis
docs_df = run_query(f"SELECT * FROM INSPECTION_DOCUMENTS WHERE property_id = '{prop_id}'")

if not docs_df.empty:
    st.subheader("📄 Technical Document Analysis")
    for _, doc in docs_df.iterrows():
        with st.expander(f"Report: {doc['filename']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.write("**AI Summary:**")
                st.write(doc['ai_summary'])
            with c2:
                st.write("**Suggestions:**")
                st.write(doc['ai_suggestions'])
            
            if st.button("View Extracted Text", key=f"v_{doc['doc_id']}"):
                st.text_area("Content", doc['extracted_text'], height=200)

st.divider()

# Executive Summary
st.subheader("📝 Executive Summary")
risk_rating = summary['risk_rating']
color = "red" if "CRITICAL" in risk_rating else "orange" if "HIGH" in risk_rating else "green"

st.markdown(f"""
<div style="padding: 20px; border-left: 5px solid {color}; background: rgba(255,255,255,0.05);">
    <h3 style="margin-top:0">{risk_rating}</h3>
    <p>{summary['executive_summary']}</p>
</div>
""", unsafe_allow_html=True)

# Recommended Actions
st.subheader("✅ Recommended Actions")
actions = summary['recommended_actions'].split('. ')
for act in actions:
    if act.strip():
        st.info(act.strip())

# Room Breakdown
st.subheader("🏠 Room Analysis")
if not rooms_df.empty:
    for _, room in rooms_df.iterrows():
        with st.expander(f"{room['room_name']} - {room['risk_category']} ({room['risk_score']:.0f})"):
            # Show findings for this room
            room_findings = findings_df[findings_df['room_id'] == room['room_id']]
            if not room_findings.empty:
                for _, f in room_findings.iterrows():
                    st.markdown(f"**[{f['severity']}] {f['finding_category']}**: {f['finding_description']}")
            else:
                st.caption("No issues found.")

# Findings List
st.subheader("🔍 Detailed Findings")
st.dataframe(findings_df[['room_name', 'finding_category', 'severity', 'finding_description', 'confidence_score']], use_container_width=True)

# Actions
st.divider()

# Rating Section (Only for Property Owner)
if st.session_state.user_type == 'normal_user' and inspector_info:
    st.subheader("⭐ Rate Inspector Service")
    with st.expander("Leave a Rating & Review"):
        with st.form("rating_form"):
            user_rating = st.slider("Rating (1-5)", 1, 5, 5)
            user_feedback = st.text_area("Feedback")
            
            if st.form_submit_button("Submit Rating"):
                from utils.db import execute_statement
                import uuid
                
                rid = f"RAT-{str(uuid.uuid4())[:8]}"
                
                # save rating
                execute_statement(f"""
                    INSERT INTO INSPECTION_RATINGS (rating_id, report_id, user_id, inspector_id, rating_score, feedback)
                    VALUES ('{rid}', '{inspector_info['report_id']}', '{st.session_state.user_id}', '{inspector_info['inspector_id']}', {user_rating}, '{user_feedback}')
                """)
                
                # update inspector profile average
                # Note: This is a simple update, in prod use a trigger or smarter recalc
                execute_statement(f"""
                    UPDATE INSPECTOR_PROFILES 
                    SET rating = (SELECT AVG(rating_score) FROM INSPECTION_RATINGS WHERE inspector_id = '{inspector_info['inspector_id']}'),
                        total_inspections = total_inspections + 1
                    WHERE inspector_id = '{inspector_info['inspector_id']}'
                """)
                
                st.success("Thank you for your feedback!")

st.divider()
c1, c2 = st.columns(2)
with c1:
    st.download_button("📥 Download PDF Report", "Report Content Placeholder", "report.pdf")
with c2:
    if st.button("⬅️ Back to Dashboard"):
        st.switch_page("pages/02_User_Dashboard.py")
