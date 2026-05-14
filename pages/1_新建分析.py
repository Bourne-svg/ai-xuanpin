"""
AI跨境选品 - 新建分析页
"""
import streamlit as st
import os
import json
import tempfile
import base64
from datetime import datetime

from config import MARKETS, DEFAULT_INTERVAL, QUICK_TEST_FRAMES, API_KEY, BASE_URL, MODEL
from pipeline import run_pipeline, format_timestamp, check_api_health
from utils.aggregator import deduplicate, get_statistics
from utils.exporter import to_excel

SAVE_DIR = "data"

# ==================== 初始化 Session State ====================
if "analysis_running" not in st.session_state:
    st.session_state.analysis_running = False
if "results" not in st.session_state:
    st.session_state.results = None
if "stats" not in st.session_state:
    st.session_state.stats = None


# ==================== 页面标题 ====================
st.title("🛒 AI跨境电商选品系统")
st.caption("上传目标市场的生活纪录片 → AI自动识别可出口产品 → 选品清单+评分")

col1, col2 = st.columns([1, 1], gap="large")

# ==================== 左栏：视频输入 + 配置 ====================
with col1:
    st.subheader("📤 视频输入")

    input_method = st.radio("视频来源", ["上传本地文件", "粘贴URL"], horizontal=True, label_visibility="collapsed")

    video_path = None
    if input_method == "上传本地文件":
        uploaded = st.file_uploader("选择视频文件", type=["mp4", "avi", "mov", "mkv", "webm"])
        if uploaded:
            os.makedirs("uploads", exist_ok=True)
            video_path = os.path.join("uploads", uploaded.name)
            with open(video_path, "wb") as f:
                f.write(uploaded.getbuffer())
            st.success(f"已加载: {uploaded.name}")
    else:
        url = st.text_input("粘贴B站/YouTube视频URL", placeholder="https://www.bilibili.com/video/BV...")
        if url:
            st.info("URL下载功能请在本地使用 yt-dlp 下载后上传")

    st.subheader("⚙️ 分析设置")
    target_market = st.selectbox("目标市场", list(MARKETS.keys()))
    interval = st.slider("抽帧间隔(秒)", 10, 60, DEFAULT_INTERVAL, 5,
                         help="间隔越短分析越细致，但耗时越长")
    quick_test = st.checkbox("快速测试模式(仅分析3帧)", value=False,
                              help="勾选后只分析前3帧，用于快速验证")

    market_features = MARKETS.get(target_market, MARKETS["日本"])
    with st.expander(f"📋 {target_market}市场特征"):
        for f in market_features["特征"]:
            st.write(f"- {f}")

    # API 连接诊断
    with st.expander("🔧 系统诊断"):
        if st.button("检测API连接"):
            with st.spinner("检测中..."):
                health = check_api_health()
                if health["status"] == "ok":
                    st.success(f"API连接正常 - 模型: {health['model']} - 响应: {health['response']}")
                else:
                    st.error(f"API连接失败: {health['error']}")
                    st.info(f"Base URL: {health['base_url']}")

    start_btn = st.button("🚀 开始分析", type="primary", use_container_width=True,
                          disabled=(video_path is None and input_method != "上传本地文件"))

    # ==================== 进度显示 ====================
    if start_btn and video_path:
        st.session_state.analysis_running = True
        st.session_state.results = None

    if st.session_state.analysis_running and video_path:
        st.subheader("📊 分析进度")
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.container(height=300)

        all_products = []
        frames_dir = ""
        video_name = ""

        try:
            for update in run_pipeline(
                video_path, target_market, interval, quick_test,
            ):
                if update["type"] == "info":
                    total = update["total_frames"]
                    video_name = os.path.basename(video_path)
                    status_text.text(f"准备分析 {total} 帧...")

                elif update["type"] == "frame_done":
                    idx, total = update["current"], update["total"]
                    progress_bar.progress(idx / total)
                    status_text.text(f"正在分析: 第 {idx}/{total} 帧 [{update['timestamp']}] — 找到 {update['count']} 个产品")
                    with log_container:
                        st.write(f"✅ [{update['timestamp']}] 找到 {update['count']} 个产品")

                elif update["type"] == "frame_error":
                    idx, total = update["current"], update["total"]
                    progress_bar.progress(idx / total)
                    err_msg = update.get("error", "未知错误")
                    tb = update.get("traceback", "")
                    with log_container:
                        st.error(f"❌ [{update['timestamp']}] 失败 | 错误: {err_msg}")
                        if tb:
                            with st.expander(f"查看详细错误 [{update['timestamp']}]"):
                                st.code(tb)

                elif update["type"] == "done":
                    progress_bar.progress(1.0)
                    status_text.text("✅ 分析完成！")
                    all_products = update["products"]
                    frames_dir = update["frames_dir"]
                    video_name = update.get("video_name", "")
                    analysis_id = update["analysis_id"]

                    # 去重 + 统计
                    deduped = deduplicate(all_products)
                    stats = get_statistics(deduped)

                    # 保存结果
                    result = {
                        "analysis_id": analysis_id,
                        "video_name": video_name,
                        "target_market": target_market,
                        "timestamp": datetime.now().isoformat(),
                        "products": deduped,
                        "stats": stats,
                        "frames_dir": frames_dir,
                    }
                    result_path = os.path.join(SAVE_DIR, f"{analysis_id}_result.json")
                    with open(result_path, "w", encoding="utf-8") as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)

                    st.session_state.results = result
                    st.session_state.stats = stats
                    st.session_state.analysis_running = False

        except Exception as e:
            st.error(f"分析失败: {e}")
            st.session_state.analysis_running = False

# ==================== 右栏：结果展示 ====================
with col2:
    st.subheader("📊 分析结果")

    if st.session_state.results:
        result = st.session_state.results
        products = result["products"]
        stats = result["stats"]
        frames_dir = result.get("frames_dir", "")

        # 统计卡片
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("产品总数", stats["总数"])
        c2.metric("高潜力", stats["高潜力"])
        c3.metric("中潜力", stats["中潜力"])
        c4.metric("类别数", len(stats.get("类别分布", {})))

        # 筛选
        filt_col1, filt_col2, filt_col3 = st.columns([1, 1, 1.5])
        with filt_col1:
            cat_filter = st.selectbox("类别筛选", ["全部"] + list(stats.get("类别分布", {}).keys()))
        with filt_col2:
            rating_filter = st.selectbox("评级筛选", ["全部", "高", "中", "低"])
        with filt_col3:
            search = st.text_input("搜索产品", placeholder="输入关键词...")

        # 导出Excel
        excel_data = to_excel(products, stats, result.get("video_name", ""))
        st.download_button(
            "📥 导出Excel报告",
            data=excel_data,
            file_name=f"选品报告_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # 过滤
        filtered = products
        if cat_filter != "全部":
            filtered = [p for p in filtered if p.get("类别") == cat_filter]
        if rating_filter != "全部":
            filtered = [p for p in filtered if p.get("综合评级") == rating_filter]
        if search:
            filtered = [p for p in filtered if search.lower() in p.get("产品名称", "").lower()]

        st.caption(f"显示 {len(filtered)}/{len(products)} 个产品")

        # 产品列表
        for i, p in enumerate(filtered):
            scores = f"需求{p.get('市场需求度','?')}/差异{p.get('差异化空间','?')}/物流{p.get('物流可行性','?')}"
            rating = p.get("综合评级", "?")
            emoji = {"高": "🟢", "中": "🟡", "低": "🔴"}.get(rating, "⚪")

            with st.container(border=True):
                top_row = st.columns([4, 1, 1])
                top_row[0].markdown(f"**{i+1}. {p.get('产品名称', '?')}**  {emoji}{rating}")
                top_row[1].markdown(f"类别: `{p.get('类别', '?')}`")
                top_row[2].markdown(f"出现: {p.get('出现频率', '1次')}")

                mid_row = st.columns([1, 1, 1])
                mid_row[0].metric("市场需求度", p.get("市场需求度", "?"))
                mid_row[1].metric("差异化空间", p.get("差异化空间", "?"))
                mid_row[2].metric("物流可行性", p.get("物流可行性", "?"))

                st.caption(f"💡 {p.get('选品建议', '')}")

                # 展开查看截图
                with st.expander(f"📷 画面证据 ({len(p.get('截图列表', [p.get('截图','')]))}张截图)"):
                    screenshots = p.get("截图列表", [p.get("截图", "")])
                    timestamps = p.get("时间戳列表", [p.get("时间戳", "")])
                    cols = st.columns(min(len(screenshots), 3))
                    for j, (s, t) in enumerate(zip(screenshots, timestamps)):
                        if os.path.exists(s):
                            cols[j % 3].image(s, caption=f"🕐 {t}", use_container_width=True)
    else:
        if not st.session_state.analysis_running:
            st.info('上传视频并点击「开始分析」查看结果')
