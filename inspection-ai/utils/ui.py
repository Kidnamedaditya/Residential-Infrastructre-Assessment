import streamlit as st

def load_custom_css():
    st.markdown("""
        <style>
        /* Modern Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Hide the first main page (app) from sidebar */
        [data-testid="stSidebarNav"] > ul > li:first-child {
            display: none;
        }
        
        /* Hide Inspection Wizard from sidebar specifically */
        li:has(span[title="Inspection Wizard"]), li:has(div:contains("Inspection Wizard")) {
            display: none !important;
        }
        /* Fallback for older browsers/Streamlit versions without :has support or title attr */
        a[href*="Inspection_Wizard"] {
            display: none !important;
        }
        
        /* Glassmorphism Cards */
        .stCard {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        /* Gradient Buttons */
        .stButton button {
            background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        /* Headers */
        h1, h2, h3 {
            background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        
        /* Metric Cards */
        .css-1r6slb0 {
            background-color: #1E1E1E;
            border: 1px solid #333;
            border-radius: 10px;
            padding: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

def header(title, subtitle=None):
    st.markdown(f"# {title}")
    if subtitle:
        st.caption(subtitle)
    st.divider()

def card(content):
    st.markdown(f"""
        <div class="stCard">
            {content}
        </div>
    """, unsafe_allow_html=True)

def require_login():
    if "user_id" not in st.session_state or not st.session_state.user_id:
        st.warning("Please login to access this page")
        st.switch_page("app.py")
        st.stop()

def render_sidebar():
    """Renders the standard sidebar with user info and logout."""
    if "user_id" in st.session_state and st.session_state.user_id:
        st.sidebar.markdown(f"### 👤 {st.session_state.username}")
        st.sidebar.caption(f"Role: {st.session_state.user_type.replace('_', ' ').title() if st.session_state.user_type else 'User'}")
        
        st.sidebar.divider()
        
        if st.sidebar.button("Logout", key="logout_btn", type="primary"):
            st.session_state.clear()
            st.switch_page("app.py")
            
        # Dynamic Role-based Page Hiding
        css_hide = ""
        
        if st.session_state.user_type == 'normal_user':
            # Hide Inspector Pages AND Start Inspection (keep it accessible only via Dashboard)
            css_hide += """
                li:has(span[title*="Inspector"]), li:has(div:contains("Inspector")) { display: none !important; }
                a[href*="Inspector"] { display: none !important; }
                li:has(span[title="Start Inspection"]), li:has(div:contains("Start Inspection")) { display: none !important; }
                a[href*="Start_Inspection"] { display: none !important; }
            """
        elif st.session_state.user_type == 'inspector':
            # Hide Normal User Pages (Keep Search and Results, but maybe hide Start Inspection?)
            # Usually Inspectors just view Dashboard and Workflow
            css_hide += """
                li:has(span[title="Start Inspection"]), li:has(div:contains("Start Inspection")) { display: none !important; }
                a[href*="Start_Inspection"] { display: none !important; }
                li:has(span[title="User Dashboard"]), li:has(div:contains("User Dashboard")) { display: none !important; }
                a[href*="User_Dashboard"] { display: none !important; }
            """
            
        if css_hide:
            st.markdown(f"<style>{css_hide}</style>", unsafe_allow_html=True)
            
    else:
        # If somehow we are here without login (e.g. public page), show login link
        pass
