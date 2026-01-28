import streamlit as st
import uuid
import time
from utils.db import execute_statement
from utils.ui import load_custom_css, header, require_login, render_sidebar
from utils.s3 import upload_to_s3
from utils.ai import analyze_image_mock, analyze_document_text
from pypdf import PdfReader
import io

st.set_page_config(page_title="Inspection Wizard", page_icon="🕵️", layout="wide")
load_custom_css()
load_custom_css()
require_login()
render_sidebar()

# Check for property
if 'current_property_id' not in st.session_state:
    st.warning("Please start a new inspection first.")
    if st.button("Start New"):
        st.switch_page("pages/03_Start_Inspection.py")

# API Status Check
from utils.ai import GEMINI_API_KEY
api_status = "🟢 Online (Gemini)" if GEMINI_API_KEY else " 🟡 Offline (Mock Mode)"

# Simulation Controls
st.sidebar.markdown("### 🛠️ Developer / Demo Mode")
st.sidebar.info(f"AI Status: {api_status}")
sim_mode = st.sidebar.selectbox(
    "Force Detection Result",
    ["auto", "damp", "wiring", "structural", "ok"],
    format_func=lambda x: "Auto (AI/Random)" if x == "auto" else f"Force: {x.title()}"
)
st.sidebar.caption("Use 'Force' options to simulate specific defects if API is missing or for testing reports.")

header(f"Inspection: {st.session_state.current_property_name}")

# Wizard State
if 'wizard_step' not in st.session_state:
    st.session_state.wizard_step = 1
if 'room_config' not in st.session_state:
    st.session_state.room_config = []

# Step 1: Configure Rooms (Only for Full Property Mode)
# If Single mode, this step is skipped (wizard_step set to 2 in previous page)
if st.session_state.wizard_step == 1:
    st.subheader("Step 1: Configure Rooms")
    
    num_rooms = st.number_input("How many rooms/areas to inspect?", 1, 20, 3)
    
    with st.form("room_config_form"):
        rooms = []
        for i in range(num_rooms):
            col1, col2 = st.columns(2)
            with col1:
                r_name = st.text_input(f"Room {i+1} Name", value=f"Room {i+1}")
            with col2:
                r_type = st.selectbox(f"Type for Room {i+1}", 
                                    ["bedroom", "kitchen", "bathroom", "living_room", "utility", "exterior"])
            rooms.append({"name": r_name, "type": r_type})
        
        if st.form_submit_button("Next: Upload Images"):
            st.session_state.room_config = rooms
            st.session_state.wizard_step = 2
            st.rerun()

# Step 2: Upload Images (Room by Room)
elif st.session_state.wizard_step == 2:
    if 'current_room_idx' not in st.session_state:
        st.session_state.current_room_idx = 0
    
    current_idx = st.session_state.current_room_idx
    rooms = st.session_state.room_config
    
    # Fallback if config empty (should happen via single mode logic but safecheck)
    if not rooms:
        rooms = [{"name": "Single Room", "type": "generic"}]
        st.session_state.room_config = rooms

    if current_idx < len(rooms):
        room = rooms[current_idx]
        
        # UI for Single Mode vs Full
        if len(rooms) > 1:
             st.progress((current_idx) / len(rooms))
             st.caption(f"Room {current_idx + 1} of {len(rooms)}")
        
        st.subheader(f"📸 Upload for: {room['name']}")
        
        # Allow room name edit for Single Mode
        if len(rooms) == 1:
            new_name = st.text_input("Confirm Room Name", value=room['name'])
            room['name'] = new_name
        
        uploaded_files = st.file_uploader(
            f"Upload images for {room['name']}",
            accept_multiple_files=True,
            type=['png', 'jpg', 'jpeg'],
            key=f"uploader_{current_idx}"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if len(rooms) > 1 and st.button("⬅️ Previous", disabled=(current_idx==0)):
                st.session_state.current_room_idx -= 1
                st.rerun()
        
        with col2:
            next_label = "Next Room ➡️" if current_idx < len(rooms) - 1 else "Finish & Analyze 🚀"
            if st.button(next_label, use_container_width=True):
                if uploaded_files:
                    with st.spinner(f"Analyzing images for {room['name']}..."):
                        # Create Room in DB
                        room_id = f"RM-{str(uuid.uuid4())[:8]}"
                        
                        execute_statement(f"""
                            INSERT INTO ROOMS (room_id, property_id, room_name, room_type)
                            VALUES ('{room_id}', '{st.session_state.current_property_id}', '{room['name']}', '{room['type']}')
                        """)
                        
                        # Process Images
                        session_id = f"SESS-{str(uuid.uuid4())[:8]}" 
                        
                        for file in uploaded_files:
                            url = upload_to_s3(file)
                            analysis = analyze_image_mock(url, simulation_override=sim_mode)
                            
                            # Store Image
                            img_sql = f"""
                            INSERT INTO INSPECTION_IMAGES (
                                image_id, upload_session_id, user_id, property_id, room_id,
                                upload_scenario, image_url, original_filename,
                                ai_detected_defects, ai_confidence_score, ai_description, ai_severity
                            ) VALUES (
                                '{uuid.uuid4()}', '{session_id}', '{st.session_state.user_id}',
                                '{st.session_state.current_property_id}', '{room_id}',
                                'room_set', '{url}', '{file.name}',
                                '{analysis['defect_type']}', {analysis['confidence']},
                                '{analysis['description'].replace("'", "")}', '{analysis['severity']}'
                            )
                            """
                            execute_statement(img_sql)
                            
                            # Create Finding
                            if analysis['defect_type'] != 'none':
                                fnd_sql = f"""
                                INSERT INTO INSPECTION_FINDINGS (
                                    finding_id, room_id, property_id,
                                    finding_category, finding_description, severity,
                                    detected_by, confidence_score
                                ) VALUES (
                                    '{uuid.uuid4()}', '{room_id}', '{st.session_state.current_property_id}',
                                    '{analysis['defect_type']}', '{analysis['description'].replace("'", "")} Action: {analysis['action'].replace("'", "")}',
                                    '{analysis['severity']}', 'ai', {analysis['confidence']}
                                )
                                """
                                execute_statement(fnd_sql)
                        
                        st.Success = True
                
                # Move next
                st.session_state.current_room_idx += 1
                if st.session_state.current_room_idx >= len(rooms):
                    st.session_state.wizard_step = 3 # Move to Doc Upload
                st.rerun()

# Step 3: Upload Inspector Reports (Optional)
elif st.session_state.wizard_step == 3:
    st.subheader("Step 3: Upload Inspector Reports (Optional)")
    st.info("If you have an existing technical report (PDF/Text) from an inspector, upload it here for AI analysis.")
    
    doc_files = st.file_uploader(
        "Upload Reports",
        accept_multiple_files=True,
        type=['pdf', 'txt']
    )
    
    if st.button("Process & Finish 🚀", type="primary"):
        if doc_files:
            for doc in doc_files:
                text_content = ""
                if doc.type == "application/pdf":
                    try:
                        reader = PdfReader(doc)
                        for page in reader.pages:
                            text_content += page.extract_text() + "\n"
                    except Exception as e:
                        st.error(f"Error reading PDF {doc.name}: {e}")
                else:
                    # Text file
                    text_content = str(doc.read(), "utf-8")
                
                if text_content:
                    with st.spinner(f"Analyzing {doc.name}..."):
                        analysis = analyze_document_text(text_content)
                        
                        # Save to DB
                        d_id = f"DOC-{str(uuid.uuid4())[:8]}"
                        file_url = upload_to_s3(doc) # Reusing s3 for storage
                        
                        # Escape quotes for SQL
                        summary = analysis.get('ai_summary', '').replace("'", "''")
                        suggestions = analysis.get('ai_suggestions', '').replace("'", "''")
                        
                        sql_doc = f"""
                        INSERT INTO INSPECTION_DOCUMENTS (
                            doc_id, property_id, user_id, filename, file_url,
                            extracted_text, ai_summary, ai_suggestions
                        ) VALUES (
                            '{d_id}', '{st.session_state.current_property_id}', '{st.session_state.user_id}',
                            '{doc.name}', '{file_url}', '{text_content[:500].replace("'", "''")}...',
                            '{summary}', '{suggestions}'
                        )
                        """
                        execute_statement(sql_doc)
                        st.toast(f"Analyzed {doc.name}")
        
        st.session_state.wizard_step = 4
        st.rerun()
        
    if st.button("Skip"):
        st.session_state.wizard_step = 4
        st.rerun()

# Step 4: Completion
elif st.session_state.wizard_step == 4:
    st.balloons()
    st.success("Inspection Complete!")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
         st.markdown("### Analysis Report Ready")
         st.write("Your inspection report has been generated and saved.")
    
    with col2:
         if st.session_state.user_type == 'inspector':
             if st.button("Proceed to Cross-Check ->", type="primary"):
                 st.switch_page("pages/07_Inspector_Workflow.py")
         else:
             if st.button("View Full Report ->", type="primary"):
                 st.switch_page("pages/05_Analysis_Results.py")
