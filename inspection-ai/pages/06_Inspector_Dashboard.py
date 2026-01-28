import streamlit as st
from utils.db import run_query
from utils.ui import load_custom_css, header, require_login, render_sidebar

st.set_page_config(page_title="Inspector Dashboard", page_icon="👷", layout="wide")
load_custom_css()
require_login()
render_sidebar()

if st.session_state.user_type != 'inspector':
    st.error("Access Restricted: Inspectors Only")
    st.stop()

header(f"Inspector Dashboard: {st.session_state.username}")

# Metrics
try:
    metrics = run_query(f"""
        SELECT 
            total_inspections,
            rating,
            years_experience
        FROM INSPECTOR_PROFILES
        WHERE user_id = '{st.session_state.user_id}'
    """)
    if not metrics.empty:
        m = metrics.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Inspections", m['total_inspections'])
        c2.metric("Rating", f"{m['rating']} ⭐")
        c3.metric("Experience", f"{m['years_experience']} Years")

    if st.button("➕ Start New Inspection"):
        st.session_state.inspector_mode = True
        st.session_state.inspection_mode = 'single' # Default to single for now, or let them choose
        st.switch_page("pages/03_Start_Inspection.py")
    
    
    st.divider()
    
    tab1, tab2 = st.tabs(["📋 Assignments", "📬 Access Requests"])
    
    with tab1:
        st.subheader("Active Assignments")
    # For demo, show all properties that requested inspection or high risk
        # Show Requested Inspections
        assignments = run_query("""
            SELECT sr.service_id, p.property_id, p.property_name, p.address, sr.status, u.full_name as requester
            FROM INSPECTION_SERVICE_REQUESTS sr
            JOIN PROPERTIES p ON sr.property_id = p.property_id
            JOIN USERS u ON sr.requester_user_id = u.user_id
            WHERE sr.status = 'requested'
        """)
        
        if assignments.empty:
            st.info("No active inspection requests.")
        else:
            for _, task in assignments.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"**{task['property_name']}**")
                    c1.caption(f"{task['address']} (Req by: {task['requester']})")
                    c2.info(f"Status: {task['status'].title()}")
                    if c3.button("Inspect", key=task['service_id']):
                         st.session_state.current_property_id = task['property_id']
                         st.session_state.current_property_name = task['property_name']
                         st.session_state.inspector_mode = True
                         st.session_state.current_service_id = task['service_id'] # Track service request
                         st.switch_page("pages/03_Start_Inspection.py")
                    st.divider()
                
    with tab2:
        st.subheader("Pending Access Requests")
        
        reqs = run_query(f"""
            SELECT ar.request_id, p.property_name, u.full_name as requester_name, ar.request_date, ar.status
            FROM ACCESS_REQUESTS ar
            JOIN PROPERTIES p ON ar.property_id = p.property_id
            JOIN USERS u ON ar.requester_user_id = u.user_id
            WHERE ar.owner_user_id = '{st.session_state.user_id}' AND ar.status = 'pending'
        """)
        
        if reqs.empty:
            st.info("No pending requests.")
        else:
            from utils.db import execute_statement
            for _, r in reqs.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.write(f"**{r['requester_name']}** requested access to **{r['property_name']}**")
                    c1.caption(f"Date: {r['request_date']}")
                    
                    if c2.button("Approve", key=f"app_{r['request_id']}", type="primary"):
                        execute_statement(f"UPDATE ACCESS_REQUESTS SET status = 'approved' WHERE request_id = '{r['request_id']}'")
                        st.toast("Request Approved")
                        st.rerun()
                        
                    if c3.button("Reject", key=f"rej_{r['request_id']}"):
                        execute_statement(f"UPDATE ACCESS_REQUESTS SET status = 'rejected' WHERE request_id = '{r['request_id']}'")
                        st.toast("Request Rejected")
                        st.rerun()
                    st.divider()

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
