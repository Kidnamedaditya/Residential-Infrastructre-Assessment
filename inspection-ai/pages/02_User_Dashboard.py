import streamlit as st
from utils.db import run_query
from utils.ui import load_custom_css, header, require_login, render_sidebar

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
load_custom_css()
require_login()
render_sidebar()

if st.session_state.user_type != 'normal_user' and st.session_state.user_type != 'inspector':
    pass

st.markdown(f"## Welcome, {st.session_state.username}")
st.divider()

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div style="text-align: center; padding: 40px; background: rgba(0, 201, 255, 0.1); border-radius: 15px; border: 1px solid #00C9FF;">
        <h1>🕵️ Self Inspection</h1>
        <p>Analyze your own property or room instantly with AI.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Start New Inspection", use_container_width=True):
         # Navigate to a pre-wizard selection step
         st.session_state.inspection_flow = "select_mode" 
         st.switch_page("pages/03_Start_Inspection.py") # Reusing add property as entry point

with col2:
    st.markdown("""
    <div style="text-align: center; padding: 40px; background: rgba(146, 254, 157, 0.1); border-radius: 15px; border: 1px solid #92FE9D;">
        <h1>🔍 Search Existing</h1>
        <p>Find past reports and public property inspections.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Search Database", use_container_width=True):
        st.switch_page("pages/08_Search.py")

st.divider()

# Request Professional Inspection
st.subheader("👷 Request Professional Inspection")
with st.expander("Need an expert inspector? Request one here."):
    with st.form("req_insp_form"):
        req_name = st.text_input("Property Name (e.g. My Villa)")
        req_addr = st.text_input("Address")
        req_house = st.text_input("House/Unit Number")
        
        if st.form_submit_button("Submit Request"):
            if not req_addr or not req_house:
                st.error("Address and House Number are required.")
            else:
                from utils.db import execute_statement
                import uuid
                
                # Check if property exists for this user
                existing = run_query(f"""
                    SELECT property_id FROM PROPERTIES 
                    WHERE owner_user_id = '{st.session_state.user_id}' 
                    AND (house_number = '{req_house}' OR address = '{req_addr}')
                """)
                
                if not existing.empty:
                    prop_id = existing.iloc[0]['property_id']
                else:
                    # Create new property
                    prop_id = f"PROP-{str(uuid.uuid4())[:8]}"
                    execute_statement(f"""
                        INSERT INTO PROPERTIES (
                            property_id, house_number, property_name, address, 
                            property_type, construction_status, total_rooms, 
                            owner_user_id, report_visibility
                        ) VALUES (
                            '{prop_id}', '{req_house}', '{req_name or req_addr}', '{req_addr}',
                            'residential', 'existing', 1,
                            '{st.session_state.user_id}', 'private'
                        )
                    """)
                
                # Create Service Request
                sid = f"SR-{str(uuid.uuid4())[:8]}"
                execute_statement(f"""
                    INSERT INTO INSPECTION_SERVICE_REQUESTS (service_id, property_id, requester_user_id, status)
                    VALUES ('{sid}', '{prop_id}', '{st.session_state.user_id}', 'requested')
                """)
                st.success("Inspection Request Submitted! An inspector will be assigned soon.")

st.divider()

# Recent Activity / My Properties (Optional but good for history)
st.subheader("🕑 Recent Inspections")
try:
    if st.session_state.user_type == 'normal_user':
        props = run_query(f"""
            SELECT p.property_id, p.property_name, p.address, p.house_number, 
                   prs.risk_rating, prs.property_risk_score
            FROM PROPERTIES p
            LEFT JOIN PROPERTY_RISK_SCORES prs ON p.property_id = prs.property_id
            WHERE p.owner_user_id = '{st.session_state.user_id}'
            ORDER BY p.created_at DESC LIMIT 3
        """)
        
        if props.empty:
            st.caption("No recent inspections found.")
        else:
            for _, prop in props.iterrows():
                with st.container():
                     c1, c2, c3 = st.columns([3, 2, 1])
                     c1.markdown(f"**{prop['property_name']}**")
                     c2.caption(f"{prop['risk_rating'] or 'Pending'}")
                     if c3.button("View", key=prop['property_id']):
                         st.session_state.current_property_id = prop['property_id']
                         st.switch_page("pages/05_Analysis_Results.py")
except:
    pass
