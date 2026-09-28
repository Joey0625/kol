import csv

from koltool.exporter import EXPORT_FIELDS, export_csv


def test_export_has_all_required_fields(tmp_path):
    profile = {
        "channel_name": "频道", "channel_url": "https://youtube.example/c", "channel_id": "id", "region": "台湾", "region_confidence": "高", "region_basis": "公开资料明确写台湾",
        "tags": ["手办"], "matched_keywords": ["手办"], "subscribers": 1, "total_videos": 2, "posts_90": 3, "avg_views": 4, "engagement_rate": 0.05,
        "contacts": ["a@example.com"], "promotion_status": "未发现推广过潮流勁抽", "checked_at": "2026-01-01", "scanned_videos": 5, "evidence": [],
        "score": 80, "score_reason": "测试", "review_status": "待联系", "note": "", "favorite": False, "minor_risk": True,
        "source": "YouTube Data API", "sourced_at": "2026-01-01", "videos": [],
    }
    path = export_csv(tmp_path / "out.csv", [profile])
    with path.open(encoding="utf-8-sig") as f:
        row = next(csv.reader(f))
    assert row == [label for label, _ in EXPORT_FIELDS]
    assert "合规提示" in row
