from __future__ import annotations


TAIWAN_DIRECT = ("台湾", "台灣", "taiwan", "中華民國")
HONG_KONG_DIRECT = ("香港", "hong kong", "hongkong", "hk")
TAIWAN_LOCAL = ("台北", "臺北", "新北", "桃園", "台中", "臺中", "高雄", "台南", "新竹", "台灣人")
HONG_KONG_LOCAL = ("廣東話", "粤语", "粵語", "九龍", "旺角", "港幣", "hkd", "香港人")
TRADITIONAL_MARKERS = ("開箱", "頻道", "這個", "還有", "與", "獎", "體", "萬")


def _contains(text: str, terms: tuple[str, ...]) -> list[str]:
    lower = text.casefold()
    return [term for term in terms if term.casefold() in lower]


def decide_region(channel_text: str, video_text: str = "", contact_text: str = "") -> dict[str, str]:
    """Return a conservative regional judgment using only supplied public text."""
    direct_text = " ".join((channel_text, video_text, contact_text))
    tw_direct = _contains(direct_text, TAIWAN_DIRECT)
    hk_direct = _contains(direct_text, HONG_KONG_DIRECT)
    if tw_direct and hk_direct:
        return {"region": "无法确认", "confidence": "无法确认", "basis": "公开文字同时出现台湾与香港，无法判断频道主要所在地"}
    if tw_direct:
        return {"region": "台湾", "confidence": "高", "basis": "公开频道、视频或联系资料明确出现：" + "、".join(tw_direct[:2])}
    if hk_direct:
        return {"region": "香港", "confidence": "高", "basis": "公开频道、视频或联系资料明确出现：" + "、".join(hk_direct[:2])}

    local_text = " ".join((channel_text, video_text))
    tw_local = _contains(local_text, TAIWAN_LOCAL)
    hk_local = _contains(local_text, HONG_KONG_LOCAL)
    if tw_local and not hk_local:
        return {"region": "台湾", "confidence": "中", "basis": "公开内容常用台湾本地用语/地点：" + "、".join(tw_local[:2])}
    if hk_local and not tw_local:
        return {"region": "香港", "confidence": "中", "basis": "公开内容常用香港本地用语/地点：" + "、".join(hk_local[:2])}
    if _contains(local_text, TRADITIONAL_MARKERS):
        return {"region": "无法确认", "confidence": "低", "basis": "仅从繁体中文内容推测，不能确认台湾或香港"}
    return {"region": "无法确认", "confidence": "无法确认", "basis": "公开频道与近期视频资料不足以确认地区"}
