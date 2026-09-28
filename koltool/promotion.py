from __future__ import annotations

from datetime import datetime

PROMOTION_TERMS = ("gachafashion.com", "gacha fashion", "潮流勁抽", "潮流劲抽")


def find_promotion(channel_name: str, channel_description: str, videos: list[dict]) -> dict:
    evidence: list[dict] = []
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    channel_text = f"{channel_name}\n{channel_description}".casefold()
    channel_hits = [term for term in PROMOTION_TERMS if term.casefold() in channel_text]
    if channel_hits:
        evidence.append({"title": "频道公开资料", "url": "", "excerpt": channel_description[:180], "hits": channel_hits, "found_at": checked_at})
    for video in videos:
        text = f"{video.get('title', '')}\n{video.get('description', '')}".casefold()
        hits = [term for term in PROMOTION_TERMS if term.casefold() in text]
        if hits:
            evidence.append({
                "title": video.get("title", "公开视频"), "url": video.get("url", ""),
                "excerpt": video.get("description", "")[:180], "hits": hits, "found_at": checked_at,
            })
    return {
        "status": "已推广过潮流勁抽" if evidence else "未发现推广过潮流勁抽",
        "evidence": evidence,
        "checked_at": checked_at,
        "scanned_videos": len(videos),
    }
