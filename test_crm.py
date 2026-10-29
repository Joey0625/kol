import sqlite3

from koltool.database import Database, GALAXY_TAG
from koltool.scoring import assess_target


def profile(channel_id="channel-1", **extra):
    result = {
        "channel_id": channel_id, "channel_name": "潮玩开箱实验室", "channel_url": "https://youtube.example/channel",
        "description": "台湾公仔、模型、盲盒开箱频道", "region": "台湾", "region_confidence": "高", "region_basis": "频道资料",
        "tags": ["公仔", "盲盒"], "matched_keywords": ["公仔"], "subscribers": 20000, "total_videos": 100,
        "posts_90": 6, "avg_views": 12000, "engagement_rate": 0.05, "contacts": [], "promotion_status": "未发现推广过潮流勁抽",
        "evidence": [], "checked_at": "", "scanned_videos": 10, "score": 80, "score_reason": "测试", "review_status": "未处理",
        "note": "", "favorite": False, "minor_risk": False, "source": "测试", "sourced_at": "2026-01-01", "videos": [],
    }
    result.update(extra)
    return result


def test_existing_database_migrates_status_without_losing_profile(tmp_path):
    path = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE profiles (channel_id TEXT PRIMARY KEY, channel_name TEXT, channel_url TEXT, description TEXT, region TEXT, region_confidence TEXT, region_basis TEXT, tags TEXT, matched_keywords TEXT, subscribers INTEGER, total_videos INTEGER, posts_90 INTEGER, avg_views INTEGER, engagement_rate REAL, contacts TEXT, promotion_status TEXT, evidence TEXT, checked_at TEXT, scanned_videos INTEGER, score INTEGER, score_reason TEXT, review_status TEXT, note TEXT, favorite INTEGER, minor_risk INTEGER, source TEXT, sourced_at TEXT, videos TEXT)")
    conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("CREATE TABLE keyword_groups (name TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE keywords (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, term TEXT, normalized TEXT UNIQUE)")
    conn.execute("INSERT INTO profiles VALUES (?, ?, ?, '', '台湾', '高', '', '[]', '[]', 0, 0, 0, 0, 0, '[]', '', '[]', '', 0, 0, '', '已合作', '保留备注', 0, 0, '', '', '[]')", ("legacy", "旧档案", "https://example.com"))
    conn.commit(); conn.close()
    db = Database(path)
    migrated = db.get_profile("legacy")
    assert migrated["workflow_status"] == "已合作"
    assert migrated["note"] == "保留备注"


def test_galaxy_tag_and_manual_review_survive_research(tmp_path):
    db = Database(tmp_path / "crm.sqlite")
    db.upsert_profile(profile())
    db.update_review("channel-1", ["公仔", GALAXY_TAG], 91, "银河潮赏", "重点跟进", True)
    db.upsert_profile(profile(score=30, tags=["盲盒"]))
    saved = db.get_profile("channel-1")
    assert saved["workflow_status"] == "银河潮赏"
    assert GALAXY_TAG in saved["tags"]
    assert saved["note"] == "重点跟进" and saved["favorite"]
    assert db.processed_channel_ids() == {"channel-1"}


def test_target_assessment_rejects_news_and_english_teaching():
    eligible, _, _, reason = assess_target(profile(channel_name="英语新闻学习", description="英语教学与国际新闻", tags=[]))
    assert not eligible
    assert "排除内容" in reason

