"""
产品聚合工具：去重、统计、排序
"""
import re
from collections import Counter


def normalize_name(name: str) -> str:
    """标准化产品名称：去除括号内的变体描述，提取核心名称"""
    name = name.strip()
    name = re.sub(r"[（(][^)）]*[)）]", "", name)  # 去括号
    name = re.sub(r"（.*?）", "", name)
    return name.strip()


def get_keywords(name: str) -> set:
    """提取产品名称中的关键词"""
    name = normalize_name(name)
    # 简单分词：按常见分隔符
    parts = re.split(r"[，,、/／\s]+", name)
    keywords = set()
    for p in parts:
        p = p.strip()
        if len(p) >= 2:
            keywords.add(p)
    return keywords


def is_similar(name1: str, name2: str) -> bool:
    """判断两个产品名称是否指向同一产品"""
    kw1 = get_keywords(name1)
    kw2 = get_keywords(name2)
    if not kw1 or not kw2:
        return False
    # Jaccard相似度
    intersection = kw1 & kw2
    union = kw1 | kw2
    return len(intersection) / len(union) >= 0.4


def deduplicate(products: list) -> list:
    """
    产品去重：将相似产品合并，保留最高评分的版本
    返回去重后的产品列表，每个产品附带出现次数和时间戳列表
    """
    if not products:
        return []

    # 按名称分组
    groups = []
    used = set()

    for i, p1 in enumerate(products):
        if i in used:
            continue
        group = {"product": p1, "indices": [i]}
        used.add(i)

        for j, p2 in enumerate(products):
            if j in used:
                continue
            if is_similar(p1.get("产品名称", ""), p2.get("产品名称", "")):
                group["indices"].append(j)
                used.add(j)
        groups.append(group)

    # 合并每组
    merged = []
    for g in groups:
        items = [products[i] for i in g["indices"]]
        # 取评分最高的版本
        best = max(items, key=lambda p: (
            p.get("市场需求度", 0) + p.get("差异化空间", 0) + p.get("物流可行性", 0)
        ))
        # 收集所有时间戳
        timestamps = sorted(set(p.get("时间戳", "") for p in items))
        screenshots = list(set(p.get("截图", "") for p in items))

        best["出现次数"] = len(items)
        best["时间戳列表"] = timestamps
        best["截图列表"] = screenshots
        best["出现频率"] = f"{len(items)}次"
        merged.append(best)

    # 按综合评分排序
    merged.sort(
        key=lambda p: (
            p.get("市场需求度", 0) + p.get("差异化空间", 0) + p.get("物流可行性", 0)
        ),
        reverse=True
    )

    return merged


def get_statistics(products: list) -> dict:
    """生成统计摘要"""
    if not products:
        return {"总数": 0, "高潜力": 0, "中潜力": 0, "低潜力": 0, "类别分布": {}}

    categories = Counter(p.get("类别", "其他") for p in products)
    ratings = Counter(p.get("综合评级", "中") for p in products)

    return {
        "总数": len(products),
        "高潜力": ratings.get("高", 0),
        "中潜力": ratings.get("中", 0),
        "低潜力": ratings.get("低", 0),
        "类别分布": dict(categories.most_common()),
    }
