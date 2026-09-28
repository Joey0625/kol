from __future__ import annotations

from datetime import datetime, timedelta

from .keywords import keyword_hits
from .promotion import find_promotion
from .region import decide_region
from .scoring import calculate_score


def _video(title: str, days: int, views: int, description: str = "", suffix: str = "") -> dict:
    return {"title": title, "url": f"https://www.youtube.com/watch?v=demo{suffix}{days}", "published_at": (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"), "views": views, "likes": int(views * 0.055), "comments": int(views * 0.008), "description": description}


def _make(channel_id: str, name: str, description: str, videos: list[dict], subscribers: int, contacts: list[str], all_keywords: list[str]) -> dict:
    region = decide_region(description, " ".join(v["title"] + " " + v["description"] for v in videos), " ".join(contacts))
    promo = find_promotion(name, description, videos)
    tags = keyword_hits(description + " " + " ".join(v["title"] for v in videos), all_keywords)
    posts = sum(1 for v in videos if (datetime.now() - datetime.strptime(v["published_at"], "%Y-%m-%d")).days <= 90)
    avg_views = int(sum(v["views"] for v in videos) / len(videos))
    engagement = sum(v["likes"] + v["comments"] for v in videos) / max(1, sum(v["views"] for v in videos))
    profile = {
        "channel_id": channel_id, "channel_name": name, "channel_url": f"https://www.youtube.com/channel/{channel_id}", "description": description,
        "region": region["region"], "region_confidence": region["confidence"], "region_basis": region["basis"],
        "tags": tags, "matched_keywords": tags, "subscribers": subscribers, "total_videos": 168, "posts_90": posts, "avg_views": avg_views,
        "engagement_rate": round(engagement, 4), "contacts": contacts, "promotion_status": promo["status"], "evidence": promo["evidence"],
        "checked_at": promo["checked_at"], "scanned_videos": promo["scanned_videos"], "review_status": "待联系", "note": "", "favorite": False,
        "source": "内置演示数据（非真实合作结论）", "sourced_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "videos": videos,
    }
    profile["score"], profile["score_reason"], profile["minor_risk"] = calculate_score(profile)
    return profile


def profiles(keywords: list[str]) -> list[dict]:
    return [
        _make("DEMO_TW_TOY", "台北玩具研究所", "台湾台北的公仔、GK 模型与一番賞開箱频道。商务合作：toy.lab@example.com Instagram: https://instagram.com/toylabtw", [
            _video("潮流勁抽一番賞開箱，抽到隐藏款", 8, 82600, "本集合作资讯：gachafashion.com，使用优惠码 TOYLAB", "a"),
            _video("台北模型展战利品与GK开箱", 25, 42300, "", "a"), _video("宝可梦 PSA 卡牌送评开箱", 57, 67300, "", "a"),
        ], 128000, ["toy.lab@example.com", "Instagram: @toylabtw"], keywords),
        _make("DEMO_HK_CARD", "港玩卡牌日誌", "香港频道，主要分享 Pokemon PSA、PTCG 开箱及卡牌收藏。商业查询 hello@hkcardlog.example", [
            _video("香港卡店寻宝：Pokemon PSA 开箱", 12, 38400, "", "b"), _video("PTCG 新系列拆包实测", 31, 29600, "", "b"), _video("球星卡开箱：这张值得送评吗", 70, 25100, "", "b"),
        ], 76400, ["hello@hkcardlog.example", "Facebook: 港玩卡牌日誌"], keywords),
        _make("DEMO_TW_FAMILY", "小宅开箱日", "住在高雄的家庭 Vlog，亲子玩具试玩、盲盒和礼物开箱。合作邮箱 familybox@example.com", [
            _video("亲子盲盒开箱，孩子最喜欢哪一款", 4, 52900, "", "c"), _video("高雄玩具展战利品开箱", 22, 31300, "", "c"), _video("儿童玩具试玩日", 66, 22500, "", "c"),
        ], 93400, ["familybox@example.com"], keywords),
        _make("DEMO_UNCONFIRMED", "模型开箱频道", "繁体中文模型、手办与动漫周边开箱。", [
            _video("最新手办模型开箱", 15, 18000, "", "d"), _video("宅物开箱清单", 49, 15300, "", "d"),
        ], 42000, [], keywords),
    ]
