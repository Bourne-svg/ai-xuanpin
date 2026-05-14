"""
AI跨境选品 - 历史分析记录页
"""
import streamlit as st
import os
import json
from datetime import datetime

SAVE_DIR = "data"


def load_all_results():
    """加载所有历史分析结果"""
    if not os.path.exists(SAVE_DIR):
        return []

    results = []
    for fname in sorted(os.listdir(SAVE_DIR), reverse=True):
        if fname.endswith("_result.json"):
            try:
                with open(os.path.join(SAVE_DIR, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append(data)
            except Exception:
                continue
    return results


st.title("📋 历史分析记录")

# 加载所有记录
all_results = load_all_results()

if not all_results:
    st.info("暂无历史分析记录。去「新建分析」页开始第一次分析吧！")
    st.stop()

# 历史列表
st.subheader(f"共 {len(all_results)} 条分析记录")

for i, result in enumerate(all_results):
    ts = result.get("timestamp", "")
    try:
        dt = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
    except Exception:
        dt = ts

    stats = result.get("stats", {})
    with st.container(border=True):
        cols = st.columns([3, 1, 1, 1, 1, 1.5])
        cols[0].markdown(f"**{result.get('video_name', '未知视频')}**")
        cols[0].caption(f"📅 {dt} | 市场: {result.get('target_market', '?')}")

        cols[1].metric("总数", stats.get("总数", "?"))
        cols[2].metric("高", stats.get("高潜力", "?"))
        cols[3].metric("中", stats.get("中潜力", "?"))
        cols[4].metric("类", len(stats.get("类别分布", {})))

        if cols[5].button("查看详情", key=f"view_{i}"):
            st.session_state.selected_history = result

if "selected_history" not in st.session_state:
    st.session_state.selected_history = None

# 显示选中记录的详细结果
if st.session_state.selected_history:
    st.divider()
    result = st.session_state.selected_history

    st.subheader(f"📊 {result.get('video_name', '未知视频')} — 详细结果")
    st.caption(f"分析时间: {result.get('timestamp', '?')} | 目标市场: {result.get('target_market', '?')}")

    products = result.get("products", [])
    stats = result.get("stats", {})
    frames_dir = result.get("frames_dir", "")

    # 统计
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("产品总数", stats.get("总数", 0))
    c2.metric("高潜力", stats.get("高潜力", 0))
    c3.metric("中潜力", stats.get("中潜力", 0))
    c4.metric("类别数", len(stats.get("类别分布", {})))

    # 产品表格
    with st.expander("查看完整产品列表", expanded=True):
        for i, p in enumerate(products):
            rating = p.get("综合评级", "?")
            emoji = {"高": "🟢", "中": "🟡", "低": "🔴"}.get(rating, "⚪")

            cols = st.columns([3, 1, 1, 1, 1])
            cols[0].markdown(f"**{i+1}. {p.get('产品名称', '?')}** {emoji}")
            cols[1].markdown(f"`{p.get('类别', '?')}`")
            cols[2].metric("需求", p.get("市场需求度", "?"))
            cols[3].metric("差异", p.get("差异化空间", "?"))
            cols[4].metric("物流", p.get("物流可行性", "?"))
            st.caption(f"💡 {p.get('选品建议', '')}")

    if st.button("清除详情", use_container_width=True):
        st.session_state.selected_history = None
        st.rerun()
