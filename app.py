import streamlit as st

st.set_page_config(
    page_title="Team Document System",
    page_icon="📄",
    layout="wide"
)

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
                       'Drive_File_ID', 'Created_At', 'Created_By', 'Status']
        docs_sheet = _spreadsheet.add_worksheet(title='公文資料', rows=1000, cols=20)
        docs_sheet.append_row(doc_headers)
        time.sleep(1)
    else:
        docs_sheet = _spreadsheet.worksheet('公文資料')
    
    # 刪除紀錄表
    if '刪除紀錄' not in existing_sheets:
        deleted_headers = ['ID', 'Date', 'Type', 'Agency', 'Subject', 'Parent_ID',
                           'Drive_File_ID', 'Created_At', 'Created_By', 'Deleted_At', 'Deleted_By']
        deleted_sheet = _spreadsheet.add_worksheet(title='刪除紀錄', rows=1000, cols=20)
        deleted_sheet.append_row(deleted_headers)
        time.sleep(1)
    else:
        deleted_sheet = _spreadsheet.worksheet('刪除紀錄')
    
    # 使用者資料表
    if '使用者' not in existing_sheets:
        user_headers = ['Username', 'Password', 'Display_Name', 'Role', 'Created_At']
        users_sheet = _spreadsheet.add_worksheet(title='使用者', rows=1000, cols=20)
        users_sheet.append_row(user_headers)
        time.sleep(1)
        
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
                return f"{date_code}001"
            else:
                return None
        
        if is_reply and parent_id:
            reply_count = len(df[df['Parent_ID'].astype(str) == str(parent_id)])
            new_reply_number = str(reply_count + 2).zfill(2)
            doc_id = f"{new_reply_number}{parent_id}"
        else:
            date_code = date_str.replace('-', '')
            same_day_docs = df[
                (df['ID'].astype(str).str.startswith(date_code)) & 
                (df['ID'].astype(str).str.len() == 11)
            ]
            next_serial = str(len(same_day_docs) + 1).zfill(3)
            doc_id = f"{date_code}{next_serial}"
        
        return doc_id
    except Exception as e:
        date_code = date_str.replace('-', '')
        return f"{date_code}001"

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
            'active'
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
                    
                    st.image(img_bytes, caption=f"第 {page_num + 1} 頁", use_container_width=True)
                
                if len(doc) > 10:
                    st.info("⚠️ 僅顯示前 10 頁，完整文件請下載查看")
                doc.close()
            except Exception as e:
                st.warning(f"PDF 預覽失敗: {str(e)}")
        else:
            st.info("📄 請使用下載按鈕查看 PDF")
    except Exception as e:
        st.error(f"處理 PDF 失敗: {str(e)}")

# ===== 登入頁面 =====
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
    
    # 初始化 Google Services
    gc, drive_service, credentials = init_google_services()
    
    # 從 secrets 讀取設定
    sheet_id = st.secrets.get("SHEET_ID", "") if "SHEET_ID" in st.secrets else ""
    folder_id = st.secrets.get("DRIVE_FOLDER_ID", "") if "DRIVE_FOLDER_ID" in st.secrets else ""
    
    if not sheet_id:
        st.error("❌ 請在 Secrets 設定 SHEET_ID")
        st.stop()
    
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
    
    # 登入檢查
    if not st.session_state.logged_in:
        login_page(users_sheet)
        return
    
    # ===== 已登入的主介面 =====
    
    # 側邊欄
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['display_name']}")
        st.caption(f"角色：{'管理員' if is_admin() else '一般使用者'}")
        
        if st.button("🚪 登出", width="stretch"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        st.markdown("---")
        
        st.header("⚙️ 系統設定")
        
        if not folder_id:
            st.warning("⚠️ 請在 Secrets 設定 DRIVE_FOLDER_ID")
        else:
            st.success("✅ 資料夾已設定")
            st.caption("刪除的檔案會自動移到「已刪除公文」子資料夾")
    
    # 主標題
    st.title("📄 團隊版政府公文追蹤系統")
    st.markdown("---")
    
    # 根據角色顯示不同頁籤
    if is_admin():
        tabs = st.tabs(["➕ 新增公文", "🔍 查詢預覽", "📊 刪除紀錄", "👥 使用者管理"])
    else:
        tabs = st.tabs(["➕ 新增公文", "🔍 查詢預覽", "📊 刪除紀錄"])
    
    # ===== 新增公文頁籤 =====
    with tabs[0]:
        st.header("新增公文資料")
        
        if 'form_key' not in st.session_state:
            st.session_state.form_key = 0
        
        col1, col2 = st.columns(2)
        
        with col1:
            date_input = st.date_input("📅 日期", datetime.now(), key=f"date_{st.session_state.form_key}")
            doc_type = st.selectbox("📋 公文類型", ["發文", "收文", "簽呈", "函"], key=f"type_{st.session_state.form_key}")
            agency = st.text_input("🏢 機關單位", placeholder="例：人事處", key=f"agency_{st.session_state.form_key}")
        
        with col2:
            subject = st.text_input("📝 主旨", placeholder="請輸入公文主旨", key=f"subject_{st.session_state.form_key}")
        
        st.markdown("---")
        
        is_reply = st.checkbox("↩️ 這是回覆案件", key=f"reply_{st.session_state.form_key}")
        parent_id = None
        
        if is_reply:
            df = get_all_documents(docs_sheet)
            if not df.empty:
                doc_options = [f"{row['ID']} - {row['Subject']}" for _, row in df.iterrows()]
                selected = st.selectbox("選擇原始公文", doc_options, key=f"parent_{st.session_state.form_key}")
                parent_id = selected.split(" - ")[0] if selected else None
            else:
                st.warning("目前沒有可回覆的公文")
        
        st.markdown("---")
        
        st.subheader("📎 上傳 PDF 附件")
        if 'uploader_key' not in st.session_state:
            st.session_state.uploader_key = 0
        uploaded_file = st.file_uploader("選擇 PDF 檔案", type=['pdf'], key=f"pdf_{st.session_state.uploader_key}")
        
        st.markdown("---")
        
        date_str = date_input.strftime('%Y-%m-%d')
        preview_id = generate_document_id(docs_sheet, date_str, is_reply, parent_id)
        
        if preview_id:
            st.info(f"### 🔢 預覽流水號: `{preview_id}`")
        
        st.markdown("---")
        
        if st.button("✅ 確認新增", type="primary", width="stretch"):
            if not folder_id:
                st.error("❌ 請先設定 Google Drive Folder ID")
            elif not subject or not agency:
                st.error("❌ 請填寫完整資料")
            elif is_reply and not parent_id:
                st.error("❌ 請選擇原始公文")
            elif not uploaded_file:
                st.error("❌ 請上傳 PDF 檔案")
            else:
                with st.spinner("上傳中..."):
                    file_bytes = uploaded_file.read()
                    filename = f"{preview_id}_{agency}_{subject}.pdf"
                    file_id = upload_to_drive(drive_service, file_bytes, filename, folder_id)
                    
                    if file_id:
                        doc_data = {
                            'id': preview_id,
                            'date': date_str,
                            'type': doc_type,
                            'agency': agency,
                            'subject': subject,
                            'parent_id': parent_id,
                            'drive_file_id': file_id,
                            'created_at': datetime.now().isoformat(),
                            'created_by': st.session_state.user['display_name']
                        }
                        
                        if add_document_to_sheet(docs_sheet, doc_data):
                            st.success(f"✅ 公文新增成功！流水號：{preview_id}")
                            st.balloons()
                            st.session_state.uploader_key += 1
                            st.session_state.form_key += 1
                            st.rerun()
                    else:
                        st.error("❌ 上傳失敗")
        
        st.markdown("---")
        
        # 公文列表
        st.header("📚 公文列表")
        df = get_all_documents(docs_sheet)
        
        if df.empty:
            st.info("尚無公文資料")
        else:
            def get_status(row):
                if check_needs_tracking(df, row['ID'], row['Type'], row['Date']):
                    days = (datetime.now() - datetime.strptime(row['Date'], '%Y-%m-%d')).days
                    return f"🔴 待追蹤({days}天)"
                return "✅ 正常"
            
            display_cols = ['ID', 'Date', 'Type', 'Agency', 'Subject', 'Created_By']
            df_display = df[display_cols].copy()
            df_display['狀態'] = df.apply(get_status, axis=1)
            df_display.columns = ['流水號', '日期', '類型', '機關', '主旨', '建立者', '狀態']
            
            tracking_count = len(df_display[df_display['狀態'].str.contains('待追蹤')])
            if tracking_count > 0:
                st.warning(f"⚠️ 有 {tracking_count} 筆發文超過 7 天未收到回覆")
            
            st.dataframe(df_display, width="stretch", hide_index=True)
    
    # ===== 查詢預覽頁籤 =====
    with tabs[1]:
        st.header("查詢與預覽")
        
        df = get_all_documents(docs_sheet)
        
        if df.empty:
            st.info("尚無公文資料")
        else:
            left_col, right_col = st.columns([1, 2])
            
            with left_col:
                st.subheader("📋 公文清單")
                
                for idx, row in df.iterrows():
                    doc_id = row['ID']
                    subject = row['Subject']
                    agency = row['Agency']
                    doc_type = row['Type']
                    created_by = row.get('Created_By', '未知')
                    
                    button_label = f"**{doc_id}**\n{agency} | {doc_type}\n{subject[:20]}...\n👤 {created_by}"
                    
                    if st.button(button_label, key=f"select_{doc_id}", width="stretch"):
                        st.session_state.selected_doc_id = doc_id
                
                st.markdown("---")
                st.caption(f"共 {len(df)} 筆公文")
            
            with right_col:
                st.subheader("👁️ 文件資訊")
                
                if 'selected_doc_id' not in st.session_state:
                    st.info("👈 請從左側選擇公文")
                else:
                    selected_id = st.session_state.selected_doc_id
                    selected_row = df[df['ID'] == selected_id]
                    
                    if selected_row.empty:
                        st.warning("找不到此公文")
                        del st.session_state.selected_doc_id
                    else:
                        selected_row = selected_row.iloc[0]
                        
                        st.markdown(f"**公文字號：** `{selected_row['ID']}`")
                        st.markdown(f"**機關單位：** {selected_row['Agency']}")
                        st.markdown(f"**類型：** {selected_row['Type']}")
                        st.markdown(f"**主旨：** {selected_row['Subject']}")
                        st.markdown(f"**日期：** {selected_row['Date']}")
                        st.markdown(f"**建立者：** {selected_row.get('Created_By', '未知')}")
                        
                        if selected_row.get('Parent_ID'):
                            st.markdown(f"**回覆：** `{selected_row['Parent_ID']}`")
                        
                        st.markdown("---")
                        
                        # 刪除功能
                        with st.expander("⚠️ 刪除公文"):
                            st.warning("刪除後將移至刪除紀錄，無法從前台復原！")
                            
                            confirm_text = st.text_input(
                                f"請輸入公文字號 `{selected_id}` 以確認：",
                                key="delete_confirm"
                            )
                            
                            if st.button("🗑️ 確認刪除", type="secondary"):
                                if confirm_text == selected_id:
                                    drive_file_id = selected_row.get('Drive_File_ID')
                                    
                                    # 移動 PDF 到刪除資料夾
                                    if drive_file_id and deleted_folder_id:
                                        move_file_to_folder(drive_service, drive_file_id, deleted_folder_id)
                                    
                                    # 軟刪除（移到刪除紀錄）
                                    if soft_delete_document(docs_sheet, deleted_sheet, selected_id, 
                                                           st.session_state.user['display_name']):
                                        st.success(f"✅ 公文 {selected_id} 已刪除")
                                        del st.session_state.selected_doc_id
                                        st.rerun()
                                else:
                                    st.error("❌ 輸入的公文字號不正確")
            
            # PDF 預覽（全寬）
            if 'selected_doc_id' in st.session_state:
                selected_id = st.session_state.selected_doc_id
                selected_row = df[df['ID'] == selected_id]
                
                if not selected_row.empty:
                    selected_row = selected_row.iloc[0]
                    drive_file_id = selected_row.get('Drive_File_ID')
                    
                    st.markdown("---")
                    st.subheader("📄 PDF 預覽")
                    
                    if drive_file_id:
                        with st.spinner("載入中..."):
                            pdf_bytes = download_from_drive(drive_service, drive_file_id)
                            if pdf_bytes:
                                # 使用使用者名稱作為浮水印
                                watermark = st.session_state.user['display_name']
                                display_pdf_from_bytes(pdf_bytes, watermark)
                            else:
                                st.error("無法載入 PDF")
                    else:
                        st.warning("📋 此公文無附件")
    
    # ===== 刪除紀錄頁籤 =====
    with tabs[2]:
        st.header("📊 刪除紀錄")
        
        try:
            deleted_values = deleted_sheet.get_all_values()
            if len(deleted_values) <= 1:
                st.info("尚無刪除紀錄")
            else:
                headers = deleted_values[0]
                data = deleted_values[1:]
                deleted_df = pd.DataFrame(data, columns=headers)
                
                display_cols = ['ID', 'Date', 'Type', 'Agency', 'Subject', 'Created_By', 'Deleted_At', 'Deleted_By']
                deleted_df = deleted_df[[c for c in display_cols if c in deleted_df.columns]]
                deleted_df.columns = ['流水號', '日期', '類型', '機關', '主旨', '建立者', '刪除時間', '刪除者'][:len(deleted_df.columns)]
                
                st.dataframe(deleted_df, width="stretch", hide_index=True)
        except Exception as e:
            st.error(f"讀取刪除紀錄失敗: {str(e)}")
    
    # ===== 使用者管理頁籤（僅管理員）=====
    if is_admin():
        with tabs[3]:
            user_management_page(users_sheet)
    
    # 底部資訊
    st.markdown("---")
    st.info("""
    ### 📌 系統說明
    - **登入系統：** 需要帳號密碼才能使用
    - **權限管理：** 管理員可新增/刪除使用者
    - **刪除紀錄：** 刪除的公文會保留在紀錄中
    - **追蹤提醒：** 發文超過 7 天未收到回覆會標示紅色
    """)

if __name__ == "__main__":
    main()
