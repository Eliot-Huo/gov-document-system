import streamlit as st

st.set_page_config(page_title="測試", layout="wide")

st.title("🎉 測試頁面")
st.success("✅ 系統成功啟動！")

# 測試 Secrets
try:
    if "SHEET_NAME" in st.secrets:
        st.success("✅ Secrets 設定正確")
        st.write(f"📊 Sheet 名稱：{st.secrets['SHEET_NAME']}")
        st.write(f"📁 Folder ID：{st.secrets['DRIVE_FOLDER_ID']}")
        
        if "gcp_service_account" in st.secrets:
            st.success("✅ Google Service Account 憑證已設定")
    else:
        st.warning("⚠️ Secrets 未設定")
except Exception as e:
    st.error(f"❌ 讀取 Secrets 時出錯：{str(e)}")
```

6. Commit changes

---

## ⏱️ 等待部署

修改後：
- 等待 1-2 分鐘
- Streamlit Cloud 會自動重新部署
- 重新整理網頁

---

## ✅ 預期結果

如果成功，您應該會看到：
```
🎉 測試頁面
✅ 系統成功啟動！
✅ Secrets 設定正確
📊 Sheet 名稱：政府公文資料庫
📁 Folder ID：1Iai9cTcvUtB9XxoAXbCdEHEP9zfsNoSM
✅ Google Service Account 憑證已設定
