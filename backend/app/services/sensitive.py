"""敏感词过滤服务（DFA 自动机，文档 9.3）。

- 内置默认词表（广告/辱骂等基础词，生产可扩展为数据库维护）
- 命中策略：发帖/评论直接拦截（返回 400）
- 词典变更后调用 rebuild() 重建自动机（后续接入管理后台词库）
"""

import logging

logger = logging.getLogger(__name__)

# 默认敏感词表（示例基础词；正式词库应由管理后台维护，见文档 9.3）
DEFAULT_WORDS = [
    "代开发票",
    "办证",
    "刷单",
    "赌博",
    "博彩",
    "裸聊",
    "傻逼",
    "妈的",
    "操你妈",
    "去死吧",
    "垃圾广告",
]


class SensitiveWordFilter:
    """基于 DFA（确定性有限状态自动机）的敏感词匹配。"""

    def __init__(self) -> None:
        self._trie: dict = {}
        self._words: list[str] = []
        self.rebuild(DEFAULT_WORDS)

    def rebuild(self, words: list[str]) -> None:
        self._words = list(words)
        trie: dict = {}
        for word in words:
            node = trie
            for ch in word:
                node = node.setdefault(ch, {})
            node["#"] = True  # 词尾标记
        self._trie = trie

    def contains(self, text: str) -> bool:
        """文本是否命中任一敏感词。"""
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

    def matched_words(self, text: str) -> list[str]:
        hits = []
        n = len(text)
        for i in range(n):
            node = self._trie
            for j in range(i, n):
                ch = text[j]
                if ch not in node:
                    break
                node = node[ch]
                if node.get("#"):
                    word = text[i : j + 1]
                    if word not in hits:
                        hits.append(word)
        return hits


sensitive_filter = SensitiveWordFilter()
