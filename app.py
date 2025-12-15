import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.title("System Test Page")
st.success("If you see this, the deployment is successful!")

try:
    if "SHEET_NAME" in st.secrets:
        st.success("Secrets configured correctly")
        st.write(f"Sheet Name: {st.secrets['SHEET_NAME']}")
        st.write(f"Folder ID: {st.secrets['DRIVE_FOLDER_ID']}")
        
        if "gcp_service_account" in st.secrets:
            st.success("Google Service Account credentials are set")
    else:
        st.warning("Secrets not configured")
except Exception as e:
    st.error(f"Error reading Secrets: {str(e)}")
