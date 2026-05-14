"""
视频分析管线：抽帧 → AI识别 → 返回产品列表
"""
import cv2
import base64
import os
import json
import uuid
from datetime import datetime
from openai import OpenAI

from config import API_KEY, BASE_URL, MODEL, QUICK_TEST_FRAMES, build_prompt


def extract_frames(video_path: str, output_dir: str, interval: int = 30):
    """从视频中按间隔抽帧，yield (时间戳秒数, 文件路径)"""
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频文件: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = int(total_frames / fps)

    for sec in range(0, duration_sec, interval):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = cap.read()
        if ret:
            filename = f"frame_{sec//60:02d}m{sec%60:02d}s.jpg"
            filepath = os.path.join(output_dir, filename)
            cv2.imwrite(filepath, frame)
            yield sec, filepath

    cap.release()


def format_timestamp(seconds: int) -> str:
    """秒数转为 mm:ss 格式"""
    return f"{seconds//60:02d}:{seconds%60:02d}"


def analyze_frame(client: OpenAI, filepath: str, timestamp: str, prompt: str) -> list:
    """用多模态模型分析单帧，返回产品列表"""
    with open(filepath, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )

    raw = resp.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]

    products = json.loads(raw)
    for p in products:
        p["时间戳"] = timestamp
        p["截图"] = filepath
    return products


def check_api_health() -> dict:
    """检测 API 连接状态"""
    try:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": "你好，请回复OK"}],
            max_tokens=10,
        )
        return {"status": "ok", "model": MODEL, "response": resp.choices[0].message.content.strip()}
    except Exception as e:
        return {"status": "error", "model": MODEL, "base_url": BASE_URL, "error": str(e)}


def run_pipeline(video_path: str, target_market: str = "日本",
                 interval: int = 30, quick_test: bool = False,
                 progress_callback=None):
    """
    运行完整分析管线（生成器）
    yield {"type": "progress"|"product"|"done", ...}
    """
    analysis_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    frames_dir = os.path.join("frames", analysis_id)
    os.makedirs("data", exist_ok=True)

    prompt = build_prompt(target_market)
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    # Step 1: 抽帧
    all_frames = list(extract_frames(video_path, frames_dir, interval))
    total_frames = len(all_frames)
    max_frames = QUICK_TEST_FRAMES if quick_test else total_frames

    frames_to_process = all_frames[:max_frames]

    yield {"type": "info", "total_frames": len(frames_to_process), "analysis_id": analysis_id}

    # Step 2: 逐帧分析
    all_products = []

    for idx, (sec, filepath) in enumerate(frames_to_process):
        timestamp = format_timestamp(sec)

        try:
            products = analyze_frame(client, filepath, timestamp, prompt)
            all_products.extend(products)

            yield {
                "type": "frame_done",
                "current": idx + 1,
                "total": len(frames_to_process),
                "timestamp": timestamp,
                "filepath": filepath,
                "count": len(products)
            }
        except Exception as e:
            yield {
                "type": "frame_error",
                "current": idx + 1,
                "total": len(frames_to_process),
                "timestamp": timestamp,
                "error": str(e)
            }

    # Step 3: 保存原始结果
    raw_path = os.path.join("data", f"{analysis_id}_raw.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)

    yield {
        "type": "done",
        "products": all_products,
        "analysis_id": analysis_id,
        "raw_path": raw_path,
        "frames_dir": frames_dir,
        "video_name": os.path.basename(video_path),
    }
