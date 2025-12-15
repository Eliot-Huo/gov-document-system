import streamlit as st

st.set_page_config(page_title="測試", layout="wide")

st.title("🎉 系統測試頁面")
st.success("✅ 如果您看到這個訊息，表示部署成功！")

st.info("""
這是簡化測試版本。
如果這個版本能成功啟動，我們再逐步加入完整功能。
""")

# 測試 Secrets
if "SHEET_NAME" in st.secrets:
    st.write(f"✅ Secrets 設定正確，Sheet 名稱：{st.secrets['SHEET_NAME']}")
else:
    st.warning("⚠️ Secrets 未設定")
```

Commit changes

---

### 步驟 3：重新部署（使用簡化版）

1. 回到 Streamlit Cloud
2. New app
3. Repository: `Eliot-Huo/gov-document-system`
4. Branch: `main`
5. Main file path: `app.py`
6. **暫時不要設定 Secrets**
7. Deploy

---

### 步驟 4：觀察結果

**預期：** 2-3 分鐘內應該會成功，顯示測試頁面

如果這個簡化版本能成功：
- ✅ 表示問題出在原本的程式碼
- ✅ 我們再逐步加回功能

如果這個簡化版本也卡住：
- ❌ 表示是 Streamlit Cloud 平台問題
- ❌ 需要聯絡 Streamlit 支援

---

## 🎯 請現在就做：

1. ✅ 刪除目前的 app
2. ✅ 編輯 GitHub 的 app.py 為簡化版本
3. ✅ 重新部署（不設定 Secrets）
4. ✅ 告訴我能否看到測試頁面

---

## 💡 為什麼要這樣做？
```
複雜系統（目前）
├── Google API 連線
├── Secrets 讀取
├── 資料庫操作
├── 檔案上傳
└── PDF 預覽
   ↓
太多環節，不知道哪裡出錯


簡化版本
└── 只顯示一個頁面
   ↓
快速測試部署流程是否正常
   ↓
成功後再逐步加回功能
