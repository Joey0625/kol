from __future__ import annotations


VERTICAL_TERMS = ("一番", "抽赏", "抽獎", "手办", "手辦", "模型", "公仔", "卡牌", "pokemon", "ptcg", "盲盒", "潮玩", "玩具", "扭蛋", "动漫", "二次元", "gk", "beyblade")
MINOR_TERMS = ("儿童", "兒童", "亲子", "親子", "小朋友", "kids", "儿童玩具")


def calculate_score(profile: dict) -> tuple[int, str, bool]:
    tags_text = " ".join(profile.get("tags", []) + profile.get("matched_keywords", [])).casefold()
    vertical_hits = sum(1 for term in VERTICAL_TERMS if term in tags_text)
    relevance = min(35, 8 + vertical_hits * 5) if vertical_hits else 5
    region_points = {"高": 20, "中": 14, "低": 6}.get(profile.get("region_confidence"), 0)
    activity = min(15, int(profile.get("posts_90", 0)) * 3)
    views = profile.get("avg_views", 0)
    view_points = 15 if views >= 100000 else 11 if views >= 30000 else 7 if views >= 5000 else 3
    engagement = profile.get("engagement_rate", 0)
    engagement_points = 10 if engagement >= 0.06 else 7 if engagement >= 0.03 else 3
    contact_points = 5 if profile.get("contacts") else 0
    score = min(100, relevance + region_points + activity + view_points + engagement_points + contact_points)
    reasons = [f"内容相关性 {relevance}/35", f"地区可信度 {region_points}/20", f"活跃度 {activity}/15", f"观看表现 {view_points}/15", f"互动表现 {engagement_points}/10"]
    if contact_points:
        reasons.append("含公开联系入口 +5")
    if profile.get("promotion_status") == "已推广过潮流勁抽":
        reasons.append("存量合作/竞品排除待人工判断")
    minor_risk = any(term in tags_text for term in MINOR_TERMS)
    return score, "；".join(reasons), minor_risk
