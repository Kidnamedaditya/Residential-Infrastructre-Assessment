import streamlit as st
from utils.db import run_query
from utils.ui import load_custom_css, header, require_login, render_sidebar

st.set_page_config(page_title="Property Search", page_icon="🔍", layout="wide")
load_custom_css()
require_login()
render_sidebar()

header("Search Properties")

query = st.text_input("Enter House/Unit Number or Address", placeholder="e.g. 301")

if query:
    results = run_query(f"""
        SELECT property_id, property_name, address, house_number, report_visibility, owner_user_id
        FROM PROPERTIES
        WHERE house_number ILIKE '%{query}%' OR address ILIKE '%{query}%'
    """)
    
    if results.empty:
        st.warning("No properties found.")
    else:
        st.subheader(f"Found {len(results)} properties")
        for _, p in results.iterrows():
            with st.container():
                st.markdown(f"### {p['property_name']}")
                st.write(p['address'])
                
                
                # Access Control Logic
                has_access = False
                if p['report_visibility'] == 'public':
                    has_access = True
                elif p['owner_user_id'] == st.session_state.user_id:
                    has_access = True
                
                # Check DB for approved access
                if not has_access:
                     acc_check = run_query(f"""
                        SELECT status FROM ACCESS_REQUESTS 
                        WHERE property_id = '{p['property_id']}' 
                        AND requester_user_id = '{st.session_state.user_id}'
                     """)
                     if not acc_check.empty and acc_check.iloc[0]['status'] == 'approved':
                         has_access = True
                
                if has_access:
                    if st.button("View Report", key=p['property_id']):
                        st.session_state.current_property_id = p['property_id']
                        st.switch_page("pages/05_Analysis_Results.py")
                else:
                    st.info("🔒 Private Report")
                    # Check for pending
                    pending_check = run_query(f"""
                        SELECT status FROM ACCESS_REQUESTS 
                        WHERE property_id = '{p['property_id']}' 
                        AND requester_user_id = '{st.session_state.user_id}'
                        AND status = 'pending'
                    """)
                    
                    if not pending_check.empty:
                        st.warning("⏳ Access Request Pending")
                    else:
                        if st.button("Request Access", key=f"req_{p['property_id']}"):
                            from utils.db import execute_statement
                            import uuid
                            rid = f"REQ-{str(uuid.uuid4())[:8]}"
                            execute_statement(f"""
                                INSERT INTO ACCESS_REQUESTS (request_id, property_id, requester_user_id, owner_user_id, status)
                                VALUES ('{rid}', '{p['property_id']}', '{st.session_state.user_id}', '{p['owner_user_id']}', 'pending')
                            """)
                            st.success("Request sent to owner.")
                            st.rerun()
                
                st.divider()
