from __future__ import annotations

import re
import unicodedata


DEFAULT_KEYWORDS = {
    "垂直类": [
        "一番赏", "抽一番赏", "一番賞開箱", "線上抽", "一番賞抽獎", "台湾", "台灣", "香港", "Hong Kong", "Taiwan",
        "宝可梦评级卡", "Pokemon PSA", "PSA 开箱", "PTCG 开箱", "球星卡开箱", "卡牌抽奖", "盲盒", "公仔", "手办", "模型", "GK",
        "盲盒开箱", "手办开箱", "战斗陀螺", "Beyblade", "陀螺开箱", "陀螺对战", "潮玩", "玩具", "扭蛋", "抽赏", "抽獎", "开箱",
        "游戏开箱", "动漫周边", "二次元开箱", "宅物开箱",
    ],
    "非垂直类": [
        "日常 Vlog", "惊喜开箱", "礼物开箱", "战利品开箱", "亲子开箱", "玩具试玩", "家庭 Vlog", "儿童玩具", "情侣开箱", "情侣抽奖", "挑战开箱",
    ],
}


def normalize_keyword(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold().strip())


def dedupe_keywords(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = value.strip()
        key = normalize_keyword(clean)
        if key and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def parse_bulk_keywords(text: str) -> list[str]:
    return dedupe_keywords(re.split(r"[\n,，;；]+", text))


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    haystack = normalize_keyword(text)
    return [word for word in keywords if normalize_keyword(word) in haystack]
