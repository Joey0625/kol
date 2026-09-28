from __future__ import annotations

import os
import re
from datetime import datetime, timezone

import requests

from .keywords import keyword_hits
from .promotion import find_promotion
from .region import decide_region
from .scoring import calculate_score


class YouTubeApiError(RuntimeError):
    pass


class YouTubeClient:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY", "")
        if not self.api_key:
            raise YouTubeApiError("尚未配置 YouTube API Key；请在“设置”中填写，或启用演示数据模式。")
        self.session = requests.Session()

    def _get(self, endpoint: str, **params) -> dict:
        response = self.session.get(f"{self.BASE_URL}/{endpoint}", params={**params, "key": self.api_key}, timeout=20)
        if not response.ok:
            message = response.text[:300]
            raise YouTubeApiError(f"YouTube API 请求失败（{response.status_code}）：{message}")
        return response.json()

    def discover(self, keywords: list[str], region_code: str, limit: int, search_mode: str, query: str = "") -> list[dict]:
        queries = [query.strip()] if query.strip() else keywords
        channel_ids: list[str] = []
        for term in queries[:20]:
            results = self._get("search", part="snippet", q=term, type="video", regionCode=region_code, relevanceLanguage="zh-Hant", maxResults=min(10, limit))
            for item in results.get("items", []):
                channel_id = item.get("snippet", {}).get("channelId")
                if channel_id and channel_id not in channel_ids:
                    channel_ids.append(channel_id)
                if len(channel_ids) >= limit:
                    break
            if len(channel_ids) >= limit:
                break
        if search_mode == "频道" and query.strip():
            results = self._get("search", part="snippet", q=query.strip(), type="channel", regionCode=region_code, relevanceLanguage="zh-Hant", maxResults=min(25, limit))
            channel_ids = [item["id"]["channelId"] for item in results.get("items", []) if item.get("id", {}).get("channelId")]
        return self._hydrate(channel_ids[:limit], keywords)

    def _hydrate(self, channel_ids: list[str], keywords: list[str]) -> list[dict]:
        output: list[dict] = []
        for start in range(0, len(channel_ids), 50):
            channel_data = self._get("channels", part="snippet,statistics,contentDetails", id=",".join(channel_ids[start:start + 50]))
            for item in channel_data.get("items", []):
                snippet = item["snippet"]
                uploads = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")
                videos = self._recent_videos(uploads)
                profile = self._to_profile(item, videos, keywords)
                output.append(profile)
        return output

    def _recent_videos(self, playlist_id: str) -> list[dict]:
        if not playlist_id:
            return []
        playlist = self._get("playlistItems", part="snippet,contentDetails", playlistId=playlist_id, maxResults=10)
        ids = [item["contentDetails"].get("videoId") for item in playlist.get("items", []) if item.get("contentDetails", {}).get("videoId")]
        if not ids:
            return []
        stats = self._get("videos", part="snippet,statistics", id=",".join(ids))
        result = []
        for item in stats.get("items", []):
            snippet, stat = item["snippet"], item.get("statistics", {})
            result.append({"title": snippet["title"], "url": f"https://www.youtube.com/watch?v={item['id']}", "published_at": snippet.get("publishedAt", "")[:10], "views": int(stat.get("viewCount", 0)), "likes": int(stat.get("likeCount", 0)), "comments": int(stat.get("commentCount", 0)), "description": snippet.get("description", "")})
        return result

    @staticmethod
    def _contacts(text: str) -> list[str]:
        contacts = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        contacts.extend(re.findall(r"https?://(?:www\.)?(?:instagram\.com|facebook\.com)/[^\s)]+", text, re.I))
        return list(dict.fromkeys(contacts))

    def _to_profile(self, item: dict, videos: list[dict], keywords: list[str]) -> dict:
        snippet, stats = item["snippet"], item.get("statistics", {})
        desc = snippet.get("description", "")
        video_text = " ".join(v["title"] + " " + v["description"] for v in videos)
        contacts = self._contacts(desc)
        region = decide_region(desc, video_text, " ".join(contacts))
        promo = find_promotion(snippet["title"], desc, videos)
        cutoff = datetime.now(timezone.utc).timestamp() - 90 * 86400
        recent = [v for v in videos if _timestamp(v["published_at"]) >= cutoff]
        avg_views = int(sum(v["views"] for v in videos) / len(videos)) if videos else 0
        total_views = sum(v["views"] for v in videos)
        engagement = sum(v["likes"] + v["comments"] for v in videos) / total_views if total_views else 0
        profile = {
            "channel_id": item["id"], "channel_name": snippet["title"], "channel_url": f"https://www.youtube.com/channel/{item['id']}", "description": desc,
            "region": region["region"], "region_confidence": region["confidence"], "region_basis": region["basis"], "tags": keyword_hits(desc + " " + video_text, keywords),
            "matched_keywords": keyword_hits(desc + " " + video_text, keywords), "subscribers": int(stats.get("subscriberCount", 0)), "total_videos": int(stats.get("videoCount", 0)),
            "posts_90": len(recent), "avg_views": avg_views, "engagement_rate": round(engagement, 4), "contacts": contacts,
            "promotion_status": promo["status"], "evidence": promo["evidence"], "checked_at": promo["checked_at"], "scanned_videos": promo["scanned_videos"],
            "review_status": "待联系", "note": "", "favorite": False, "source": "YouTube Data API v3（公开频道与视频元数据）", "sourced_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "videos": videos[:5],
        }
        profile["score"], profile["score_reason"], profile["minor_risk"] = calculate_score(profile)
        return profile


def _timestamp(value: str) -> float:
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0
