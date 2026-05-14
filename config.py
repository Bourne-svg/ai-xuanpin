"""
配置文件：API Key、模型参数、选品Prompt
"""
import os

# ============ API配置 ============
# 注意：部署到 Streamlit Cloud 时在 Settings → Secrets 中设置 GLM_API_KEY

_HARDCODED_KEY = "f921c032b8644508a9cf0e527b85dcf7.Dqblov49GuqO1Wln"

def _is_valid_key(key: str) -> bool:
    """检查 key 是否看起来像真的 API Key（排除占位文本）"""
    if not key or len(key) < 20:
        return False
    # 包含中文肯定不对
    if any(ord(c) > 127 for c in key):
        return False
    return True

def get_api_key():
    """读取 API Key：Cloud Secrets → 环境变量 → 内置默认值"""
    try:
        import streamlit as st
        val = st.secrets.get("GLM_API_KEY", "")
        if _is_valid_key(val):
            return val
    except Exception:
        pass

    val = os.getenv("GLM_API_KEY", "")
    if _is_valid_key(val):
        return val

    return _HARDCODED_KEY

API_KEY = get_api_key()
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MODEL = "glm-4.6v"

# ============ 分析配置 ============
DEFAULT_INTERVAL = 30         # 默认抽帧间隔(秒)
QUICK_TEST_FRAMES = 3         # 快速测试只分析前3帧

# ============ 目标市场配置 ============
MARKETS = {
    "日本": {
        "特征": [
            "小户型住宅多，收纳需求旺盛",
            "独居/少子化/老龄化趋势明显，一人食、适老化产品有市场",
            "消费者品质要求高，注重产品细节和包装",
            "百元店文化盛行，性价比敏感",
            "厨房空间小，小型厨具/多功能工具受欢迎",
        ]
    },
    "韩国": {
        "特征": [
            "单身经济发达，一人食产品需求大",
            "颜值经济，产品外观设计至关重要",
            "便利店文化盛行，即食/便捷产品受欢迎",
            "公寓居住为主，小型家电需求高",
        ]
    },
    "东南亚": {
        "特征": [
            "气候炎热潮湿，清凉/防晒/防潮产品需求大",
            "年轻人口多，社交媒体驱动的消费趋势明显",
            "摩托车文化，便携/车载用品有市场",
            "价格敏感度较高，性价比是关键",
        ]
    },
    "欧美": {
        "特征": [
            "DIY文化盛行，工具类/手工类产品需求大",
            "环保意识强，可持续/可降解产品受欢迎",
            "大户型住宅，大型收纳/花园用品有市场",
            "宠物经济发达，宠物用品是刚需",
        ]
    },
}

# ============ 选品分析Prompt ============

def build_prompt(target_market: str) -> str:
    """根据目标市场生成选品分析Prompt"""
    market_info = MARKETS.get(target_market, MARKETS["日本"])
    features_text = "\n".join(f"- {f}" for f in market_info["特征"])

    return f"""你是跨境电商选品专家。
业务场景：中国卖家从国内供应链采购商品，销售给{target_market}消费者。
数据来源：关于{target_market}当地生活的纪录片画面截图，展示的是当地人真实的日常生活和消费场景。
你的价值：从画面中发现{target_market}市场的真实消费需求，为中国卖家推荐可出口的选品方向。

=== 重要：什么才算"产品" ===
✅ 是产品：可在中国工厂生产、可包装运输的实物商品（厨具、餐具、小家电、收纳用品、清洁工具、日用杂货、纺织品、家居装饰品等）
❌ 不是产品：新鲜食材、餐厅菜品/菜单项、现场服务、人物、纯装饰物

=== 打分标准 ===
对每个识别到的产品，在三个维度上打分（1-5分）：

【市场需求度】这个产品在{target_market}消费者中的需求程度
5分={target_market}家庭刚需高频消费品
3分=有一定需求但非必需
1分=几乎无需求

【差异化空间】中国供应链相比{target_market}本土产品的竞争优势
5分=中国制造有明显成本或设计优势
3分=有一定差异但竞品众多
1分={target_market}本土产品已完全覆盖，无空间

【物流可行性】跨境运输的实际操作难度
5分=小件轻量、耐运输、无特殊法规限制
3分=有一定物流门槛（如易碎、中等体积）
1分=几乎无法跨境销售（如新鲜食品、超大件）

综合评级规则：三维度平均分 >= 4为"高"，3.0-3.9为"中"，<3为"低"

=== {target_market}市场参考特征 ===
{features_text}

=== 输出格式 ===
只输出JSON数组，不要任何其他文字：
[
  {{
    "产品名称": "具体产品名称",
    "类别": "厨房用品/餐具/小家电/收纳用品/清洁工具/日用杂货/纺织品/家居装饰/个人护理/户外用品/其他",
    "画面场景": "产品在画面中的具体使用场景（一句话）",
    "市场需求度": 4,
    "差异化空间": 5,
    "物流可行性": 5,
    "综合评级": "高",
    "选品建议": "基于三维度分析的具体选品建议（30字以内）"
  }}
]
画面中无产品时返回 []。"""
