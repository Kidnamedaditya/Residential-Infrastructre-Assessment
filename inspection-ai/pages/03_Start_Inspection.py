import streamlit as st
import uuid
from utils.db import execute_statement
from utils.ui import load_custom_css, header, require_login, render_sidebar

st.set_page_config(page_title="Start Inspection", page_icon="➕")
load_custom_css()
require_login()
render_sidebar()

header("Start New Inspection")

# Always default to single mode as per user request
st.session_state.inspection_mode = 'single'

# Common Details Form (Shown immediately)
with st.form("property_details_form"):
    st.write("### Property Details")
    
    # Pre-fill if context exists
    def_name = st.session_state.get('current_property_name', '')
    def_house = ""
    def_address = ""
    
    if st.session_state.get('current_property_id'):
        from utils.db import run_query
        p_df = run_query(f"SELECT house_number, address FROM PROPERTIES WHERE property_id = '{st.session_state.current_property_id}'")
        if not p_df.empty:
            def_house = p_df.iloc[0]['house_number']
            def_address = p_df.iloc[0]['address']

    name = st.text_input("Property Name (e.g. My Apartment)", value=def_name)
    col1, col2 = st.columns(2)
    with col1:
        house_num = st.text_input("House/Unit Number (ID)", value=def_house)
    with col2:
        address = st.text_input("Address", value=def_address)
    
    # Renamed button to 'Inspect' as requested
    submitted = st.form_submit_button("Inspect")
    
    if submitted:
        if not name or not house_num:
            st.error("Name and ID are required.")
        else:
            try:
                # Logic: If property ID exists in session, it might be an existing one.
                # However, usually we might want to update it or just use it.
                
                prop_id = st.session_state.get('current_property_id')
                if not prop_id:
                    prop_id = f"PROP-{str(uuid.uuid4())[:8]}"
                    is_new = True
                else:
                    # Check if it actually exists in DB to be safe
                    from utils.db import run_query
                    check = run_query(f"SELECT 1 FROM PROPERTIES WHERE property_id = '{prop_id}'")
                    is_new = check.empty

                st.session_state.current_property_id = prop_id
                st.session_state.current_property_name = name
                
                if is_new:
                    # Insert Property
                    sql = f"""
                    INSERT INTO PROPERTIES (
                        property_id, house_number, property_name, address, 
                        property_type, construction_status, total_rooms, 
                        owner_user_id, report_visibility
                    ) VALUES (
                        '{prop_id}', '{house_num}', '{name}', '{address}',
                        'residential', 'existing', 1,
                        '{st.session_state.user_id}', 'private'
                    )
                    """
                    execute_statement(sql)
                
                # Update Service Request Status if applicable
                if 'current_service_id' in st.session_state:
                    execute_statement(f"UPDATE INSPECTION_SERVICE_REQUESTS SET status = 'in_progress' WHERE service_id = '{st.session_state.current_service_id}'")
                
                # Navigate to Wizard
                st.session_state.wizard_step = 1 # Start at config step
                st.session_state.room_config = [] # Clear config
                st.session_state.current_room_idx = 0 # Reset room index

                    
                st.switch_page("pages/04_Inspection_Wizard.py")
                    
            except Exception as e:
                st.error(f"Error: {e}")
