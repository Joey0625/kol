from koltool.promotion import find_promotion


def test_promotion_is_classified_with_evidence():
    result = find_promotion("测试频道", "", [{"title": "一番赏合作", "url": "https://youtube.example/v", "description": "前往 gachafashion.com 使用优惠码"}])
    assert result["status"] == "已推广过潮流勁抽"
    assert result["evidence"][0]["url"] == "https://youtube.example/v"


def test_no_hit_uses_required_wording():
    result = find_promotion("测试频道", "", [{"title": "模型开箱", "url": "", "description": "普通内容"}])
    assert result["status"] == "未发现推广过潮流勁抽"
