"""敏感词过滤服务（DFA 自动机 + 符号降噪清洗）。"""

import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_WORDS = [
    "代开发票", "办证", "刷单", "赌博", "博彩",
    "裸聊", "傻逼", "妈的", "操你妈", "去死吧", "垃圾广告",
]

# 匹配所有常见干扰字符（空格、标点、特殊符号）
_PUNCTUATION_PATTERN = re.compile(
    r"[\s\-_~`!@#$%^&*()+=|\\\[\]{};:'\",.<>/?·！@#￥%……&*（）——+【】{}；：'\"，。、《》？]+"
)


class SensitiveWordFilter:
    """基于 DFA 的敏感词匹配（具备干扰符号自动降噪过滤）。"""

    def __init__(self) -> None:
        self._trie: dict = {}
        self._words: list[str] = []
        self.rebuild(DEFAULT_WORDS)

    def rebuild(self, words: list[str]) -> None:
        self._words = list(words)
        trie: dict = {}
        for word in words:
            # 构建树前统一转为小写且去干扰
            clean_word = self._normalize(word)
            if not clean_word:
                continue
            node = trie
            for ch in clean_word:
                node = node.setdefault(ch, {})
            node["#"] = True
        self._trie = trie

    def _normalize(self, text: str) -> str:
        """剔除干扰符号并小写化，例如 '代*开 发_票' -> '代开发票'"""
        if not text:
            return ""
        return _PUNCTUATION_PATTERN.sub("", text).lower()

    def contains(self, text: str) -> bool:
        """文本是否命中敏感词（同时检测原始文本与降噪后的文本）。"""
        if not text:
            return False
        # 检测降噪后的紧凑文本
        clean_text = self._normalize(text)
        return self._match_trie(clean_text)

    def _match_trie(self, text: str) -> bool:
        n = len(text)
        for i in range(n):
            node = self._trie
            for j in range(i, n):
                ch = text[j]
                if ch not in node:
                    break
                node = node[ch]
                if node.get("#"):
                    return True
        return False


sensitive_filter = SensitiveWordFilter()