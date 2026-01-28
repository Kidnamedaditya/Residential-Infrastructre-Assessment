import os
import streamlit as st

def upload_to_s3(file_obj):
    """
    Saves uploaded file to local 'uploads' directory.
    Replaces S3 functionality for local-only operation.
    """
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    file_path = os.path.join(upload_dir, file_obj.name)
    
    try:
        with open(file_path, "wb") as f:
            f.write(file_obj.getbuffer())
        
        # Return local path (or relative path for access)
        # In a real deployed web app, this would need to be served via static file server.
        # For Streamlit local run, we can reference it directly or via Image.open
        return os.path.abspath(file_path).replace("\\", "/")
    except Exception as e:
        st.error(f"Local save failed: {e}")
        return None
