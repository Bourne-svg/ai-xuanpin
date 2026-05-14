"""
AI跨境选品系统 - 主入口
启动: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="AI跨境选品系统",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 多页导航：Streamlit会自动扫描 pages/ 目录
# pages/1_新建分析.py  → 默认页
# pages/2_历史分析.py  → 侧边栏"历史分析"

# 首页重定向到新建分析页
pg = st.navigation([
    st.Page("pages/1_新建分析.py", title="新建分析", icon="🔍"),
    st.Page("pages/2_历史分析.py", title="历史记录", icon="📋"),
])
pg.run()
