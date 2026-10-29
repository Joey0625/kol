from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .keywords import DEFAULT_KEYWORDS, dedupe_keywords


JSON_FIELDS = {"tags", "matched_keywords", "contacts", "videos", "evidence"}
WORKFLOW_STATUSES = ("未处理", "已查看", "已联系", "已合作", "不联系", "银河潮赏")
GALAXY_TAG = "银河潮赏"

PROFILE_DEFAULTS = {
    "workflow_status": "未处理", "content_type": "待判定", "exclusion_reason": "",
}


class Database:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        self._seed_keywords()

    def _create_schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS keyword_groups (name TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS keywords (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT NOT NULL, term TEXT NOT NULL, normalized TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS profiles (
          channel_id TEXT PRIMARY KEY, channel_name TEXT NOT NULL, channel_url TEXT NOT NULL, description TEXT DEFAULT '',
          region TEXT NOT NULL, region_confidence TEXT NOT NULL, region_basis TEXT NOT NULL,
          tags TEXT NOT NULL, matched_keywords TEXT NOT NULL, subscribers INTEGER DEFAULT 0, total_videos INTEGER DEFAULT 0,
          posts_90 INTEGER DEFAULT 0, avg_views INTEGER DEFAULT 0, engagement_rate REAL DEFAULT 0,
          contacts TEXT NOT NULL, promotion_status TEXT NOT NULL, evidence TEXT NOT NULL,
          checked_at TEXT DEFAULT '', scanned_videos INTEGER DEFAULT 0, score INTEGER DEFAULT 0, score_reason TEXT DEFAULT '',
          review_status TEXT DEFAULT '待联系', note TEXT DEFAULT '', favorite INTEGER DEFAULT 0, minor_risk INTEGER DEFAULT 0,
          source TEXT DEFAULT '演示数据', sourced_at TEXT DEFAULT '', videos TEXT NOT NULL,
          workflow_status TEXT NOT NULL DEFAULT '未处理', content_type TEXT DEFAULT '待判定', exclusion_reason TEXT DEFAULT ''
        );
        """)
        # SQLite's CREATE TABLE IF NOT EXISTS does not add new columns to an
        # existing local database.  These migrations keep all prior records.
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(profiles)")}
        for name, definition in {
            "workflow_status": "TEXT NOT NULL DEFAULT '未处理'",
            "content_type": "TEXT DEFAULT '待判定'",
            "exclusion_reason": "TEXT DEFAULT ''",
        }.items():
            if name not in existing:
                self.conn.execute(f"ALTER TABLE profiles ADD COLUMN {name} {definition}")
        if not self.get_setting("workflow_status_migrated"):
            self.conn.execute("""
                UPDATE profiles SET workflow_status=CASE review_status
                    WHEN '已联系' THEN '已联系'
                    WHEN '已回复' THEN '已联系'
                    WHEN '已合作' THEN '已合作'
                    WHEN '不合作' THEN '不联系'
                    WHEN '待联系' THEN '已查看'
                    ELSE '未处理' END
            """)
            self.set_setting("workflow_status_migrated", "1")
        self.conn.commit()

    def _seed_keywords(self) -> None:
        if self.conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]:
            return
        for group, terms in DEFAULT_KEYWORDS.items():
            self.conn.execute("INSERT OR IGNORE INTO keyword_groups(name) VALUES (?)", (group,))
            for term in dedupe_keywords(terms):
                self.conn.execute("INSERT OR IGNORE INTO keywords(group_name, term, normalized) VALUES (?, ?, ?)", (group, term, term.casefold().replace(" ", "")))
        self.conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute("INSERT INTO settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self.conn.commit()

    def keyword_groups(self) -> list[str]:
        return [row[0] for row in self.conn.execute("SELECT name FROM keyword_groups ORDER BY name")]

    def keywords(self) -> dict[str, list[str]]:
        rows = self.conn.execute("SELECT group_name, term FROM keywords ORDER BY group_name, id").fetchall()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(row["group_name"], []).append(row["term"])
        return result

    def add_keywords(self, group: str, terms: list[str]) -> None:
        self.conn.execute("INSERT OR IGNORE INTO keyword_groups(name) VALUES (?)", (group.strip(),))
        for term in dedupe_keywords(terms):
            normalized = term.casefold().replace(" ", "")
            self.conn.execute("INSERT OR IGNORE INTO keywords(group_name,term,normalized) VALUES (?,?,?)", (group.strip(), term, normalized))
        self.conn.commit()

    def delete_keyword(self, term: str) -> None:
        self.conn.execute("DELETE FROM keywords WHERE term=?", (term,))
        self.conn.commit()

    def upsert_profile(self, profile: dict) -> None:
        data = profile.copy()
        data.pop("eligible", None)  # search-only field, not persisted
        existing = self.get_profile(data["channel_id"])
        for name, value in PROFILE_DEFAULTS.items():
            data.setdefault(name, value)
        # Re-searching enriches public metrics but must never erase a human
        # decision, note, favourite marker, or manually added tag.
        if existing:
            data["tags"] = list(dict.fromkeys(existing["tags"] + data.get("tags", [])))
            for name in ("workflow_status", "review_status", "note", "favorite"):
                data[name] = existing[name]
        if data["workflow_status"] == GALAXY_TAG and GALAXY_TAG not in data["tags"]:
            data["tags"].append(GALAXY_TAG)
        for field in JSON_FIELDS:
            data[field] = json.dumps(data.get(field, []), ensure_ascii=False)
        columns = list(data.keys())
        marks = ", ".join("?" for _ in columns)
        update = ", ".join(f"{name}=excluded.{name}" for name in columns if name != "channel_id")
        self.conn.execute(f"INSERT INTO profiles ({', '.join(columns)}) VALUES ({marks}) ON CONFLICT(channel_id) DO UPDATE SET {update}", [data[name] for name in columns])
        self.conn.commit()

    def get_profiles(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM profiles ORDER BY score DESC, channel_name COLLATE NOCASE").fetchall()
        return [self._row_to_profile(row) for row in rows]

    def get_profile(self, channel_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM profiles WHERE channel_id=?", (channel_id,)).fetchone()
        return self._row_to_profile(row) if row else None

    def processed_channel_ids(self) -> set[str]:
        rows = self.conn.execute("SELECT channel_id FROM profiles WHERE workflow_status != '未处理'").fetchall()
        return {row[0] for row in rows}

    def update_review(self, channel_id: str, tags: list[str], score: int, workflow_status: str, note: str, favorite: bool) -> None:
        if workflow_status not in WORKFLOW_STATUSES:
            raise ValueError(f"未知 KOL 状态：{workflow_status}")
        if workflow_status == GALAXY_TAG and GALAXY_TAG not in tags:
            tags.append(GALAXY_TAG)
        self.conn.execute(
            "UPDATE profiles SET tags=?, score=?, workflow_status=?, review_status=?, note=?, favorite=? WHERE channel_id=?",
            (json.dumps(tags, ensure_ascii=False), score, workflow_status, workflow_status, note, int(favorite), channel_id),
        )
        self.conn.commit()

    def mark_viewed(self, channel_id: str) -> None:
        self.conn.execute("UPDATE profiles SET workflow_status='已查看', review_status='已查看' WHERE channel_id=? AND workflow_status='未处理'", (channel_id,))
        self.conn.commit()

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> dict:
        data = dict(row)
        for field in JSON_FIELDS:
            data[field] = json.loads(data[field] or "[]")
        data["favorite"] = bool(data["favorite"])
        data["minor_risk"] = bool(data["minor_risk"])
        return data
