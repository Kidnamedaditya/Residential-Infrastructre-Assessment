import streamlit as st
import time
from utils.db import execute_statement, run_query
from utils.ui import load_custom_css, header

# Page Config
st.set_page_config(
    page_title="InfraIntel - AI Inspection",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load CSS
load_custom_css()

# Session State Init
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'user_type' not in st.session_state:
    st.session_state.user_type = None

def login():
    # Hide Sidebar on Login Page
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center; margin-bottom: 50px;'><h1>🏠 InfraIntel</h1><p>AI-Powered Residential Infrastructure Intelligence</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True):
                # Mock Login - In production verify hash
                try:
                    # In production, verify hash of password
                    user_df = run_query(f"SELECT user_id, user_type, full_name FROM USERS WHERE email = '{email}' AND password = '{password}'")
                    if not user_df.empty:
                        user = user_df.iloc[0]
                        st.session_state.user_id = user['user_id']
                        st.session_state.user_type = user['user_type']
                        st.session_state.username = user['full_name']
                        st.success(f"Welcome back, {user['full_name']}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("User not found")
                except Exception as e:
                    # Fallback for when DB isn't ready or mocked
                    if email == "john@example.com": 
                        st.session_state.user_id = "USER001"
                        st.session_state.user_type = "normal_user"
                        st.session_state.username = "John Doe"
                        st.rerun()
                    elif email == "raj@example.com":
                        st.session_state.user_id = "USER002"
                        st.session_state.user_type = "inspector"
                        st.session_state.username = "Rajesh Kumar"
                        st.rerun()
                    else:
                        st.error(f"Login failed: {e}")

        with tab2:
            new_email = st.text_input("New Email")
            new_password = st.text_input("New Password", type="password")
            new_name = st.text_input("Full Name")
            new_type = st.selectbox("I am a", ["normal_user", "inspector"])
            new_phone = st.text_input("Phone Number")
            
            if new_type == "inspector":
                license = st.text_input("License Number")
                specs = st.multiselect("Specialization", ["structural", "electrical", "plumbing", "finishing", "moisture"])
            
            if st.button("Create Account", use_container_width=True):
                try:
                    import uuid
                    uid = f"USER-{str(uuid.uuid4())[:8]}"
                    
                    # Insert User
                    sql = f"""
                    INSERT INTO USERS (user_id, email, password, user_type, full_name, phone, verified, created_at)
                    VALUES ('{uid}', '{new_email}', '{new_password}', '{new_type}', '{new_name}', '{new_phone}', TRUE, CURRENT_TIMESTAMP)
                    """
                    execute_statement(sql)
                    
                    if new_type == "inspector":
                        # Insert Profile
                        insp_id = f"INSP-{str(uuid.uuid4())[:8]}"
                        specs_arr = str(specs).replace('[', '').replace(']', '').replace("'", "") # Simplified serialization
                        # Note: array handling in simple SQL string injection might need specific syntax for Snowflake
                        # Using ARRAY_CONSTRUCT in real scenario or parameterized queries
                        
                        # Simplified for demo
                        sql_insp = f"""
                        INSERT INTO INSPECTOR_PROFILES (inspector_id, user_id, license_number, verified_inspector)
                        VALUES ('{insp_id}', '{uid}', '{license}', FALSE)
                        """
                        execute_statement(sql_insp)
                        
                    st.success("Account created! Please login.")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

def main():
    if not st.session_state.user_id:
        login()
        return

    # Sidebar Navigation
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.caption(f"Role: {st.session_state.user_type.replace('_', ' ').title()}")
    
    if st.sidebar.button("Logout"):
        st.session_state.user_id = None
        st.session_state.user_type = None
        st.rerun()
    
    st.sidebar.divider()
    
    # Conditional Navigation based on User Type
    # Auto-redirect to Dashboard
    if st.session_state.user_type == 'normal_user':
        st.switch_page("pages/02_User_Dashboard.py")
    elif st.session_state.user_type == 'inspector':
        st.switch_page("pages/06_Inspector_Dashboard.py")
    
    st.subheader("Welcome to InfraIntel")
    st.info("👈 Please select a page from the sidebar to get started.")
    
    # Dashboard preview/summary could go here
    if st.session_state.user_type == 'normal_user':
        col1, col2 = st.columns(2)
        with col1:
             st.markdown("### 🏠 My Properties")
             st.write("Manage your property portfolio and view inspection statuses.")
        with col2:
             st.markdown("### 🔍 Search")
             st.write("Search for properties by House Number to view public reports.")

if __name__ == "__main__":
    main()
