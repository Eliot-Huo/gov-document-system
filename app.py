import streamlit as st

st.set_page_config(
    page_title="Team Document System",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== 自訂 CSS 樣式 =====
st.markdown("""
<style>
    /* 全域設定 */
    .main {
        background-color: #F5F1E8;
    }
    
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 卡片樣式 */
    .custom-card {
        background: #FFFFFF;
        border: 1px solid #E8DCC8;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(139, 115, 85, 0.08);
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .custom-card:hover {
        box-shadow: 0 4px 16px rgba(139, 115, 85, 0.12);
        transform: translateY(-2px);
    }
    
    /* 功能磚塊 */
    .feature-tile {
        background: linear-gradient(135deg, #F5F1E8 0%, #E8DCC8 100%);
        border-radius: 16px;
        padding: 32px;
        text-align: center;
        cursor: pointer;
        min-height: 180px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        transition: all 0.3s ease;
        border: 2px solid transparent;
    }
    
    .feature-tile:hover {
        background: linear-gradient(135deg, #E8DCC8 0%, #C9B8A0 100%);
        border-color: #8B7355;
    }
    
    .feature-icon {
        font-size: 48px;
        margin-bottom: 12px;
    }
    
    .feature-title {
        font-size: 20px;
        font-weight: 600;
        color: #3E3E3E;
        margin-bottom: 8px;
    }
    
    .feature-desc {
        font-size: 14px;
        color: #666;
    }
    
    /* 警示卡片 */
    .alert-card {
        background: #FFF3F3;
        border-left: 4px solid #C97676;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .alert-card-warning {
        background: #FFFEF3;
        border-left: 4px solid #D4A574;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .alert-card-success {
        background: #F3FFF5;
        border-left: 4px solid #7FA881;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    /* 統計卡片 */
    .stat-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .stat-number {
        font-size: 36px;
        font-weight: 700;
        color: #8B7355;
        margin: 8px 0;
    }
    
    .stat-label {
        font-size: 14px;
        color: #666;
    }
    
    .stat-delta {
        font-size: 12px;
        color: #C97676;
        margin-top: 4px;
    }
    
    /* Header */
    .custom-header {
        background: linear-gradient(90deg, #8B7355 0%, #C9B8A0 100%);
        padding: 20px 30px;
        border-radius: 10px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        color: white;
    }
    
    /* 按鈕樣式 */
    .stButton > button {
        background: #8B7355;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: #6F5D45;
        box-shadow: 0 4px 12px rgba(139, 115, 85, 0.3);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #F5F1E8;
        border-radius: 8px;
    }
    
    /* 輸入框 */
    .stTextInput > div > div > input {
        border-color: #E8DCC8;
        border-radius: 8px;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #8B7355;
        box-shadow: 0 0 0 1px #8B7355;
    }
    
    /* 選擇框 */
    .stSelectbox > div > div {
        border-color: #E8DCC8;
        border-radius: 8px;
    }
    
    /* Metric 樣式優化 */
    [data-testid="stMetricValue"] {
        color: #8B7355;
        font-size: 28px;
    }
    
    [data-testid="stMetricLabel"] {
        color: #666;
    }
    
    [data-testid="stMetricDelta"] {
        color: #C97676;
    }
</style>
""", unsafe_allow_html=True)

import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import base64
from datetime import datetime
import pandas as pd
import hashlib

# PDF 轉圖片
try:
    import fitz  # PyMuPDF
    PDF_PREVIEW_AVAILABLE = True
except ImportError:
    PDF_PREVIEW_AVAILABLE = False

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# ===== 密碼加密 =====
def hash_password(password):
    """將密碼進行 SHA256 加密"""
    return hashlib.sha256(password.encode()).hexdigest()

# ===== 使用者驗證 =====
def check_login(users_df, username, password):
    """驗證使用者登入"""
    if users_df.empty:
        return None
    
    hashed = hash_password(password)
    user = users_df[(users_df['Username'] == username) & (users_df['Password'] == hashed)]
    
    if not user.empty:
        return {
            'username': user.iloc[0]['Username'],
            'display_name': user.iloc[0]['Display_Name'],
            'role': user.iloc[0]['Role']
        }
    return None

def is_admin():
    """檢查目前登入的使用者是否為管理員"""
    if 'user' not in st.session_state:
        return False
    return st.session_state.user.get('role') == 'admin'

# ===== Google API 連線設定 =====
@st.cache_resource
def init_google_services():
    """初始化 Google Services (Sheets & Drive)"""
    try:
        import os
        
        possible_paths = [
            'credentials.json',
            os.path.expanduser('~/credentials.json'),
        ]
        
        credentials = None
        for path in possible_paths:
            if os.path.exists(path):
                credentials = Credentials.from_service_account_file(
                    path,
                    scopes=SCOPES
                )
                break
        
        if not credentials and 'gcp_service_account' in st.secrets:
            credentials_dict = dict(st.secrets['gcp_service_account'])
            credentials = Credentials.from_service_account_info(
                credentials_dict,
                scopes=SCOPES
            )
        
        if not credentials:
            raise FileNotFoundError("找不到憑證檔案")
        
        gc = gspread.authorize(credentials)
        drive_service = build('drive', 'v3', credentials=credentials)
        
        return gc, drive_service, credentials
    
    except Exception as e:
        st.error(f"❌ Google API 連線失敗: {str(e)}")
        st.stop()

# ===== Google Sheets 操作 =====
def get_spreadsheet(gc, sheet_id):
    """取得 Google Spreadsheet"""
    try:
        return gc.open_by_key(sheet_id)
    except Exception as e:
        st.error(f"❌ 無法開啟 Google Sheet: {str(e)}")
        return None

@st.cache_resource(ttl=300)
def init_all_sheets(_spreadsheet):
    """初始化所有需要的工作表（使用快取）"""
    import time
    
    # 取得所有現有工作表
    existing_sheets = [ws.title for ws in _spreadsheet.worksheets()]
    
    # 公文資料表
    if '公文資料' not in existing_sheets:
        doc_headers = ['ID', 'Date', 'Type', 'Agency', 'Subject', 'Parent_ID', 
                       'Drive_File_ID', 'Created_At', 'Created_By', 'Status',
                       'OCR_Text', 'OCR_Status', 'OCR_Date']
        docs_sheet = _spreadsheet.add_worksheet(title='公文資料', rows=1000, cols=20)
        docs_sheet.append_row(doc_headers)
        time.sleep(0.5)  # 減少等待時間
    else:
        docs_sheet = _spreadsheet.worksheet('公文資料')
        # 檢查是否有 OCR 欄位,沒有就新增
        try:
            headers = docs_sheet.row_values(1)
            if 'OCR_Text' not in headers:
                # 新增 OCR 欄位
                next_col = len(headers) + 1
                docs_sheet.update_cell(1, next_col, 'OCR_Text')
                docs_sheet.update_cell(1, next_col + 1, 'OCR_Status')
                docs_sheet.update_cell(1, next_col + 2, 'OCR_Date')
        except:
            pass
    
    # 刪除紀錄表
    if '刪除紀錄' not in existing_sheets:
        deleted_headers = ['ID', 'Date', 'Type', 'Agency', 'Subject', 'Parent_ID',
                           'Drive_File_ID', 'Created_At', 'Created_By', 'Deleted_At', 'Deleted_By']
        deleted_sheet = _spreadsheet.add_worksheet(title='刪除紀錄', rows=1000, cols=20)
        deleted_sheet.append_row(deleted_headers)
        time.sleep(0.5)  # 減少等待時間
    else:
        deleted_sheet = _spreadsheet.worksheet('刪除紀錄')
    
    # 使用者資料表
    if '使用者' not in existing_sheets:
        user_headers = ['Username', 'Password', 'Display_Name', 'Role', 'Created_At']
        users_sheet = _spreadsheet.add_worksheet(title='使用者', rows=1000, cols=20)
        users_sheet.append_row(user_headers)
        time.sleep(0.5)  # 減少等待時間
        
        # 建立預設管理員帳號
        default_admin = [
            'admin',
            hash_password('admin123'),
            '系統管理員',
            'admin',
            datetime.now().isoformat()
        ]
        users_sheet.append_row(default_admin)
    else:
        users_sheet = _spreadsheet.worksheet('使用者')
    
    return docs_sheet, deleted_sheet, users_sheet

def get_all_documents(worksheet):
    """從工作表讀取所有公文資料"""
    try:
        values = worksheet.get_all_values()
        if not values or len(values) <= 1:
            return pd.DataFrame(columns=['ID', 'Date', 'Type', 'Agency', 'Subject', 
                                        'Parent_ID', 'Drive_File_ID', 'Created_At', 'Created_By', 'Status'])
        headers = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=headers)
        # 只顯示未刪除的資料
        if 'Status' in df.columns:
            df = df[df['Status'] != 'deleted']
        return df
    except Exception as e:
        st.error(f"讀取資料失敗: {str(e)}")
        return pd.DataFrame()

def get_all_users(worksheet):
    """從工作表讀取所有使用者"""
    try:
        values = worksheet.get_all_values()
        if not values or len(values) <= 1:
            return pd.DataFrame(columns=['Username', 'Password', 'Display_Name', 'Role', 'Created_At'])
        headers = values[0]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)
    except Exception as e:
        st.error(f"讀取使用者失敗: {str(e)}")
        return pd.DataFrame()

def generate_document_id(worksheet, date_str, is_reply, parent_id):
    """生成流水號"""
    try:
        df = get_all_documents(worksheet)
        
        if df.empty or 'ID' not in df.columns:
            if not is_reply:
                date_code = date_str.replace('-', '')
                return f"金展詢{date_code}001"
            else:
                return None
        
        if is_reply and parent_id:
            # 計算該 parent_id 的回覆數量
            reply_count = len(df[df['Parent_ID'].astype(str) == str(parent_id)])
            new_reply_number = str(reply_count + 2).zfill(2)
            doc_id = f"金展回{new_reply_number}{parent_id}"
        else:
            # 新發文:金展詢 + 日期 + 流水號
            date_code = date_str.replace('-', '')
            # 找出同一天所有以「金展詢+日期」開頭的公文
            same_day_docs = df[
                df['ID'].astype(str).str.startswith(f"金展詢{date_code}")
            ]
            next_serial = str(len(same_day_docs) + 1).zfill(3)
            doc_id = f"金展詢{date_code}{next_serial}"
        
        return doc_id
    except Exception as e:
        date_code = date_str.replace('-', '')
        return f"金展詢{date_code}001"

def add_document_to_sheet(worksheet, doc_data):
    """新增公文資料"""
    try:
        row = [
            doc_data['id'],
            doc_data['date'],
            doc_data['type'],
            doc_data['agency'],
            doc_data['subject'],
            doc_data['parent_id'] or '',
            doc_data['drive_file_id'] or '',
            doc_data['created_at'],
            doc_data['created_by'],
            'active',
            '',  # OCR_Text (空白,稍後填入)
            'pending',  # OCR_Status (待辨識)
            ''  # OCR_Date (辨識完成後填入)
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"寫入失敗: {str(e)}")
        return False

def add_user_to_sheet(worksheet, user_data):
    """新增使用者"""
    try:
        row = [
            user_data['username'],
            hash_password(user_data['password']),
            user_data['display_name'],
            user_data['role'],
            datetime.now().isoformat()
        ]
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"新增使用者失敗: {str(e)}")
        return False

def delete_user_from_sheet(worksheet, username):
    """刪除使用者"""
    try:
        cell = worksheet.find(username)
        if cell:
            worksheet.delete_rows(cell.row)
            return True
        return False
    except Exception as e:
        st.error(f"刪除使用者失敗: {str(e)}")
        return False

def soft_delete_document(docs_sheet, deleted_sheet, doc_id, deleted_by):
    """軟刪除公文（移到刪除紀錄）"""
    try:
        # 找到該筆資料
        cell = docs_sheet.find(doc_id)
        if not cell:
            return False
        
        # 取得該列資料
        row_data = docs_sheet.row_values(cell.row)
        
        # 新增到刪除紀錄表
        deleted_row = row_data[:9] + [datetime.now().isoformat(), deleted_by]
        deleted_sheet.append_row(deleted_row)
        
        # 從公文資料表刪除該列
        docs_sheet.delete_rows(cell.row)
        
        return True
    except Exception as e:
        st.error(f"刪除公文失敗: {str(e)}")
        return False

# ===== Google Drive 操作 =====
def get_or_create_subfolder(drive_service, parent_folder_id, folder_name):
    """在指定資料夾內取得或建立子資料夾"""
    try:
        # 先搜尋是否已存在
        query = f"name='{folder_name}' and '{parent_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            # 已存在，回傳 ID
            return files[0]['id']
        
        # 不存在，建立新資料夾
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        
        folder = drive_service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        return folder.get('id')
    except Exception as e:
        st.error(f"建立資料夾失敗: {str(e)}")
        return None

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
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        return file.get('id')
    except Exception as e:
        st.error(f"上傳失敗: {str(e)}")
        return None

def move_file_to_folder(drive_service, file_id, dest_folder_id):
    """移動檔案到另一個資料夾"""
    try:
        # 取得檔案目前的父資料夾
        file = drive_service.files().get(
            fileId=file_id,
            fields='parents',
            supportsAllDrives=True
        ).execute()
        
        previous_parents = ",".join(file.get('parents', []))
        
        # 移動到新資料夾
        drive_service.files().update(
            fileId=file_id,
            addParents=dest_folder_id,
            removeParents=previous_parents,
            supportsAllDrives=True,
            fields='id, parents'
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"移動檔案失敗: {str(e)}")
        return False

def download_from_drive(drive_service, file_id):
    """從 Google Drive 下載檔案"""
    try:
        request = drive_service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True
        )
        file_bytes = io.BytesIO()
        downloader = MediaIoBaseDownload(file_bytes, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        file_bytes.seek(0)
        return file_bytes.read()
    except Exception as e:
        st.error(f"下載失敗: {str(e)}")
        return None

def check_needs_tracking(df, doc_id, doc_type, doc_date):
    """檢查發文是否需要追蹤"""
    if doc_type != "發文":
        return False
    
    try:
        doc_date_obj = datetime.strptime(doc_date, '%Y-%m-%d')
        days_passed = (datetime.now() - doc_date_obj).days
        
        if days_passed <= 7:
            return False
        
        replies = df[df['Parent_ID'] == doc_id]
        has_reply = any(replies['Type'] == '收文')
        
        return not has_reply
    except:
        return False

def build_conversation_tree(df):
    """建立公文對話串結構"""
    if df.empty:
        return []
    
    # 建立 ID 對應的資料字典
    doc_dict = {row['ID']: row for _, row in df.iterrows()}
    
    # 找出所有根節點（沒有 Parent_ID 的公文）
    root_docs = df[df['Parent_ID'].isna() | (df['Parent_ID'] == '')]
    
    def build_tree_recursive(doc_id, level=0):
        """遞迴建立樹狀結構"""
        result = []
        if doc_id not in doc_dict:
            return result
        
        doc = doc_dict[doc_id]
        result.append({
            'doc': doc,
            'level': level,
            'id': doc_id
        })
        
        # 找出所有回覆此公文的子節點
        children = df[df['Parent_ID'] == doc_id]
        for _, child in children.iterrows():
            result.extend(build_tree_recursive(child['ID'], level + 1))
        
        return result
    
    # 建立完整的樹狀列表
    tree_list = []
    for _, root in root_docs.iterrows():
        tree_list.extend(build_tree_recursive(root['ID']))
    
    return tree_list

def get_conversation_thread(df, root_id):
    """取得特定公文的對話串"""
    if df.empty:
        return []
    
    # 建立 ID 對應的資料字典
    doc_dict = {row['ID']: row for _, row in df.iterrows()}
    
    def build_thread_recursive(doc_id, level=0):
        """遞迴建立對話串"""
        result = []
        if doc_id not in doc_dict:
            return result
        
        doc = doc_dict[doc_id]
        result.append({
            'doc': doc,
            'level': level,
            'id': doc_id
        })
        
        # 找出所有回覆此公文的子節點
        children = df[df['Parent_ID'] == doc_id]
        for _, child in children.iterrows():
            result.extend(build_thread_recursive(child['ID'], level + 1))
        
        return result
    
    return build_thread_recursive(root_id)

def filter_recent_documents(df, months=3):
    """篩選近 N 個月的公文"""
    if df.empty:
        return df
    
    try:
        from datetime import timedelta
        
        # 計算日期門檻
        threshold_date = datetime.now() - timedelta(days=months * 30)
        
        # 篩選近 N 個月的公文
        recent_docs = df[
            pd.to_datetime(df['Date'], errors='coerce') >= threshold_date
        ]
        
        return recent_docs
    except Exception as e:
        # 如果出錯,回傳全部
        return df

# ===== OCR 相關函數 =====
def ocr_pdf_from_drive(drive_service, file_id):
    """
    從 Google Drive 下載 PDF 並進行 OCR 辨識
    
    參數:
        drive_service: Google Drive API service
        file_id: PDF 在 Drive 中的 ID
    
    回傳:
        辨識的文字內容 (string) 或 None (失敗)
    """
    try:
        # 檢查是否有 Google Cloud Vision API 設定
        if 'gcp_service_account' not in st.secrets:
            print("OCR 辨識失敗: 未設定 Google Cloud Vision API")
            return None
        
        from google.cloud import vision
        from google.oauth2 import service_account
        
        # 使用 service account 認證
        credentials_dict = dict(st.secrets['gcp_service_account'])
        credentials = service_account.Credentials.from_service_account_info(credentials_dict)
        
        # 1. 從 Drive 下載 PDF
        pdf_bytes = download_from_drive(drive_service, file_id)
        if not pdf_bytes:
            return None
        
        # 2. 使用 Vision API 辨識
        client = vision.ImageAnnotatorClient(credentials=credentials)
        
        # 將 PDF 轉成圖片並辨識每一頁
        all_text = []
        
        # 使用 PyMuPDF 將 PDF 轉成圖片
        if not PDF_PREVIEW_AVAILABLE:
            return None
            
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 限制最多辨識 20 頁 (避免成本過高)
        max_pages = min(20, len(doc))
        
        for page_num in range(max_pages):
            # 取得頁面
            page = doc[page_num]
            
            # 轉成圖片 (PNG, 300 DPI 提高準確度)
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            
            # 呼叫 Vision API
            image = vision.Image(content=img_bytes)
            response = client.text_detection(image=image)
            
            if response.text_annotations:
                # 第一個結果是完整的文字
                page_text = response.text_annotations[0].description
                all_text.append(f"--- 第 {page_num + 1} 頁 ---\n{page_text}")
        
        doc.close()
        
        # 合併所有頁面的文字
        full_text = "\n\n".join(all_text)
        
        # 限制字數 (Google Sheets 單一儲存格最多 50,000 字元)
        if len(full_text) > 45000:
            full_text = full_text[:45000] + "\n\n...(文字過長,已截斷)"
        
        return full_text
        
    except Exception as e:
        print(f"OCR 辨識失敗: {str(e)}")
        return None

# ===== Gemini AI 摘要相關函數 =====
def generate_conversation_summary_prompt(conversation_data):
    """
    建立對話串摘要的 Prompt
    
    參數:
        conversation_data: 對話串資料列表
    
    回傳:
        格式化的 prompt 文字
    """
    prompt = "請以繁體中文分析以下政府公文對話串，提供結構化摘要：\n\n"
    
    for idx, item in enumerate(conversation_data, 1):
        doc = item['doc']
        level = item['level']
        indent = "  " * level
        
        prompt += f"{indent}[{idx}] {doc['Type']} - {doc['ID']}\n"
        prompt += f"{indent}日期: {doc['Date']}\n"
        prompt += f"{indent}機關: {doc['Agency']}\n"
        prompt += f"{indent}主旨: {doc['Subject']}\n"
        
        # 如果有 OCR 文字，加入前 500 字
        if 'OCR_Text' in doc and doc['OCR_Text']:
            ocr_preview = doc['OCR_Text'][:500]
            prompt += f"{indent}內容摘要: {ocr_preview}...\n"
        
        prompt += "\n"
    
    prompt += """
請提供以下格式的摘要（用繁體中文）:

📌 對話主題
[用一句話說明這個對話串的核心議題]

📊 往來狀況
[總共幾筆公文，最早到最晚的時間範圍，涉及哪些機關]

🔑 關鍵重點
1. [第一個重點]
2. [第二個重點]
3. [第三個重點]

✅ 處理結果
[目前的處理狀態，是否已完成回覆]

💡 備註
[任何需要注意的事項或建議]
"""
    
    return prompt

@st.cache_data(ttl=3600, show_spinner=False)
def get_ai_summary(conversation_ids_tuple, conversation_data):
    """
    使用 Gemini API 產生對話串摘要
    
    參數:
        conversation_ids_tuple: 對話串 ID 的 tuple (用於快取)
        conversation_data: 對話串資料列表
    
    回傳:
        摘要文字 或 None
    """
    try:
        # 檢查是否有 Gemini API Key
        if 'GOOGLE_GEMINI_API_KEY' not in st.secrets:
            return None
        
        import google.generativeai as genai
        
        # 設定 API Key
        genai.configure(api_key=st.secrets['GOOGLE_GEMINI_API_KEY'])
        
        # 建立模型
        model = genai.GenerativeModel('gemini-pro')
        
        # 建立 prompt
        prompt = generate_conversation_summary_prompt(conversation_data)
        
        # 呼叫 API
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return None
        
    except Exception as e:
        print(f"AI 摘要失敗: {str(e)}")
        return None

def update_ocr_result(worksheet, doc_id, ocr_text, status="completed"):
    """
    更新 OCR 辨識結果到 Google Sheets
    
    參數:
        worksheet: Google Sheets 工作表
        doc_id: 公文字號
        ocr_text: 辨識的文字
        status: 辨識狀態 (completed/failed)
    """
    try:
        # 找到該公文的行號
        cell = worksheet.find(doc_id)
        if not cell:
            return False
        
        row_num = cell.row
        
        # 取得欄位索引
        headers = worksheet.row_values(1)
        
        # 檢查是否有 OCR 欄位
        if 'OCR_Text' not in headers:
            return False
            
        ocr_text_col = headers.index('OCR_Text') + 1
        ocr_status_col = headers.index('OCR_Status') + 1
        ocr_date_col = headers.index('OCR_Date') + 1
        
        # 更新資料
        worksheet.update_cell(row_num, ocr_text_col, ocr_text or '')
        worksheet.update_cell(row_num, ocr_status_col, status)
        worksheet.update_cell(row_num, ocr_date_col, datetime.now().isoformat())
        
        return True
    except Exception as e:
        print(f"更新 OCR 結果失敗: {str(e)}")
        return False

def process_pending_ocr(docs_sheet, drive_service, limit=1):
    """
    處理待辨識的公文 (背景辨識)
    
    參數:
        docs_sheet: Google Sheets 工作表
        drive_service: Google Drive API service
        limit: 一次處理幾筆 (預設 1)
    
    回傳:
        處理的數量
    """
    try:
        df = get_all_documents(docs_sheet)
        
        # 找出待辨識的公文
        if 'OCR_Status' in df.columns:
            pending = df[df['OCR_Status'] == 'pending'].head(limit)
        else:
            return 0
        
        if pending.empty:
            return 0
        
        processed = 0
        for _, doc in pending.iterrows():
            doc_id = doc['ID']
            file_id = doc.get('Drive_File_ID')
            
            if not file_id:
                # 沒有檔案,標記為跳過
                update_ocr_result(docs_sheet, doc_id, None, "skipped")
                continue
            
            # 進行 OCR
            ocr_text = ocr_pdf_from_drive(drive_service, file_id)
            
            if ocr_text:
                update_ocr_result(docs_sheet, doc_id, ocr_text, "completed")
                processed += 1
            else:
                update_ocr_result(docs_sheet, doc_id, None, "failed")
        
        return processed
        
    except Exception as e:
        print(f"處理待辨識公文失敗: {str(e)}")
        return 0

def add_watermark_to_pdf(pdf_bytes, watermark_text):
    """為 PDF 添加浮水印（支援中文）"""
    if not PDF_PREVIEW_AVAILABLE:
        return pdf_bytes
    
    try:
        # 開啟 PDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        # 浮水印設定
        font_size = 16
        color = (0.75, 0.75, 0.75)  # 淡灰色
        
        for page in doc:
            page_width = page.rect.width
            page_height = page.rect.height
            
            # 計算浮水印間距
            x_gap = 180
            y_gap = 130
            
            y = 30
            row = 0
            while y < page_height + 100:
                x_start = -50 if row % 2 == 0 else 40
                x = x_start
                
                while x < page_width + 100:
                    try:
                        # 使用 fontname="china-s" 支援簡體中文
                        # 或使用 fontname="china-t" 支援繁體中文
                        page.insert_text(
                            fitz.Point(x, y),
                            watermark_text,
                            fontname="china-t",  # 繁體中文字體
                            fontsize=font_size,
                            color=color,
                            overlay=True
                        )
                    except:
                        # 備用：嘗試其他字體
                        try:
                            page.insert_text(
                                fitz.Point(x, y),
                                watermark_text,
                                fontname="china-s",
                                fontsize=font_size,
                                color=color,
                                overlay=True
                            )
                        except:
                            pass
                    
                    x += x_gap
                y += y_gap
                row += 1
        
        # 輸出為 bytes
        output = io.BytesIO()
        doc.save(output)
        doc.close()
        output.seek(0)
        return output.read()
    
    except Exception as e:
        return pdf_bytes

def add_watermark_to_image(img_bytes, watermark_text):
    """為圖片添加浮水印（支援中文）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import urllib.request
        import os
        
        # 開啟圖片
        img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
        
        # 建立透明圖層
        txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        # 嘗試取得中文字體
        font = None
        font_size = 32
        
        # 可能的中文字體路徑
        chinese_font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
            "/tmp/NotoSansTC-Regular.ttf",
        ]
        
        for font_path in chinese_font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
        
        # 如果沒有中文字體，嘗試下載
        if font is None:
            try:
                font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/TraditionalChinese/NotoSansTC-Regular.otf"
                font_path = "/tmp/NotoSansTC-Regular.otf"
                if not os.path.exists(font_path):
                    urllib.request.urlretrieve(font_url, font_path)
                font = ImageFont.truetype(font_path, font_size)
            except:
                # 最後備用：使用預設字體
                font = ImageFont.load_default()
        
        # 浮水印設定
        opacity = 50
        text_color = (128, 128, 128, opacity)
        
        # 計算文字大小
        try:
            bbox = draw.textbbox((0, 0), watermark_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            text_width = len(watermark_text) * font_size
            text_height = font_size
        
        # 間距
        x_gap = max(text_width + 80, 200)
        y_gap = max(text_height + 60, 100)
        
        # 佈滿浮水印
        y = -50
        row = 0
        while y < img.height + 100:
            x_offset = (row * 60) % x_gap
            x = -100 + x_offset
            
            while x < img.width + 100:
                draw.text((x, y), watermark_text, font=font, fill=text_color)
                x += x_gap
            
            y += y_gap
            row += 1
        
        # 合併圖層
        result = Image.alpha_composite(img, txt_layer)
        result = result.convert('RGB')
        
        # 輸出
        output = io.BytesIO()
        result.save(output, format='PNG')
        output.seek(0)
        return output.read()
    
    except Exception as e:
        return img_bytes

def display_pdf_from_bytes(pdf_bytes, watermark_text=None):
    """顯示 PDF 預覽（含浮水印）"""
    if not pdf_bytes:
        st.warning("📋 無附件預覽")
        return
    
    try:
        # 如果有浮水印文字，添加浮水印到下載的 PDF
        if watermark_text:
            watermarked_pdf = add_watermark_to_pdf(pdf_bytes, watermark_text)
            download_data = watermarked_pdf
        else:
            download_data = pdf_bytes
        
        st.download_button(
            label="📥 下載 PDF 檔案",
            data=download_data,
            file_name="document.pdf",
            mime="application/pdf"
        )
        
        if PDF_PREVIEW_AVAILABLE:
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                st.markdown(f"**共 {len(doc)} 頁**")
                
                for page_num in range(min(len(doc), 10)):
                    page = doc[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    img_bytes = pix.tobytes("png")
                    
                    # 為預覽圖片添加浮水印
                    if watermark_text:
                        img_bytes = add_watermark_to_image(img_bytes, watermark_text)
                    
                    st.image(img_bytes, caption=f"第 {page_num + 1} 頁", width="stretch")
                
                if len(doc) > 10:
                    st.info("⚠️ 僅顯示前 10 頁，完整文件請下載查看")
                doc.close()
            except Exception as e:
                st.warning(f"PDF 預覽失敗: {str(e)}")
        else:
            st.info("📄 請使用下載按鈕查看 PDF")
    except Exception as e:
        st.error(f"處理 PDF 失敗: {str(e)}")

# ===== 追蹤回覆相關函數 =====
def check_reply_status(df, doc_id, doc_type, doc_date):
    """
    檢查公文是否已有回覆
    
    參數:
        df: 所有公文的 DataFrame
        doc_id: 公文字號
        doc_type: 公文類型
        doc_date: 發文日期
    
    回傳:
        {
            'has_reply': True/False,
            'days_waiting': 10,
            'need_tracking': True/False,
            'reply_count': 2,
            'latest_reply_date': '2024-12-15'
        }
    """
    # 只檢查我方發出的公文
    if doc_type not in ['發文', '函']:
        return None
    
    try:
        # 檢查是否有子公文 (回覆)
        replies = df[df['Parent_ID'] == doc_id]
        
        # 計算等待天數
        from datetime import datetime
        doc_date_obj = datetime.strptime(doc_date, '%Y-%m-%d')
        today = datetime.now()
        days_waiting = (today - doc_date_obj).days
        
        # 檢查是否有政府回文
        gov_replies = replies[replies['Type'] == '收文']
        
        result = {
            'has_reply': len(gov_replies) > 0,
            'days_waiting': days_waiting,
            'need_tracking': days_waiting > 7 and len(gov_replies) == 0,
            'reply_count': len(replies),
            'latest_reply_date': None
        }
        
        if len(gov_replies) > 0:
            # 找最新的回覆日期
            latest_reply = gov_replies.sort_values('Date', ascending=False).iloc[0]
            result['latest_reply_date'] = latest_reply['Date']
        
        return result
    except Exception as e:
        print(f"檢查回覆狀態失敗: {str(e)}")
        return None

def get_pending_replies(df):
    """
    取得所有待回覆的公文
    
    回傳:
        {
            'urgent': [...]  # 超過 7 天的公文
            'normal': [...]  # 7 天內的公文
        }
    """
    pending = {
        'urgent': [],
        'normal': []
    }
    
    try:
        # 只檢查我方發出的公文
        our_docs = df[df['Type'].isin(['發文', '函'])]
        
        for _, doc in our_docs.iterrows():
            status = check_reply_status(df, doc['ID'], doc['Type'], doc['Date'])
            
            if status and not status['has_reply']:
                doc_info = {
                    'id': doc['ID'],
                    'date': doc['Date'],
                    'agency': doc['Agency'],
                    'subject': doc['Subject'],
                    'days_waiting': status['days_waiting'],
                    'created_by': doc.get('Created_By', '未知')
                }
                
                if status['need_tracking']:
                    pending['urgent'].append(doc_info)
                else:
                    pending['normal'].append(doc_info)
        
        # 依天數排序 (從多到少)
        pending['urgent'].sort(key=lambda x: x['days_waiting'], reverse=True)
        pending['normal'].sort(key=lambda x: x['days_waiting'], reverse=True)
        
    except Exception as e:
        print(f"取得待回覆公文失敗: {str(e)}")
    
    return pending
def login_page(users_sheet):
    """顯示登入頁面"""
    st.title("🔐 系統登入")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("請輸入帳號密碼")
        
        username = st.text_input("👤 帳號", key="login_username")
        password = st.text_input("🔑 密碼", type="password", key="login_password")
        
        if st.button("登入", type="primary", width="stretch"):
            if username and password:
                with st.spinner("🔄 驗證中..."):
                    users_df = get_all_users(users_sheet)
                    user = check_login(users_df, username, password)
                    
                    if user:
                        st.session_state.user = user
                        st.session_state.logged_in = True
                        st.success(f"✅ 歡迎，{user['display_name']}！")
                        st.rerun()
                    else:
                        st.error("❌ 帳號或密碼錯誤")
            else:
                st.warning("⚠️ 請輸入帳號和密碼")
        
        st.markdown("---")
        st.caption("預設管理員帳號：admin / admin123")
        st.caption("⚠️ 請登入後立即修改預設密碼")

# ===== 使用者管理頁面 =====
def user_management_page(users_sheet):
    """使用者管理頁面（僅管理員可用）"""
    st.header("👥 使用者管理")
    
    if not is_admin():
        st.error("❌ 您沒有權限存取此頁面")
        return
    
    tab1, tab2, tab3 = st.tabs(["📋 使用者列表", "➕ 新增使用者", "🔑 修改密碼"])
    
    # 使用者列表
    with tab1:
        users_df = get_all_users(users_sheet)
        
        if users_df.empty:
            st.info("尚無使用者資料")
        else:
            # 隱藏密碼欄位
            display_df = users_df[['Username', 'Display_Name', 'Role', 'Created_At']].copy()
            display_df.columns = ['帳號', '顯示名稱', '角色', '建立時間']
            st.dataframe(display_df, width="stretch", hide_index=True)
            
            st.markdown("---")
            st.subheader("🗑️ 刪除使用者")
            
            # 不能刪除自己和最後一個管理員
            deletable_users = users_df[users_df['Username'] != st.session_state.user['username']]
            
            if deletable_users.empty:
                st.info("沒有可刪除的使用者")
            else:
                user_to_delete = st.selectbox(
                    "選擇要刪除的使用者",
                    deletable_users['Username'].tolist()
                )
                
                if st.button("🗑️ 刪除使用者", type="secondary"):
                    # 檢查是否為最後一個管理員
                    admin_count = len(users_df[users_df['Role'] == 'admin'])
                    user_role = users_df[users_df['Username'] == user_to_delete]['Role'].iloc[0]
                    
                    if user_role == 'admin' and admin_count <= 1:
                        st.error("❌ 無法刪除最後一個管理員帳號")
                    else:
                        if delete_user_from_sheet(users_sheet, user_to_delete):
                            st.success(f"✅ 已刪除使用者：{user_to_delete}")
                            st.rerun()
    
    # 新增使用者
    with tab2:
        st.subheader("新增使用者")
        
        new_username = st.text_input("帳號", key="new_username")
        new_password = st.text_input("密碼", type="password", key="new_password")
        new_display_name = st.text_input("顯示名稱", key="new_display_name")
        new_role = st.selectbox("角色", ["user", "admin"], key="new_role")
        
        if st.button("➕ 新增", type="primary"):
            if new_username and new_password and new_display_name:
                # 檢查帳號是否已存在
                users_df = get_all_users(users_sheet)
                if new_username in users_df['Username'].values:
                    st.error("❌ 此帳號已存在")
                else:
                    user_data = {
                        'username': new_username,
                        'password': new_password,
                        'display_name': new_display_name,
                        'role': new_role
                    }
                    if add_user_to_sheet(users_sheet, user_data):
                        st.success(f"✅ 已新增使用者：{new_username}")
                        st.rerun()
            else:
                st.warning("⚠️ 請填寫所有欄位")
    
    # 修改密碼
    with tab3:
        st.subheader("修改使用者密碼")
        
        users_df = get_all_users(users_sheet)
        user_to_change = st.selectbox(
            "選擇使用者",
            users_df['Username'].tolist(),
            key="change_pwd_user"
        )
        
        new_pwd = st.text_input("新密碼", type="password", key="new_pwd")
        confirm_pwd = st.text_input("確認新密碼", type="password", key="confirm_pwd")
        
        if st.button("🔑 修改密碼"):
            if new_pwd and confirm_pwd:
                if new_pwd != confirm_pwd:
                    st.error("❌ 兩次輸入的密碼不一致")
                else:
                    try:
                        cell = users_sheet.find(user_to_change)
                        if cell:
                            users_sheet.update_cell(cell.row, 2, hash_password(new_pwd))
                            st.success(f"✅ 已修改 {user_to_change} 的密碼")
                    except Exception as e:
                        st.error(f"修改失敗: {str(e)}")
            else:
                st.warning("⚠️ 請輸入新密碼")

# ===== 主程式 =====
def main():
    # 初始化 session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # 從 secrets 讀取設定
    sheet_id = st.secrets.get("SHEET_ID", "") if "SHEET_ID" in st.secrets else ""
    folder_id = st.secrets.get("DRIVE_FOLDER_ID", "") if "DRIVE_FOLDER_ID" in st.secrets else ""
    
    if not sheet_id:
        st.error("❌ 請在 Secrets 設定 SHEET_ID")
        st.stop()
    
    # ===== 未登入:只初始化必要的服務以顯示登入頁面 =====
    if not st.session_state.logged_in:
        # 只初始化最基本的服務
        gc, drive_service, credentials = init_google_services()
        spreadsheet = get_spreadsheet(gc, sheet_id)
        if not spreadsheet:
            st.stop()
        
        # 只初始化使用者工作表
        existing_sheets = [ws.title for ws in spreadsheet.worksheets()]
        if '使用者' not in existing_sheets:
            # 如果沒有使用者表,才完整初始化
            docs_sheet, deleted_sheet, users_sheet = init_all_sheets(spreadsheet)
        else:
            users_sheet = spreadsheet.worksheet('使用者')
        
        login_page(users_sheet)
        return
    
    # ===== 已登入:初始化完整的服務 =====
    # 初始化 Google Services
    gc, drive_service, credentials = init_google_services()
    
    # 自動在主資料夾內建立「已刪除」子資料夾
    deleted_folder_id = None
    if folder_id:
        if 'deleted_folder_id' not in st.session_state:
            deleted_folder_id = get_or_create_subfolder(drive_service, folder_id, "已刪除公文")
            st.session_state.deleted_folder_id = deleted_folder_id
        else:
            deleted_folder_id = st.session_state.deleted_folder_id
    
    # 取得 Spreadsheet 並初始化所有工作表
    spreadsheet = get_spreadsheet(gc, sheet_id)
    if not spreadsheet:
        st.stop()
    
    docs_sheet, deleted_sheet, users_sheet = init_all_sheets(spreadsheet)
    
    # ===== 已登入的主介面 =====
    
    # 初始化頁面狀態
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'home'
    
    # 側邊欄 (簡化版)
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['display_name']}")
        st.caption(f"角色：{'管理員' if is_admin() else '一般使用者'}")
        
        if st.button("🚪 登出", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        st.markdown("---")
        
        # 快速導航
        st.markdown("### 📌 快速導航")
        if st.button("🏠 首頁", key="nav_home", use_container_width=True):
            st.session_state.current_page = 'home'
            st.rerun()
        
        if st.button("➕ 新增公文", key="nav_add", use_container_width=True):
            st.session_state.current_page = 'add_document'
            st.rerun()
        
        if st.button("🔍 查詢公文", key="nav_search", use_container_width=True):
            st.session_state.current_page = 'search'
            st.rerun()
        
        if st.button("⏰ 追蹤回覆", key="nav_track", use_container_width=True):
            st.session_state.current_page = 'tracking'
            st.rerun()
        
        if st.button("📝 處理辨識", key="nav_ocr", use_container_width=True):
            st.session_state.current_page = 'ocr'
            st.rerun()
        
        if is_admin():
            st.markdown("---")
            if st.button("📊 系統管理", key="nav_admin", use_container_width=True):
                st.session_state.current_page = 'admin'
                st.rerun()
    
    # Header
    try:
        with open("logo.png", "rb") as f:
            logo_bytes = f.read()
        logo_base64 = base64.b64encode(logo_bytes).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" style="height: 60px; margin-right: 20px;">'
    except:
        logo_html = '<span style="font-size: 48px; margin-right: 20px;">🏢</span>'
    
    st.markdown(
        f"""
        <div class="custom-header">
            {logo_html}
            <h1 style="margin: 0; font-size: 2rem;">團隊版政府公文追蹤系統</h1>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 根據 current_page 顯示不同頁面
    if st.session_state.current_page == 'home':
        show_home_page(docs_sheet, drive_service, deleted_folder_id)
    
    elif st.session_state.current_page == 'add_document':
        show_add_document_page(docs_sheet, drive_service, folder_id)
    
    elif st.session_state.current_page == 'search':
        show_search_page(docs_sheet, drive_service, deleted_sheet, deleted_folder_id, folder_id)
    
    elif st.session_state.current_page == 'tracking':
        show_tracking_page(docs_sheet)
    
    elif st.session_state.current_page == 'ocr':
        show_ocr_page(docs_sheet, drive_service)
    
    elif st.session_state.current_page == 'admin':
        if is_admin():
            show_admin_page(docs_sheet, deleted_sheet, users_sheet)
        else:
            st.error("❌ 您沒有權限訪問此頁面")

# ===== 首頁 =====
def show_home_page(docs_sheet, drive_service, deleted_folder_id):
    """顯示首頁 - 儀表板 + 功能磚塊"""
    
    # 取得資料
    df = get_all_documents(docs_sheet)
    
    # 計算統計數據
    total_docs = len(df)
    
    # 待回覆統計
    pending_replies = get_pending_replies(df)
    urgent_count = len(pending_replies['urgent'])
    normal_count = len(pending_replies['normal'])
    total_pending = urgent_count + normal_count
    
    # 已完成統計
    completed_count = total_docs - total_pending
    
    # OCR 待處理統計
    if 'OCR_Status' in df.columns:
        ocr_pending = len(df[df['OCR_Status'] == 'pending'])
    else:
        ocr_pending = 0
    
    # 統計卡片
    st.markdown("### 📊 系統概覽")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📚 總公文數",
            value=total_docs
        )
    
    with col2:
        st.metric(
            label="⏳ 待回覆",
            value=total_pending,
            delta=f"-{urgent_count} 筆超過7天" if urgent_count > 0 else "正常",
            delta_color="inverse" if urgent_count > 0 else "off"
        )
    
    with col3:
        st.metric(
            label="✅ 已完成",
            value=completed_count
        )
    
    with col4:
        st.metric(
            label="📝 待辨識",
            value=ocr_pending
        )
    
    st.markdown("---")
    
    # 緊急警示 (如果有超過 7 天的公文)
    if urgent_count > 0:
        st.markdown(
            f"""
            <div class="alert-card">
                <h3 style="margin: 0 0 12px 0; color: #C97676;">⚠️ 緊急提醒：{urgent_count} 筆公文超過 7 天未回覆</h3>
            """,
            unsafe_allow_html=True
        )
        
        # 顯示前 3 筆
        for doc in pending_replies['urgent'][:3]:
            st.markdown(
                f"""
                <div style="padding: 8px 0; border-bottom: 1px solid #FFE0E0;">
                    🔴 <strong>{doc['id']}</strong> | {doc['agency']} | 
                    <span style="color: #C97676; font-weight: 600;">{doc['days_waiting']} 天未回覆</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        col_alert1, col_alert2 = st.columns([1, 4])
        with col_alert1:
            if st.button("前往追蹤回覆專區 →", key="goto_tracking"):
                st.session_state.current_page = 'tracking'
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")
    
    # 功能磚塊
    st.markdown("### 🎯 快速功能")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #F5F1E8 0%, #E8DCC8 100%); 
                    border-radius: 16px; padding: 40px; text-align: center; margin-bottom: 20px;
                    min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 48px;">➕</div>
            <div style="font-size: 20px; font-weight: 600; margin: 12px 0;">新增公文</div>
            <div style="font-size: 14px; color: #666;">上傳 PDF 建立新案件</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("點擊進入", key="tile_add", use_container_width=True):
            st.session_state.current_page = 'add_document'
            st.rerun()
    
    with col2:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #F5F1E8 0%, #E8DCC8 100%); 
                    border-radius: 16px; padding: 40px; text-align: center; margin-bottom: 20px;
                    min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 48px;">🔍</div>
            <div style="font-size: 20px; font-weight: 600; margin: 12px 0;">查詢公文</div>
            <div style="font-size: 14px; color: #666;">搜尋與查看歷史紀錄</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("點擊進入", key="tile_search", use_container_width=True):
            st.session_state.current_page = 'search'
            st.rerun()
    
    col3, col4 = st.columns(2)
    
    with col3:
        track_label = "查看待回覆公文"
        if urgent_count > 0:
            track_label = f"⚠️ {urgent_count} 筆需追蹤"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F5F1E8 0%, #E8DCC8 100%); 
                    border-radius: 16px; padding: 40px; text-align: center; margin-bottom: 20px;
                    min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 48px;">⏰</div>
            <div style="font-size: 20px; font-weight: 600; margin: 12px 0;">追蹤回覆</div>
            <div style="font-size: 14px; color: #666;">{track_label}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("點擊進入", key="tile_track", use_container_width=True):
            st.session_state.current_page = 'tracking'
            st.rerun()
    
    with col4:
        ocr_label = "進行文字辨識"
        if ocr_pending > 0:
            ocr_label = f"⏳ {ocr_pending} 筆待辨識"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F5F1E8 0%, #E8DCC8 100%); 
                    border-radius: 16px; padding: 40px; text-align: center; margin-bottom: 20px;
                    min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 48px;">📝</div>
            <div style="font-size: 20px; font-weight: 600; margin: 12px 0;">處理辨識</div>
            <div style="font-size: 14px; color: #666;">{ocr_label}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("點擊進入", key="tile_ocr", use_container_width=True):
            st.session_state.current_page = 'ocr'
            st.rerun()
    
    # 管理員磚塊
    if is_admin():
        st.markdown("""
        <div style="background: linear-gradient(135deg, #F5F1E8 0%, #E8DCC8 100%); 
                    border-radius: 16px; padding: 40px; text-align: center; margin-bottom: 20px;
                    min-height: 180px; display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 48px;">📊</div>
            <div style="font-size: 20px; font-weight: 600; margin: 12px 0;">系統管理</div>
            <div style="font-size: 14px; color: #666;">使用者與系統設定</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("點擊進入", key="tile_admin", use_container_width=True):
            st.session_state.current_page = 'admin'
            st.rerun()
    
    st.markdown("---")
    
    # 近期活動
    st.markdown("### 📋 近期活動 (最新 5 筆)")
    
    if df.empty:
        st.info("尚無公文資料")
    else:
        # 取最新 5 筆
        recent_docs = df.sort_values('Created_At', ascending=False).head(5)
        
        for _, doc in recent_docs.iterrows():
            icon = "📤" if doc['Type'] in ['發文', '函'] else "📥"
            
            col_doc1, col_doc2 = st.columns([5, 1])
            with col_doc1:
                st.markdown(
                    f"{icon} **{doc['ID']}** | {doc['Date']} | {doc['Agency']} | {doc['Subject'][:40]}..."
                )
            with col_doc2:
                if st.button("查看", key=f"view_recent_{doc['ID']}"):
                    st.session_state.selected_doc_id = doc['ID']
                    st.session_state.current_page = 'search'
                    st.session_state.show_detail = True
                    st.rerun()

# ===== 追蹤回覆頁面 =====
def show_tracking_page(docs_sheet):
    """追蹤回覆專頁"""
    
    st.markdown("## ⏰ 追蹤回覆")
    
    df = get_all_documents(docs_sheet)
    pending = get_pending_replies(df)
    
    # 統計卡片
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 總計", len(pending['urgent']) + len(pending['normal']))
    
    with col2:
        st.metric("⚠️ 需追蹤", len(pending['urgent']))
    
    with col3:
        st.metric("🟡 等待中", len(pending['normal']))
    
    st.markdown("---")
    
    # 緊急追蹤區
    if pending['urgent']:
        st.markdown("### 🔴 緊急追蹤 (超過 7 天)")
        
        for doc in pending['urgent']:
            st.markdown(
                f"""
                <div class="alert-card">
                    <h4 style="margin: 0; color: #C97676;">🔴 {doc['id']}</h4>
                    <p style="margin: 8px 0 0 0;">
                        📅 發文日期: {doc['date']} | ⏰ 已等待: <strong style="color: #C97676;">{doc['days_waiting']} 天</strong><br>
                        🏢 機關: {doc['agency']}<br>
                        📝 主旨: {doc['subject']}<br>
                        👤 建立者: {doc['created_by']}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            col_a, col_b = st.columns([1, 5])
            with col_a:
                if st.button("👁️ 查看詳情", key=f"view_urgent_{doc['id']}"):
                    st.session_state.selected_doc_id = doc['id']
                    st.session_state.current_page = 'search'
                    st.session_state.show_detail = True
                    st.rerun()
            
            st.markdown("")
    else:
        st.success("✅ 目前沒有超過 7 天未回覆的公文")
    
    st.markdown("---")
    
    # 正常等待區
    if pending['normal']:
        st.markdown("### 🟡 正常等待 (7 天內)")
        
        for doc in pending['normal']:
            with st.expander(
                f"🟡 {doc['id']} | {doc['agency']} | 已等待 {doc['days_waiting']} 天"
            ):
                st.markdown(f"**發文日期**: {doc['date']}")
                st.markdown(f"**機關單位**: {doc['agency']}")
                st.markdown(f"**主旨**: {doc['subject']}")
                st.markdown(f"**建立者**: {doc['created_by']}")
                
                if st.button("👁️ 查看詳情", key=f"view_normal_{doc['id']}"):
                    st.session_state.selected_doc_id = doc['id']
                    st.session_state.current_page = 'search'
                    st.session_state.show_detail = True
                    st.rerun()

# ===== OCR 處理頁面 =====
def show_ocr_page(docs_sheet, drive_service):
    """OCR 處理專頁"""
    
    st.markdown("## 📝 處理辨識")
    
    df = get_all_documents(docs_sheet)
    
    if 'OCR_Status' not in df.columns:
        st.warning("系統尚未啟用 OCR 功能")
        return
    
    # 統計
    pending_df = df[df['OCR_Status'] == 'pending']
    completed_df = df[df['OCR_Status'] == 'completed']
    failed_df = df[df['OCR_Status'] == 'failed']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("⏳ 待辨識", len(pending_df))
    
    with col2:
        st.metric("✅ 已完成", len(completed_df))
    
    with col3:
        st.metric("❌ 失敗", len(failed_df))
    
    st.markdown("---")
    
    # 待辨識列表
    if not pending_df.empty:
        st.markdown("### ⏳ 待辨識公文")
        
        for _, doc in pending_df.head(10).iterrows():
            col_info, col_action = st.columns([4, 1])
            
            with col_info:
                st.markdown(f"**{doc['ID']}** | {doc['Date']} | {doc['Agency']} | {doc['Subject'][:40]}...")
            
            with col_action:
                if st.button("🔄 立即辨識", key=f"ocr_{doc['ID']}"):
                    with st.spinner("辨識中..."):
                        file_id = doc.get('Drive_File_ID')
                        if file_id:
                            ocr_result = ocr_pdf_from_drive(drive_service, file_id)
                            if ocr_result:
                                update_ocr_result(docs_sheet, doc['ID'], ocr_result, "completed")
                                st.success("✅ 辨識完成！")
                                st.rerun()
                            else:
                                update_ocr_result(docs_sheet, doc['ID'], None, "failed")
                                st.error("❌ 辨識失敗")
        
        st.markdown("")
        if st.button("🔄 批次處理 (前 5 筆)", type="primary"):
            with st.spinner("批次辨識中..."):
                processed = process_pending_ocr(docs_sheet, drive_service, limit=5)
                st.success(f"✅ 已辨識 {processed} 份公文")
                st.rerun()
    else:
        st.success("✅ 所有公文已辨識完成")
    
    st.markdown("---")
    
    # 失敗列表
    if not failed_df.empty:
        st.markdown("### ❌ 辨識失敗公文")
        
        for _, doc in failed_df.iterrows():
            with st.expander(f"❌ {doc['ID']} | {doc['Agency']}"):
                st.markdown(f"**日期**: {doc['Date']}")
                st.markdown(f"**主旨**: {doc['Subject']}")
                
                if st.button("🔄 重新辨識", key=f"retry_{doc['ID']}"):
                    with st.spinner("辨識中..."):
                        file_id = doc.get('Drive_File_ID')
                        if file_id:
                            ocr_result = ocr_pdf_from_drive(drive_service, file_id)
                            if ocr_result:
                                update_ocr_result(docs_sheet, doc['ID'], ocr_result, "completed")
                                st.success("✅ 辨識完成！")
                                st.rerun()
                            else:
                                st.error("❌ 辨識仍然失敗，請檢查 PDF 品質")

# ===== 新增公文頁面 =====
def show_add_document_page(docs_sheet, drive_service, folder_id):
    """新增公文頁面 - 完整版"""
    
    st.markdown("## ➕ 新增公文")
    
    if 'form_key' not in st.session_state:
        st.session_state.form_key = 0
    
    # 步驟 1: 基本資訊
    st.markdown("### 📋 步驟 1: 基本資訊")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_input = st.date_input("📅 日期", datetime.now(), key=f"date_{st.session_state.form_key}")
        doc_type = st.selectbox("📋 公文類型", ["發文", "收文", "簽呈", "函"], key=f"type_{st.session_state.form_key}")
    
    with col2:
        agency = st.text_input("🏢 機關單位", placeholder="例：教育部", key=f"agency_{st.session_state.form_key}")
        subject = st.text_input("📝 主旨", placeholder="請輸入公文主旨", key=f"subject_{st.session_state.form_key}")
    
    st.markdown("---")
    
    # 步驟 2: 回覆設定
    st.markdown("### 🔗 步驟 2: 回覆設定")
    
    parent_id = None
    manual_doc_id = None
    use_manual_id = False
    
    # 如果是收文,提供兩種模式選擇
    if doc_type == "收文":
        st.info("💡 收文有兩種模式:政府機關回文(手動輸入文號) 或 我方回覆政府(系統產生文號)")
        
        doc_id_mode = st.radio(
            "請選擇文號來源:",
            ["政府機關回文 (手動輸入政府文號)", "我方針對政府回文再回覆 (使用系統流水號)"],
            key=f"doc_id_mode_{st.session_state.form_key}"
        )
        
        if doc_id_mode == "政府機關回文 (手動輸入政府文號)":
            # 模式1: 手動輸入政府文號
            use_manual_id = True
            manual_doc_id = st.text_input(
                "📝 請輸入政府機關的文號",
                placeholder="例：府教字第1130012345號",
                key=f"manual_id_{st.session_state.form_key}"
            )
            
            st.write("💡 請選擇這個政府回文是回覆我方的哪個公文:")
            
            parent_input_mode = st.radio(
                "選擇方式:",
                ["從近三個月公文選擇", "手動輸入文號"],
                key=f"parent_input_mode1_{st.session_state.form_key}"
            )
            
            if parent_input_mode == "從近三個月公文選擇":
                df = get_all_documents(docs_sheet)
                recent_df = filter_recent_documents(df, months=3)
                
                if not recent_df.empty:
                    doc_options = [
                        f"{row['ID']} | {row['Type']} | {row['Agency']} | {row['Subject'][:30]}..." 
                        for _, row in recent_df.iterrows()
                    ]
                    selected = st.selectbox(
                        "選擇原始公文（近三個月）", 
                        doc_options, 
                        key=f"parent_{st.session_state.form_key}"
                    )
                    parent_id = selected.split(" | ")[0] if selected else None
                    
                    if parent_id:
                        selected_doc = df[df['ID'] == parent_id].iloc[0]
                        st.success(f"✓ 回覆：**{parent_id}** - {selected_doc['Subject']}")
                else:
                    st.warning("近三個月沒有公文,請使用手動輸入")
            else:
                parent_id = st.text_input(
                    "📝 請輸入原始公文文號",
                    placeholder="例：金展詢1131215001",
                    key=f"parent_manual_{st.session_state.form_key}"
                )
                if parent_id:
                    st.success(f"✓ 回覆：**{parent_id}**")
        
        else:
            # 模式2: 使用系統流水號
            use_manual_id = False
            
            parent_input_mode = st.radio(
                "選擇要回覆的公文方式:",
                ["從近三個月公文選擇", "手動輸入文號"],
                key=f"parent_input_mode2_{st.session_state.form_key}"
            )
            
            if parent_input_mode == "從近三個月公文選擇":
                df = get_all_documents(docs_sheet)
                recent_df = filter_recent_documents(df, months=3)
                
                if not recent_df.empty:
                    st.info("💡 選擇要回覆的政府公文（系統將自動產生流水號）")
                    doc_options = [
                        f"{row['ID']} | {row['Type']} | {row['Agency']} | {row['Subject'][:30]}..." 
                        for _, row in recent_df.iterrows()
                    ]
                    selected = st.selectbox(
                        "選擇要回覆的公文（近三個月）", 
                        doc_options, 
                        key=f"parent_{st.session_state.form_key}"
                    )
                    parent_id = selected.split(" | ")[0] if selected else None
                    
                    if parent_id:
                        selected_doc = df[df['ID'] == parent_id].iloc[0]
                        st.success(f"✓ 將回覆：**{parent_id}** - {selected_doc['Subject']}")
                else:
                    st.warning("近三個月沒有公文,請使用手動輸入")
            else:
                st.info("💡 請先到「查詢公文」搜尋舊公文,找到後輸入文號")
                parent_id = st.text_input(
                    "📝 請輸入要回覆的公文文號",
                    placeholder="例：府教字第1130012345號",
                    key=f"parent_manual2_{st.session_state.form_key}"
                )
                if parent_id:
                    st.success(f"✓ 將回覆：**{parent_id}**")
    
    else:
        # 發文、函、簽呈等其他類型
        is_reply = st.checkbox("↩️ 這是回覆案件", key=f"reply_{st.session_state.form_key}")
        
        if is_reply:
            parent_input_mode = st.radio(
                "選擇要回覆的公文方式:",
                ["從近三個月公文選擇", "手動輸入文號"],
                key=f"parent_input_mode3_{st.session_state.form_key}"
            )
            
            if parent_input_mode == "從近三個月公文選擇":
                df = get_all_documents(docs_sheet)
                recent_df = filter_recent_documents(df, months=3)
                
                if not recent_df.empty:
                    st.info("💡 選擇要回覆的公文（可以是任何類型）")
                    doc_options = [
                        f"{row['ID']} | {row['Type']} | {row['Agency']} | {row['Subject'][:30]}..." 
                        for _, row in recent_df.iterrows()
                    ]
                    selected = st.selectbox(
                        "選擇原始公文（近三個月）", 
                        doc_options, 
                        key=f"parent_{st.session_state.form_key}"
                    )
                    parent_id = selected.split(" | ")[0] if selected else None
                    
                    if parent_id:
                        selected_doc = df[df['ID'] == parent_id].iloc[0]
                        st.success(f"✓ 將回覆：**{parent_id}** - {selected_doc['Subject']}")
                else:
                    st.warning("近三個月沒有公文,請使用手動輸入")
            else:
                st.info("💡 請先到「查詢公文」搜尋舊公文,找到後輸入文號")
                parent_id = st.text_input(
                    "📝 請輸入原始公文文號",
                    placeholder="例：金展詢1131215001 或 府教字第1130012345號",
                    key=f"parent_manual3_{st.session_state.form_key}"
                )
                if parent_id:
                    st.success(f"✓ 將回覆：**{parent_id}**")
    
    st.markdown("---")
    
    # 步驟 3: 上傳附件
    st.markdown("### 📎 步驟 3: 上傳附件")
    
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0
    uploaded_file = st.file_uploader("選擇 PDF 檔案", type=['pdf'], key=f"pdf_{st.session_state.uploader_key}")
    
    st.markdown("---")
    
    # 預覽文號
    date_str = date_input.strftime('%Y-%m-%d')
    final_doc_id = None
    
    if use_manual_id and manual_doc_id:
        final_doc_id = manual_doc_id
        st.info(f"### 📝 使用文號: `{final_doc_id}` (政府文號)")
    else:
        is_reply_for_generation = (doc_type != "收文" and parent_id) or (doc_type == "收文" and parent_id and not use_manual_id)
        preview_id = generate_document_id(docs_sheet, date_str, is_reply_for_generation, parent_id)
        final_doc_id = preview_id
        if preview_id:
            st.info(f"### 🔢 預覽流水號: `{preview_id}`")
    
    st.markdown("---")
    
    # 確認新增按鈕
    if st.button("✅ 確認新增", type="primary", use_container_width=True):
        if not folder_id:
            st.error("❌ 請先設定 Google Drive Folder ID")
        elif not subject or not agency:
            st.error("❌ 請填寫完整資料")
        elif use_manual_id and not manual_doc_id:
            st.error("❌ 請輸入政府機關的文號")
        elif not parent_id and (doc_type == "收文" or (doc_type in ["發文", "函", "簽呈"] and is_reply)):
            st.error("❌ 請選擇原始公文")
        elif not uploaded_file:
            st.error("❌ 請上傳 PDF 檔案")
        elif not final_doc_id:
            st.error("❌ 無法產生文號")
        else:
            with st.spinner("上傳中..."):
                file_bytes = uploaded_file.read()
                filename = f"{final_doc_id}_{agency}_{subject}.pdf"
                file_id = upload_to_drive(drive_service, file_bytes, filename, folder_id)
                
                if file_id:
                    doc_data = {
                        'id': final_doc_id,
                        'date': date_str,
                        'type': doc_type,
                        'agency': agency,
                        'subject': subject,
                        'parent_id': parent_id if parent_id else '',
                        'drive_file_id': file_id,
                        'created_at': datetime.now().isoformat(),
                        'created_by': st.session_state.user['display_name']
                    }
                    
                    if add_document_to_sheet(docs_sheet, doc_data):
                        st.success(f"✅ 公文新增成功！文號：{final_doc_id}")
                        st.balloons()
                        st.session_state.uploader_key += 1
                        st.session_state.form_key += 1
                        
                        # 返回首頁
                        if st.button("🏠 返回首頁"):
                            st.session_state.current_page = 'home'
                            st.rerun()
                else:
                    st.error("❌ 上傳失敗")

# ===== 查詢公文頁面 =====  
def show_search_page(docs_sheet, drive_service, deleted_sheet, deleted_folder_id, folder_id=None):
    """查詢公文頁面 - 完整版"""
    
    st.markdown("## 🔍 查詢公文")
    
    df = get_all_documents(docs_sheet)
    
    if df.empty:
        st.info("尚無公文資料")
        return
    
    # 搜尋表單
    st.markdown("### 📋 搜尋條件")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        search_date_start = st.date_input("📅 開始日期", value=None, key="search_date_start")
    
    with col2:
        search_date_end = st.date_input("📅 結束日期", value=None, key="search_date_end")
    
    with col3:
        search_agency = st.text_input("🏢 機關單位", placeholder="例：教育部", key="search_agency")
    
    with col4:
        search_type = st.selectbox("📋 公文類型", ["全部", "發文", "收文", "簽呈", "函"], key="search_type")
    
    search_keyword = st.text_input("🔍 關鍵字", placeholder="輸入關鍵字...", key="search_keyword")
    
    search_fulltext = st.checkbox(
        "📝 搜尋文字內容 (OCR辨識的文字)",
        value=False,
        key="search_fulltext",
        help="勾選後會搜尋 OCR 辨識的文字內容"
    )
    
    if st.button("🔎 搜尋", type="primary"):
        st.session_state.search_performed = True
    
    st.markdown("---")
    
    # 搜尋結果
    if 'search_performed' in st.session_state and st.session_state.search_performed:
        filtered_df = df.copy()
        
        # 日期篩選
        if search_date_start:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['Date']) >= pd.to_datetime(search_date_start)]
        if search_date_end:
            filtered_df = filtered_df[pd.to_datetime(filtered_df['Date']) <= pd.to_datetime(search_date_end)]
        
        # 機關篩選
        if search_agency:
            filtered_df = filtered_df[filtered_df['Agency'].str.contains(search_agency, case=False, na=False)]
        
        # 類型篩選
        if search_type != "全部":
            filtered_df = filtered_df[filtered_df['Type'] == search_type]
        
        # 關鍵字篩選
        if search_keyword:
            if search_fulltext and 'OCR_Text' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['OCR_Text'].str.contains(search_keyword, case=False, na=False)]
            else:
                filtered_df = filtered_df[filtered_df['Subject'].str.contains(search_keyword, case=False, na=False)]
        
        # 只顯示根節點（原始公文）
        root_docs = filtered_df[filtered_df['Parent_ID'].isna() | (filtered_df['Parent_ID'] == '')]
        
        st.subheader(f"📊 搜尋結果 (找到 {len(root_docs)} 筆原始公文)")
        
        if root_docs.empty:
            st.warning("沒有符合條件的公文")
        else:
            # 顯示每個原始公文
            for _, root_doc in root_docs.iterrows():
                with st.expander(f"📤 {root_doc['ID']} | {root_doc['Date']} | {root_doc['Agency']} | {root_doc['Subject'][:40]}...", expanded=False):
                    # 取得對話串
                    conversation = get_conversation_thread(df, root_doc['ID'])
                    
                    st.markdown(f"**對話串** ({len(conversation)} 筆):")
                    
                    for idx, doc in enumerate(conversation):
                        level = doc['level']
                        doc_data = doc['doc']
                        indent = "　" * level
                        
                        icon = "📤" if doc_data['Type'] in ['發文', '函'] else "📥"
                        
                        col_doc, col_btn = st.columns([4, 1])
                        with col_doc:
                            st.markdown(f"{indent}{icon} **{doc_data['ID']}** | {doc_data['Date']} | {doc_data['Type']} | {doc_data['Agency']}")
                        with col_btn:
                            if st.button("👁️ 查看", key=f"view_{doc_data['ID']}_{idx}"):
                                st.session_state.selected_doc_id = doc_data['ID']
                                st.session_state.show_detail = True
                                st.rerun()
                    
                    st.markdown("---")
                    
                    # AI 摘要功能
                    summary_key = f"summary_{root_doc['ID']}"
                    
                    if summary_key not in st.session_state:
                        # 顯示產生摘要按鈕
                        if st.button("🤖 產生 AI 摘要 (Gemini)", key=f"gen_summary_{root_doc['ID']}", use_container_width=True):
                            with st.spinner("🤖 AI 分析中..."):
                                # 建立 conversation_ids_tuple 用於快取
                                conv_ids = tuple([doc['id'] for doc in conversation])
                                
                                # 呼叫 Gemini API
                                summary = get_ai_summary(conv_ids, conversation)
                                
                                if summary:
                                    st.session_state[summary_key] = summary
                                    st.rerun()
                                else:
                                    st.error("❌ AI 摘要產生失敗。請確認已設定 GOOGLE_GEMINI_API_KEY")
                    else:
                        # 顯示已產生的摘要
                        st.markdown("### 🤖 AI 對話串摘要")
                        st.markdown(st.session_state[summary_key])
                        
                        # 清除摘要按鈕
                        if st.button("🗑️ 清除摘要", key=f"clear_summary_{root_doc['ID']}"):
                            del st.session_state[summary_key]
                            st.rerun()
    
    # 顯示詳細資訊
    if 'show_detail' in st.session_state and st.session_state.show_detail and 'selected_doc_id' in st.session_state:
        st.markdown("---")
        st.markdown("### 👁️ 公文詳細資訊")
        
        selected_id = st.session_state.selected_doc_id
        selected_row = df[df['ID'] == selected_id]
        
        if not selected_row.empty:
            selected_row = selected_row.iloc[0]
            
            col_info, col_action = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"**公文字號：** `{selected_row['ID']}`")
                st.markdown(f"**機關單位：** {selected_row['Agency']}")
                st.markdown(f"**類型：** {selected_row['Type']}")
                st.markdown(f"**主旨：** {selected_row['Subject']}")
                st.markdown(f"**日期：** {selected_row['Date']}")
                st.markdown(f"**建立者：** {selected_row.get('Created_By', '未知')}")
                
                if selected_row.get('Parent_ID'):
                    st.markdown(f"**回覆：** `{selected_row['Parent_ID']}`")
            
            with col_action:
                if st.button("❌ 關閉詳細資訊"):
                    st.session_state.show_detail = False
                    del st.session_state.selected_doc_id
                    st.rerun()
            
            st.markdown("---")
            
            # OCR 文字顯示
            ocr_status = selected_row.get('OCR_Status', 'pending')
            ocr_text = selected_row.get('OCR_Text', '')
            
            if ocr_status == 'completed' and ocr_text:
                with st.expander("📝 辨識文字內容", expanded=False):
                    st.text_area("文字內容 (可複製)", ocr_text, height=300, key=f"ocr_text_{selected_id}")
                    st.caption(f"辨識時間: {selected_row.get('OCR_Date', '未知')}")
            elif ocr_status == 'pending':
                st.info("⏳ 文字辨識中，請稍後查看...")
            elif ocr_status == 'failed':
                st.warning("❌ 文字辨識失敗")
            elif ocr_status == 'skipped':
                st.info("ℹ️ 此公文無附件，已跳過辨識")
            
            st.markdown("---")
            
            # PDF 預覽
            file_id = selected_row.get('Drive_File_ID')
            if file_id:
                st.markdown("### 📄 PDF 預覽")
                try:
                    pdf_bytes = download_from_drive(drive_service, file_id)
                    if pdf_bytes and PDF_PREVIEW_AVAILABLE:
                        display_pdf_from_bytes(pdf_bytes, f"預覽 - {selected_row['ID']}")
                    else:
                        st.info("PDF 預覽不可用")
                except Exception as e:
                    st.error(f"載入 PDF 失敗: {str(e)}")
            
            # 刪除功能
            st.markdown("---")
            with st.expander("⚠️ 刪除公文"):
                st.warning("刪除後將移至刪除紀錄，無法從前台復原！")
                
                confirm_text = st.text_input(
                    "請輸入公文字號以確認刪除",
                    placeholder=selected_row['ID'],
                    key=f"delete_confirm_{selected_id}"
                )
                
                if st.button("🗑️ 確認刪除", type="secondary", key=f"delete_btn_{selected_id}"):
                    if confirm_text == selected_row['ID']:
                        # 執行刪除
                        if soft_delete_document(docs_sheet, deleted_sheet, selected_row['ID'], st.session_state.user['display_name']):
                            # 移動檔案到刪除資料夾
                            if file_id and deleted_folder_id:
                                try:
                                    drive_service.files().update(
                                        fileId=file_id,
                                        addParents=deleted_folder_id,
                                        removeParents=','.join([p for p in [folder_id] if p]),
                                        fields='id, parents'
                                    ).execute()
                                except:
                                    pass
                            
                            st.success("✅ 公文已刪除")
                            st.session_state.show_detail = False
                            del st.session_state.selected_doc_id
                            st.rerun()
                    else:
                        st.error("❌ 公文字號不符，刪除失敗")

# ===== 系統管理頁面 =====
def show_admin_page(docs_sheet, deleted_sheet, users_sheet):
    """系統管理頁面 - 完整版"""
    
    st.markdown("## 📊 系統管理")
    
    # 功能選擇
    admin_tab = st.radio(
        "選擇功能",
        ["👥 使用者管理", "🗑️ 刪除紀錄"],
        horizontal=True
    )
    
    st.markdown("---")
    
    if admin_tab == "👥 使用者管理":
        user_management_page(users_sheet)
    
    elif admin_tab == "🗑️ 刪除紀錄":
        st.markdown("### 🗑️ 刪除紀錄")
        
        deleted_df = get_deleted_documents(deleted_sheet)
        
        if deleted_df.empty:
            st.info("無刪除紀錄")
        else:
            st.dataframe(
                deleted_df[['ID', 'Date', 'Type', 'Agency', 'Subject', 'Deleted_At', 'Deleted_By']],
                use_container_width=True
            )
            
            st.caption(f"共 {len(deleted_df)} 筆刪除紀錄")

# ===== 以下是舊版 tabs 介面 (備用) =====

if __name__ == "__main__":
    main()
