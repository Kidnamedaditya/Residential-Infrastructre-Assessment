import streamlit as st
import uuid
import pandas as pd
from utils.db import execute_statement, run_query
from utils.ui import load_custom_css, header, require_login, render_sidebar
from utils.ai import compare_findings_with_report

st.set_page_config(page_title="Inspection Workflow", page_icon="📝", layout="wide")
load_custom_css()
require_login()
render_sidebar()

if 'current_property_id' not in st.session_state:
    st.warning("Select a property first.")
    st.switch_page("pages/06_Inspector_Dashboard.py")

header(f"Inspection Review: {st.session_state.current_property_name}")

# Fetch AI Findings
ai_findings = run_query(f"""
    SELECT * FROM AI_CLASSIFIED_DEFECTS WHERE property_id = '{st.session_state.current_property_id}'
""")

if ai_findings.empty:
    st.info("No AI findings to review. Start by uploading images in the Wizard?")
    if st.button("Go to Upload Wizard"):
        st.switch_page("pages/04_Inspection_Wizard.py")
else:
    # --- CROSS-CHECK SECTION ---
    st.subheader("🤖 Cross-Check Analysis (Report vs AI)")
    
    # 1. Fetch Inspector's Uploaded Report Text
    docs = run_query(f"SELECT extracted_text, filename FROM INSPECTION_DOCUMENTS WHERE property_id = '{st.session_state.current_property_id}' LIMIT 1")
    
    if not docs.empty:
        report_text = docs.iloc[0]['extracted_text']
        filename = docs.iloc[0]['filename']
        
        # 2. Aggregate AI Findings
        ai_text_summary = ""
        for _, f in ai_findings.iterrows():
            ai_text_summary += f"- {f['room_name']}: Detected {f['finding_category']} ({f['finding_description']})\n"
            
        with st.expander(f"Compare with: {filename}", expanded=True):
            if st.button("Run Cross-Check Analysis"):
                with st.spinner("AI is comparing your report with visual findings..."):
                    comparison = compare_findings_with_report(ai_text_summary, report_text)
                    st.session_state.comparison_result = comparison
            
            if 'comparison_result' in st.session_state:
                res = st.session_state.comparison_result
                
                c1, c2, c3 = st.columns([1,2,2])
                c1.metric("Similarity Score", f"{res.get('similarity_score', 0)}%")
                
                with c2:
                    st.success(f"**Matches ({len(res.get('matches', []))}):**")
                    for m in res.get('matches', []):
                        st.caption(f"✅ {m}")
                        
                with c3:
                    st.warning(f"**Discrepancies ({len(res.get('discrepancies', []))}):**")
                    for d in res.get('discrepancies', []):
                        st.caption(f"⚠️ {d}")
                
                st.info(f"**Cross-Check Summary:** {res.get('summary', 'No summary available.')}")

    st.divider()

    st.subheader("Review AI Findings")
    st.write("Compare AI detections with your expert judgment.")
    
    # Store decisions in session state if not already
    if 'decisions' not in st.session_state:
        st.session_state.decisions = {}

    for idx, f in ai_findings.iterrows():
        fid = f['finding_id']
        
        with st.expander(f"{f['room_name']} - {f['finding_description'][:50]}..."):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.caption("AI Assessment")
                st.info(f"Severity: {f['original_severity']}\nConfidence: {f['confidence_score']:.2f}")
                st.write(f"Description: {f['finding_description']}")
            
            with c2:
                st.caption("Inspector Decision")
                decision = st.radio("Action", ["Confirm", "Modify", "Reject"], key=f"d_{fid}", horizontal=True)
                
                notes = st.text_area("Notes", key=f"n_{fid}")
                
                if decision == "Modify":
                    new_sev = st.selectbox("Correct Severity", ["critical", "high", "medium", "low", "ok"], key=f"s_{fid}")

    st.divider()

    # Final Score Calculation
    st.subheader("Final Assessment")
    
    # Fetch current AI Score
    ai_score_df = run_query(f"SELECT property_risk_score FROM PROPERTY_RISK_SCORES WHERE property_id = '{st.session_state.current_property_id}'")
    ai_score = ai_score_df.iloc[0]['property_risk_score'] if not ai_score_df.empty else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("AI Calculated Risk Score", f"{ai_score:.0f}")
    
    with col2:
        manual_score = st.number_input("Your Final Risk Score (0-100)", 0, 100, int(ai_score))
    
    variance = abs(manual_score - ai_score)
    st.caption(f"Variance: {variance:.0f} points")
    
    if variance > 15:
        st.warning("⚠️ High variance detected. Please ensure you have justified your score in the notes.")
    
    summary_text = st.text_area("Executive Summary for Client")
    
    if st.button("Submit Final Report", type="primary"):
        # Save Report
        try:
            report_id = f"REP-{str(uuid.uuid4())[:8]}"
            # Assuming current user uses the first profile found for them or we query it. 
            # For demo, we just use a placeholder inspector ID or query it.
            insp_df = run_query(f"SELECT inspector_id FROM INSPECTOR_PROFILES WHERE user_id = '{st.session_state.user_id}'")
            inspector_id = insp_df.iloc[0]['inspector_id'] if not insp_df.empty else 'UNK'
            
            sql = f"""
            INSERT INTO INSPECTOR_REPORTS (
                report_id, property_id, inspector_id, inspection_date,
                manual_risk_score, ai_risk_score, score_variance,
                final_approved_score, inspector_summary, status
            ) VALUES (
                '{report_id}', '{st.session_state.current_property_id}', '{inspector_id}',
                CURRENT_DATE(), {manual_score}, {ai_score}, {variance},
                {manual_score}, '{summary_text}', 'submitted'
            )
            """
            execute_statement(sql)
            st.success("Report Submitted Successfully!")
            st.balloons()
            
            # Update Property Visibility/Status? 
            # Could set property to 'inspected' or something.
            
        except Exception as e:
            st.error(f"Submission failed: {e}")
