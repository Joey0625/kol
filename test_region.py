from koltool.region import decide_region


def test_direct_region_has_high_confidence():
    judgment = decide_region("台湾台北的公仔频道", "一番賞開箱")
    assert judgment["region"] == "台湾"
    assert judgment["confidence"] == "高"


def test_traditional_language_alone_is_not_formal_region_match():
    judgment = decide_region("這個頻道分享模型開箱")
    assert judgment["region"] == "无法确认"
    assert judgment["confidence"] == "低"
