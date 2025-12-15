import streamlit as st

st.set_page_config(page_title="測試 Secrets", layout="wide")

st.title("🔐 測試 Secrets 設定")

# 測試 Secrets
try:
    if "SHEET_NAME" in st.secrets:
        st.success(f"✅ SHEET_NAME: {st.secrets['SHEET_NAME']}")
    else:
        st.warning("⚠️ SHEET_NAME 未設定")
    
    if "DRIVE_FOLDER_ID" in st.secrets:
        st.success(f"✅ DRIVE_FOLDER_ID: {st.secrets['DRIVE_FOLDER_ID']}")
    else:
        st.warning("⚠️ DRIVE_FOLDER_ID 未設定")
    
    if "gcp_service_account" in st.secrets:
        st.success("✅ gcp_service_account 已設定")
        # 不顯示內容，只確認存在
    else:
        st.warning("⚠️ gcp_service_account 未設定")

except Exception as e:
    st.error(f"❌ 讀取 Secrets 時出錯: {str(e)}")

st.info("如果上面都顯示 ✅，表示 Secrets 設定正確")
