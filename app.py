"""政府公文追蹤系統 - 主程式 (修正版 v2.1.1)"""
import sys
import os

# 1. 路徑防呆：確保專案根目錄在 sys.path 中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import streamlit as st
from src.config.settings import Settings
from src.config.constants import UIConstants
from src.data_access.google_sheets import (
    DocumentRepository,
    UserRepository,
    DeletedDocumentRepository
)
from src.data_access.google_drive import DriveRepository
from src.services.auth_service import AuthService
from src.services.document_service import DocumentService
from src.services.tracking_service import TrackingService
from src.ui.pages.home import HomePage
from src.ui.pages.add_document import AddDocumentPage
from src.ui.pages.search import SearchPage
from src.ui.pages.tracking import TrackingPage
from src.ui.pages.ocr import OCRPage
from src.ui.pages.admin import AdminPage
from src.ui.styles.theme import Theme

# 頁面設定
st.set_page_config(
    page_title="政府公文追蹤系統",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_repositories():
    """初始化所有 Repository"""
    sheets_config = Settings.load_google_sheets_config()
    drive_config = Settings.load_google_drive_config()
    credentials = Settings.load_gcp_credentials().credentials_dict
    
    doc_repo = DocumentRepository(sheets_config, credentials)
    user_repo = UserRepository(sheets_config, credentials)
    deleted_repo = DeletedDocumentRepository(sheets_config, credentials)
    drive_repo = DriveRepository(drive_config, credentials)
    
    return doc_repo, user_repo, deleted_repo, drive_repo

def render_sidebar(auth_service):
    """渲染側邊欄"""
    with st.sidebar:
        user = auth_service.get_current_user()
        
        if user:
            st.markdown(f"### 👤 {user['display_name']}")
            st.caption(f"角色: {user['role']}")
            
            if st.button("🚪 登出", use_container_width=True):
                auth_service.logout()
                st.rerun()
            
            st.markdown("---")
            st.markdown("### 📌 快速導航")
            
            nav_items = [
                ("🏠 首頁", UIConstants.PAGE_HOME),
                ("➕ 新增公文", UIConstants.PAGE_ADD_DOCUMENT),
                ("🔍 查詢公文", UIConstants.PAGE_SEARCH),
                ("⏰ 追蹤回覆", UIConstants.PAGE_TRACKING),
                ("📝 處理辨識", UIConstants.PAGE_OCR)
            ]
            
            for label, page_key in nav_items:
                if st.button(label, key=f"nav_{page_key}", use_container_width=True):
                    st.session_state[UIConstants.SESSION_CURRENT_PAGE] = page_key
                    st.rerun()
            
            if auth_service.is_admin():
                st.markdown("---")
                if st.button("📊 系統管理", key="nav_admin", use_container_width=True):
                    st.session_state[UIConstants.SESSION_CURRENT_PAGE] = UIConstants.PAGE_ADMIN
                    st.rerun()

def main():
    """主程式"""
    try:
        doc_repo, user_repo, deleted_repo, drive_repo = initialize_repositories()
        auth_service = AuthService(user_repo)
        
        if not auth_service.is_authenticated():
            auth_service.render_login_page()
            return
        
        st.markdown(Theme.get_global_css(), unsafe_allow_html=True)
        render_sidebar(auth_service)
        
        st.markdown("# 📋 政府公文追蹤系統")
        st.caption("v2.1.1 - 穩定修正版")
        st.markdown("---")
        
        current_page = st.session_state.get(
            UIConstants.SESSION_CURRENT_PAGE,
            UIConstants.PAGE_HOME
        )
        
        # 路由邏輯修正
        if current_page == UIConstants.PAGE_HOME:
            # 修正處：HomePage 內部會自己初始化 TrackingService，只需要傳入 doc_repo
            HomePage(doc_repo).render()
            
        elif current_page == UIConstants.PAGE_ADD_DOCUMENT:
            AddDocumentPage(DocumentService(doc_repo)).render()
            
        elif current_page == UIConstants.PAGE_SEARCH:
            SearchPage(DocumentService(doc_repo)).render()
            
        elif current_page == UIConstants.PAGE_TRACKING:
            TrackingPage(TrackingService(doc_repo)).render()
            
        elif current_page == UIConstants.PAGE_OCR:
            OCRPage().render()
            
        elif current_page == UIConstants.PAGE_ADMIN:
            AdminPage(auth_service, user_repo).render()
    
    except Exception as e:
        st.error(f"❌ 系統錯誤: {str(e)}")
        # 在開發階段印出詳細錯誤，方便 Debug
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
