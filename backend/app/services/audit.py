"""AI 自动审核服务（OpenAI 兼容协议：DeepSeek / 通义千问 / 智谱等）。

调用 LLM 对内容做安全审核，返回结构化结果：
- result=pass：内容安全，可直接发布
- result=review：疑似违规，转人工审核
- result=reject：确定违规，应拦截
"""

import json
import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "你是中文社区论坛的内容审核员。请对用户发布的内容进行安全审核，只输出 JSON，不要输出其他文字。\n"
    '输出格式：{"result": "pass"|"review"|"reject", "score": 0-100, "categories": [], "reason": "..."}\n'
    "- result=pass：内容安全，可直接发布；\n"
    "- result=review：疑似违规（擦边、争议），转人工审核；\n"
    "- result=reject：确定违规（涉政、色情、暴恐、违法信息、辱骂攻击、广告刷屏、诈骗等），应拦截；\n"
    "- score：违规程度 0-100，越高越违规；\n"
    "- categories：命中的违规类别数组，未命中则为空数组；\n"
    "- reason：简要判定理由（中文，50 字以内）。"
)


class AuditError(Exception):
    """AI 审核调用失败（未启用 / 网络错误 / 响应解析失败）。"""


class AIAuditService:
    """基于 LLM 的文本审核服务（同步 / 异步两种调用方式）。"""

    def __init__(self) -> None:
        self.base_url = settings.ai_base_url.rstrip("/")
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model

    @property
    def enabled(self) -> bool:
        return settings.ai_enabled and bool(self.api_key)

    # ---- 内部工具 ----

    def _build_payload(self, content: str, title: str | None) -> dict[str, Any]:
        user_msg = f"标题：{title}\n内容：{content}" if title else content
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
        }

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _parse(self, data: dict[str, Any]) -> dict[str, Any]:
        try:
            text = data["choices"][0]["message"]["content"]
            raw = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AuditError(f"AI 响应解析失败: {str(exc)}") from exc
        return self._normalize(raw)

    def _normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        result = raw.get("result")
        if result not in ("pass", "review", "reject"):
            result = "review"
        try:
            score = max(0.0, min(100.0, float(raw.get("score", 0))))
        except (TypeError, ValueError):
            score = 0.0
        categories = raw.get("categories")
        if not isinstance(categories, list):
            categories = []
        return {
            "result": result,
            "score": score,
            "categories": [str(c) for c in categories][:10],
            "reason": str(raw.get("reason", ""))[:200],
            "model": self.model,
        }

    # ---- 对外接口 ----

    async def audit_text(self, content: str, *, title: str | None = None) -> dict[str, Any]:
        """异步审核（FastAPI 请求内调用）。"""
        self._ensure_enabled(content)
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=self._build_payload(content, title),
                headers=self._headers(),
            )
            resp.raise_for_status()
            return self._parse(resp.json())

    def audit_text_sync(self, content: str, *, title: str | None = None) -> dict[str, Any]:
        """同步审核（Celery Worker 内调用）。"""
        self._ensure_enabled(content)
        with httpx.Client(timeout=settings.ai_timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=self._build_payload(content, title),
                headers=self._headers(),
            )
            resp.raise_for_status()
            return self._parse(resp.json())

    def _ensure_enabled(self, content: str) -> None:
        if not self.enabled:
            raise AuditError("AI 审核未启用：请配置 AI_ENABLED=true 与 AI_API_KEY")
        if not content or not content.strip():
            raise AuditError("待审核内容为空")
