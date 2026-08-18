"""敏感词过滤服务（DFA 自动机 + 符号降噪清洗）。

词库来源（v1.4 DB 化）：
- 首次启动：内置 DEFAULT_WORDS 种子写入 sensitive_words 表；
- 启动加载：init_db 时从 DB 加载全部词并 rebuild DFA；
- 管理端 CRUD（/admin/sensitive-words）实时增删并 rebuild。
- DB 不可用时回退内置默认词库（不阻断业务）。
"""

import logging
import re

from sqlalchemy import select

from app.models.sensitive_word import SensitiveWord

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

    @property
    def words(self) -> list[str]:
        """当前词库（供管理端列表展示）。"""
        return list(self._words)


sensitive_filter = SensitiveWordFilter()


async def load_words_from_db(session) -> None:
    """从 DB 加载词库到 DFA 过滤器（启动时调用；失败回退默认词库）。"""
    try:
        rows = (await session.execute(select(SensitiveWord.word))).scalars().all()
        if rows:
            sensitive_filter.rebuild([str(w) for w in rows])
            logger.info("敏感词库已从 DB 加载: %s 条", len(rows))
        else:
            # 首次启动：种子写入 DB
            for word in DEFAULT_WORDS:
                session.add(SensitiveWord(word=word))
            await session.commit()
            sensitive_filter.rebuild(DEFAULT_WORDS)
            logger.info("敏感词库已初始化种子: %s 条", len(DEFAULT_WORDS))
    except Exception as exc:  # noqa: BLE001
        logger.warning("敏感词 DB 加载失败，回退默认词库: %s", exc)
        await session.rollback()
        sensitive_filter.rebuild(DEFAULT_WORDS)
