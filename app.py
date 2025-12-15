import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import base64
from datetime import datetime
import pandas as pd

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

st.set_page_config(
    page_title="Team Document System",
    page_icon="📄",
    layout="wide"
)

# ===== Google API 連線設定 =====
@st.cache_resource
def init_google_services():
    """初始化 Google Services (Sheets & Drive)"""
    try:
        # 優先使用本地 credentials.json（支援多個路徑）
        import os
        
        # 定義可能的憑證檔案位置
        possible_paths = [
            'credentials.json',  # 當前目錄
            os.path.expanduser('~/credentials.json'),  # 家目錄
            '/Users/eliothuo/credentials.json',  # 您的完整路徑
        ]
        
        credentials = None
        for path in possible_paths:
            if os.path.exists(path):
                credentials = Credentials.from_service_account_file(
                    path,
                    scopes=SCOPES
                )
                st.success(f"✅ 已從 {path} 載入憑證")
                break
        
        if not credentials and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets['gcp_service_account'])
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=SCOPES
            )
            st.success("✅ 已從 Streamlit secrets 載入憑證")
        
        if not credentials:
            raise FileNotFoundError("找不到 credentials.json 檔案")
        
        # 初始化 Google Sheets 客戶端
        gc = gspread.authorize(credentials)
        
        # 初始化 Google Drive 客戶端
        drive_service = build('drive', 'v3', credentials=credentials)
        
        return gc, drive_service, credentials
    
    except FileNotFoundError as e:
        st.error(f"❌ 找不到憑證檔案: {str(e)}")
        st.info("""
        ### 📝 請完成以下步驟：
        
        1. **下載 Service Account 金鑰**
           - 前往 Google Cloud Console
           - 建立 Service Account 並下載 JSON 金鑰
        
        2. **放置檔案**
           - 將下載的 JSON 檔案重新命名為 `credentials.json`
           - 放在與 app.py 同一個資料夾中
        
        3. **重新執行程式**
           - 儲存檔案後重新整理頁面
        
        目前程式執行位置：{}
        """.format(os.getcwd()))
        st.stop()
    
    except Exception as e:
        st.error(f"❌ Google API 連線失敗: {str(e)}")
        st.info("請確認 credentials.json 檔案存在，或已設定 Streamlit secrets")
        st.stop()

# ===== Google Sheets 操作 =====
def get_sheet(gc, sheet_name):
    """取得 Google Sheet"""
    try:
        spreadsheet = gc.open(sheet_name)
        worksheet = spreadsheet.sheet1
        return worksheet
    except Exception as e:
        st.error(f"❌ 無法開啟 Google Sheet '{sheet_name}': {str(e)}")
        st.info("請確認 Service Account 已被授權存取此 Sheet")
        return None

def init_sheet_headers(worksheet):
    """初始化 Sheet 標題列（如果是空的）"""
    try:
        values = worksheet.get_all_values()
        if not values or len(values) == 0:
            headers = ['ID', 'Date', 'Type', 'Agency', 'Subject', 'Parent_ID', 'Drive_File_ID', 'Created_At']
            worksheet.append_row(headers)
            st.success("✅ 已初始化 Google Sheet 標題列")
    except Exception as e:
        st.error(f"初始化標題列失敗: {str(e)}")

def get_all_documents(worksheet):
    """從 Google Sheet 讀取所有公文資料"""
    try:
        # 取得所有值
        values = worksheet.get_all_values()
        
        # 如果 Sheet 是空的或只有標題列
        if not values or len(values) <= 1:
            return pd.DataFrame(columns=['ID', 'Date', 'Type', 'Agency', 'Subject', 'Parent_ID', 'Drive_File_ID', 'Created_At'])
        
        # 第一列是標題，後面是資料
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        
        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {str(e)}")
        return pd.DataFrame(columns=['ID', 'Date', 'Type', 'Agency', 'Subject', 'Parent_ID', 'Drive_File_ID', 'Created_At'])

def generate_document_id(worksheet, date_str, is_reply, parent_id):
    """生成流水號"""
    try:
        df = get_all_documents(worksheet)
        
        # 確保 DataFrame 不是空的且有 ID 欄位
        if df.empty or 'ID' not in df.columns:
            # 如果是空的，直接產生第一個 ID
            if not is_reply:
                date_code = date_str.replace('-', '')
                return f"{date_code}001"
            else:
                st.error("無法產生回覆案號：沒有原始公文資料")
                return None
        
        if is_reply and parent_id:
            # 回覆案：計算回覆次數
            reply_count = len(df[df['Parent_ID'].astype(str) == str(parent_id)])
            new_reply_number = str(reply_count + 2).zfill(2)
            doc_id = f"{new_reply_number}{parent_id}"
        else:
            # 新開案：YYYYMMDD + 流水號
            date_code = date_str.replace('-', '')
            same_day_docs = df[
                (df['ID'].astype(str).str.startswith(date_code)) & 
                (df['ID'].astype(str).str.len() == 11)
            ]
            next_serial = str(len(same_day_docs) + 1).zfill(3)
            doc_id = f"{date_code}{next_serial}"
        
        return doc_id
    except Exception as e:
        st.error(f"生成流水號失敗: {str(e)}")
        # 如果出錯，至少產生一個基本的 ID
        date_code = date_str.replace('-', '')
        return f"{date_code}001"

def add_document_to_sheet(worksheet, doc_data):
    """新增公文資料到 Google Sheet"""
    try:
        row = [
            doc_data['id'],
            doc_data['date'],
            doc_data['type'],
            doc_data['agency'],
            doc_data['subject'],
            doc_data['parent_id'] or '',
            doc_data['drive_file_id'] or '',
            doc_data['created_at']
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"寫入 Google Sheet 失敗: {str(e)}")
        return False

# ===== Google Drive 操作 =====
def upload_to_drive(drive_service, file_bytes, filename, folder_id):
    """上傳檔案到 Google Drive"""
    try:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype='application/pdf',
            resumable=True
        )
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        return file.get('id')
    
    except Exception as e:
        st.error(f"上傳到 Google Drive 失敗: {str(e)}")
        return None

def download_from_drive(drive_service, file_id):
    """從 Google Drive 下載檔案到記憶體"""
    try:
        request = drive_service.files().get_media(fileId=file_id)
        file_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_bytes.seek(0)
        return file_bytes.read()
    
    except Exception as e:
        st.error(f"從 Google Drive 下載失敗: {str(e)}")
        return None

def display_pdf_from_bytes(pdf_bytes):
    """將 PDF bytes 轉為 base64 並顯示"""
    if not pdf_bytes:
        st.warning("📋 無附件預覽")
        return
    
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'''
            <iframe src="data:application/pdf;base64,{base64_pdf}" 
                    width="100%" 
                    height="800px" 
                    type="application/pdf"
                    style="border: 2px solid #e5e7eb; border-radius: 8px;">
            </iframe>
        '''
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"PDF 顯示失敗: {str(e)}")

# ===== 主程式 =====
def main():
    st.title("📄 團隊版政府公文追蹤系統")
    st.markdown("**Google Drive + Google Sheets 整合版**")
    st.markdown("---")
    
    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 系統設定")
        
        # 從 secrets 或環境變數讀取預設值
        default_sheet_name = st.secrets.get("SHEET_NAME", "政府公文資料庫") if "SHEET_NAME" in st.secrets else "政府公文資料庫"
        default_folder_id = st.secrets.get("DRIVE_FOLDER_ID", "") if "DRIVE_FOLDER_ID" in st.secrets else ""
        
        sheet_name = st.text_input(
            "Google Sheet 名稱",
            value=default_sheet_name,
            help="請輸入您的 Google Sheet 名稱"
        )
        
        folder_id = st.text_input(
            "Google Drive Folder ID",
            value=default_folder_id,
            help="請輸入 Drive 資料夾的 ID（從網址取得）"
        )
        
        if not folder_id:
            st.warning("⚠️ 請設定 Google Drive Folder ID")
            st.info("從 Drive 資料夾網址取得，例如：\nhttps://drive.google.com/drive/folders/[THIS_IS_FOLDER_ID]")
        
        # 顯示設定說明
        with st.expander("💡 如何永久儲存設定？"):
            st.markdown("""
            **方法 1：使用 Streamlit Secrets**
            
            建立檔案 `~/.streamlit/secrets.toml`，內容：
            ```toml
            SHEET_NAME = "政府公文資料庫"
            DRIVE_FOLDER_ID = "您的Folder ID"
            ```
            
            **方法 2：設定環境變數**
            
            在 `~/.bash_profile` 或 `~/.zshrc` 加入：
            ```bash
            export SHEET_NAME="政府公文資料庫"
            export DRIVE_FOLDER_ID="您的Folder ID"
            ```
            """)
    
    # 初始化 Google Services
    gc, drive_service, credentials = init_google_services()
    
    # 取得 Google Sheet
    worksheet = get_sheet(gc, sheet_name)
    if worksheet:
        init_sheet_headers(worksheet)
    else:
        st.stop()
    
    # 頁籤
    tab1, tab2 = st.tabs(["➕ 新增公文", "🔍 查詢預覽"])
    
    # ===== 新增公文頁籤 =====
    with tab1:
        st.header("新增公文資料")
        
        col1, col2 = st.columns(2)
        
        with col1:
            date_input = st.date_input("📅 日期", datetime.now())
            doc_type = st.selectbox("📋 公文類型", ["發文", "收文", "簽呈", "函"])
            agency = st.text_input("🏢 機關單位", placeholder="例：人事處")
        
        with col2:
            subject = st.text_input("📝 主旨", placeholder="請輸入公文主旨")
        
        st.markdown("---")
        
        # 回覆案件選項
        is_reply = st.checkbox("↩️ 這是回覆案件")
        parent_id = None
        
        if is_reply:
            df = get_all_documents(worksheet)
            if not df.empty:
                doc_options = [f"{row['ID']} - {row['Subject']}" for _, row in df.iterrows()]
                selected = st.selectbox("選擇原始公文（Parent Document）", doc_options)
                parent_id = selected.split(" - ")[0] if selected else None
            else:
                st.warning("目前沒有可回覆的公文")
        
        st.markdown("---")
        
        # 檔案上傳
        st.subheader("📎 上傳 PDF 附件")
        uploaded_file = st.file_uploader("選擇 PDF 檔案", type=['pdf'])
        
        st.markdown("---")
        
        # 預覽流水號
        date_str = date_input.strftime('%Y-%m-%d')
        preview_id = generate_document_id(worksheet, date_str, is_reply, parent_id)
        
        if preview_id:
            st.info(f"### 🔢 預覽流水號: `{preview_id}`")
            
            if is_reply and parent_id:
                df = get_all_documents(worksheet)
                reply_count = len(df[df['Parent_ID'] == parent_id])
                st.caption(f"回覆次數：第 {str(reply_count + 2).zfill(2)} 次")
        
        st.markdown("---")
        
        # 提交按鈕
        if st.button("✅ 確認新增", type="primary", use_container_width=True):
            if not folder_id:
                st.error("❌ 請先在側邊欄設定 Google Drive Folder ID")
            elif not subject or not agency:
                st.error("❌ 請填寫完整資料（主旨、機關）")
            elif is_reply and not parent_id:
                st.error("❌ 請選擇原始公文")
            elif not uploaded_file:
                st.error("❌ 請上傳 PDF 檔案")
            else:
                with st.spinner("上傳中..."):
                    # 讀取檔案
                    file_bytes = uploaded_file.read()
                    
                    # 上傳到 Google Drive
                    filename = f"{preview_id}_{agency}_{subject}.pdf"
                    file_id = upload_to_drive(drive_service, file_bytes, filename, folder_id)
                    
                    if file_id:
                        # 寫入 Google Sheet
                        doc_data = {
                            'id': preview_id,
                            'date': date_str,
                            'type': doc_type,
                            'agency': agency,
                            'subject': subject,
                            'parent_id': parent_id,
                            'drive_file_id': file_id,
                            'created_at': datetime.now().isoformat()
                        }
                        
                        if add_document_to_sheet(worksheet, doc_data):
                            st.success(f"✅ 公文新增成功！流水號：{preview_id}")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ 寫入 Google Sheet 失敗")
                    else:
                        st.error("❌ 上傳到 Google Drive 失敗")
        
        st.markdown("---")
        
        # 顯示公文列表
        st.header("📚 公文列表")
        df = get_all_documents(worksheet)
        
        if df.empty:
            st.info("尚無公文資料")
        else:
            st.dataframe(
                df[['ID', 'Date', 'Type', 'Agency', 'Subject']],
                use_container_width=True,
                hide_index=True
            )
    
    # ===== 查詢預覽頁籤 =====
    with tab2:
        st.header("查詢與預覽")
        
        df = get_all_documents(worksheet)
        
        if df.empty:
            st.info("尚無公文資料")
        else:
            # 左右分割佈局
            left_col, right_col = st.columns([1, 1.5])
            
            # 左欄：清單區
            with left_col:
                st.subheader("📋 公文清單")
                
                for idx, row in df.iterrows():
                    doc_id = row['ID']
                    subject = row['Subject']
                    agency = row['Agency']
                    doc_type = row['Type']
                    
                    button_label = f"**{doc_id}**\n{agency} | {doc_type}\n{subject[:30]}..."
                    
                    if st.button(
                        button_label,
                        key=f"select_{doc_id}",
                        use_container_width=True
                    ):
                        st.session_state.selected_doc_id = doc_id
                
                st.markdown("---")
                st.caption(f"共 {len(df)} 筆公文")
            
            # 右欄：預覽區
            with right_col:
                st.subheader("👁️ 文件預覽")
                
                if 'selected_doc_id' not in st.session_state:
                    st.info("👈 請從左側清單選擇公文進行預覽")
                else:
                    selected_id = st.session_state.selected_doc_id
                    selected_row = df[df['ID'] == selected_id].iloc[0]
                    
                    # 顯示公文資訊
                    st.markdown(f"**公文字號：** `{selected_row['ID']}`")
                    st.markdown(f"**機關單位：** {selected_row['Agency']}")
                    st.markdown(f"**類型：** {selected_row['Type']}")
                    st.markdown(f"**主旨：** {selected_row['Subject']}")
                    st.markdown(f"**日期：** {selected_row['Date']}")
                    
                    if selected_row.get('Parent_ID'):
                        st.markdown(f"**回覆：** `{selected_row['Parent_ID']}`")
                    
                    st.markdown("---")
                    
                    # 顯示 PDF
                    st.markdown("### 📄 PDF 內容")
                    
                    drive_file_id = selected_row.get('Drive_File_ID')
                    
                    if drive_file_id:
                        with st.spinner("載入 PDF 中..."):
                            pdf_bytes = download_from_drive(drive_service, drive_file_id)
                            if pdf_bytes:
                                display_pdf_from_bytes(pdf_bytes)
                            else:
                                st.error("無法載入 PDF")
                    else:
                        st.warning("📋 此公文無附件")
    
    # 底部資訊
    st.markdown("---")
    st.info("""
    ### 📌 系統說明
    - **資料儲存：** Google Sheets（Metadata）+ Google Drive（PDF 檔案）
    - **編碼規則：** 新開案 YYYYMMDD+001，回覆案 回覆次數(2碼)+原始案號
    - **安全性：** 使用 Service Account 驗證，檔案私密存取
    - **團隊協作：** 多人可同時使用，資料即時同步
    """)

if __name__ == "__main__":
    main()
