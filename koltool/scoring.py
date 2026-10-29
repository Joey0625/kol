from __future__ import annotations


VERTICAL_TERMS = ("一番", "抽赏", "抽獎", "手办", "手辦", "模型", "公仔", "卡牌", "pokemon", "ptcg", "盲盒", "潮玩", "玩具", "扭蛋", "动漫", "二次元", "gk", "beyblade")
MINOR_TERMS = ("儿童", "兒童", "亲子", "親子", "小朋友", "kids", "儿童玩具")
EXCLUDED_CONTENT_TERMS = ("新闻", "新聞", "news", "时事", "時事", "英语教学", "英文教学", "english learning", "ielts", "托福", "雅思", "单词", "文法")


def profile_text(profile: dict) -> str:
    videos = profile.get("videos", [])
    video_text = " ".join(f"{video.get('title', '')} {video.get('description', '')}" for video in videos)
    return " ".join([profile.get("channel_name", ""), profile.get("description", ""), video_text, *profile.get("tags", []), *profile.get("matched_keywords", [])]).casefold()


def assess_target(profile: dict) -> tuple[bool, str, int, str]:
    """Return eligibility, content type, quality score and explanation.

    YouTube's public API has no demographic data, so audience fit is a
    transparent proxy based on target-language and regional signals, not a
    claim about a channel's actual audience.
    """
    text = profile_text(profile)
    excluded = [term for term in EXCLUDED_CONTENT_TERMS if term in text]
    vertical_hits = [term for term in VERTICAL_TERMS if term in text]
    if excluded and len(vertical_hits) < 2:
        return False, "非目标内容", 0, f"排除内容：{'、'.join(excluded[:3])}"
    if not vertical_hits:
        return False, "非目标内容", 0, "未命中潮玩、卡牌、模型或开箱等目标领域关键词"
    content_type = "卡牌" if any(term in text for term in ("卡牌", "pokemon", "ptcg", "psa")) else "潮玩/手办" if any(term in text for term in ("手办", "手辦", "模型", "公仔", "盲盒", "潮玩", "gk")) else "玩具/开箱"
    content_points = min(40, 18 + len(vertical_hits) * 5)
    audience_points = {"高": 20, "中": 15, "低": 8}.get(profile.get("region_confidence"), 0)
    account_points = min(20, (8 if profile.get("posts_90", 0) >= 2 else 2) + (12 if profile.get("avg_views", 0) >= 5000 else 6))
    history_points = 20 if profile.get("workflow_status") == "已合作" else 8 if profile.get("promotion_status") == "已推广过潮流勁抽" else 0
    score = min(100, content_points + audience_points + account_points + history_points)
    reason = f"内容 {content_points}/40；受众代理 {audience_points}/20；账号表现 {account_points}/20；历史合作价值 {history_points}/20"
    return True, content_type, score, reason


def calculate_score(profile: dict) -> tuple[int, str, bool]:
    tags_text = profile_text(profile)
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
