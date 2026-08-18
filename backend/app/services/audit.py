"""AI 自动审核服务（OpenAI 兼容协议：DeepSeek / 通义千问 / 智谱等）。

支持三类审核（两级审核流程的 AI 初审环节）：
- audit_text：文本审核（帖子正文 / 评论等）
- audit_image：图片审核（视觉模型，media_url 可为 http(s) 或 data URI）
- audit_post：帖子组合审核（标题 + 正文 + 正文中提取的图片，汇总取最严结论）

运行模式（settings.ai_mode）：
- llm：真实调用 OpenAI 兼容 /chat/completions（需配置 AI_API_KEY）
- mock：确定性模拟（不发起任何网络请求），用于本地演示与自动化测试：
  * 文本包含「违禁词测试」→ reject；包含「擦边测试」→ review；其余 → pass
  * 图片 URL 含「bad」→ reject；含「sus」→ review；其余 → pass

返回结构化结果：
- result=pass：内容安全，可直接发布
- result=review：疑似违规，转人工审核
- result=reject：确定违规，应拦截

注意：AI 初审结论最终都必须经过管理后台人工复审（见 api/v1/admin/audits 接口）。
"""

import json
import logging
import re
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

IMAGE_SYSTEM_PROMPT = (
    "你是中文社区论坛的图片审核员。请对用户发布的图片进行安全审核，只输出 JSON，不要输出其他文字。\n"
    '输出格式：{"result": "pass"|"review"|"reject", "score": 0-100, "categories": [], "reason": "..."}\n'
    "- result=pass：图片安全，可直接展示；\n"
    "- result=review：疑似违规（低俗擦边、争议、需人工判断），转人工审核；\n"
    "- result=reject：确定违规（色情裸露、血腥暴力、涉政敏感、违法信息、诈骗引流等），应拦截；\n"
    "- score：违规程度 0-100，越高越违规；\n"
    "- categories：命中的违规类别数组，未命中则为空数组；\n"
    "- reason：简要判定理由（中文，50 字以内）。"
)

# 正文图片提取：Markdown 图片 ![alt](url) 与 HTML <img src="url">
_IMAGE_URL_RE = re.compile(
    r"!\[[^\]]*\]\(\s*(https?://[^)\s]+)\s*\)|<img[^>]+src=[\"'](https?://[^\"']+)[\"']",
    re.IGNORECASE,
)

# 宽容 JSON 解析：视觉模型可能不严格遵守 response_format
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

# mock 模式关键词（确定性判定，仅供本地演示与自动化测试）
_MOCK_REJECT_WORDS = ("违禁词测试",)
_MOCK_REVIEW_WORDS = ("擦边测试",)


class AuditError(Exception):
    """AI 审核调用失败（未启用 / 网络错误 / 响应解析失败）。"""


def extract_image_urls(content: str, max_images: int = 4) -> list[str]:
    """从帖子正文中提取图片 URL（Markdown / HTML 格式），去重并限量。"""
    urls: list[str] = []
    for match in _IMAGE_URL_RE.finditer(content or ""):
        url = match.group(1) or match.group(2)
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= max_images:
            break
    return urls


class AIAuditService:
    """基于 LLM 的内容审核服务（文本 / 图片 / 帖子，同步 / 异步两种调用方式）。

    ai_mode=mock 时不发起网络请求，按确定性规则返回结论，方便本地演示与自动化测试。
    """

    def __init__(self) -> None:
        self.base_url = settings.ai_base_url.rstrip("/")
        self.api_key = settings.ai_api_key
        self.model = settings.ai_model
        self.vision_model = settings.ai_vision_model or self.model

    @property
    def enabled(self) -> bool:
        """mock 模式无需 API Key 即可启用；llm 模式需要 Key。"""
        if not settings.ai_enabled:
            return False
        return settings.ai_mode == "mock" or bool(self.api_key)

    @property
    def is_mock(self) -> bool:
        return settings.ai_mode == "mock"

    # ---- mock 模式（确定性判定） ----

    def _mock_result(self, content: str) -> dict[str, Any]:
        if any(w in content for w in _MOCK_REJECT_WORDS):
            return {
                "result": "reject",
                "score": 95.0,
                "categories": ["违禁内容"],
                "reason": "命中违规词（mock 判定）",
                "model": "mock-audit",
            }
        if any(w in content for w in _MOCK_REVIEW_WORDS):
            return {
                "result": "review",
                "score": 60.0,
                "categories": ["疑似擦边"],
                "reason": "疑似擦边内容，转人工（mock 判定）",
                "model": "mock-audit",
            }
        return {
            "result": "pass",
            "score": 5.0,
            "categories": [],
            "reason": "未发现明显违规（mock 判定）",
            "model": "mock-audit",
        }

    def _mock_image_result(self, media_url: str) -> dict[str, Any]:
        if "bad" in media_url.lower():
            return {
                "result": "reject",
                "score": 92.0,
                "categories": ["色情低俗"],
                "reason": "图片疑似违规（mock 判定）",
                "model": "mock-vision",
            }
        if "sus" in media_url.lower():
            return {
                "result": "review",
                "score": 55.0,
                "categories": ["疑似擦边"],
                "reason": "图片疑似擦边，转人工（mock 判定）",
                "model": "mock-vision",
            }
        return {
            "result": "pass",
            "score": 3.0,
            "categories": [],
            "reason": "图片无明显违规（mock 判定）",
            "model": "mock-vision",
        }

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

    def _build_image_payload(self, media_url: str, context: str = "") -> dict[str, Any]:
        """视觉审核 payload：content 为多模态消息（text + image_url）。

        说明：不强制 response_format=json_object（部分视觉模型不支持），
        解析时采用宽容模式（_parse_lenient）。
        """
        text = "请审核这张图片是否违规。" + (f"补充上下文：{context}" if context else "")
        return {
            "model": self.vision_model,
            "messages": [
                {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text},
                        {"type": "image_url", "image_url": {"url": media_url}},
                    ],
                },
            ],
            "temperature": 0,
            "max_tokens": 300,
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

    def _parse_lenient(self, data: dict[str, Any]) -> dict[str, Any]:
        """宽容解析（视觉模型）：JSON 解析失败时尝试提取文本中的 JSON 块。"""
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AuditError(f"AI 响应解析失败: {str(exc)}") from exc
        raw: dict[str, Any] | None = None
        try:
            raw = json.loads(text)
        except json.JSONDecodeError:
            block = _JSON_BLOCK_RE.search(text or "")
            if block:
                try:
                    raw = json.loads(block.group(0))
                except json.JSONDecodeError:
                    raw = None
        if raw is None or not isinstance(raw, dict):
            raise AuditError("AI 响应不是有效 JSON")
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

    @staticmethod
    def _merge(results: list[dict[str, Any]]) -> dict[str, Any]:
        """汇总多项审核结果：任一 reject 则 reject，否则任一 review 则 review。"""
        if not results:
            return {"result": "pass", "score": 0.0, "categories": [], "reason": "", "model": ""}
        rank = {"pass": 0, "review": 1, "reject": 2}
        worst = max(results, key=lambda r: rank.get(r["result"], 1))
        categories: list[str] = []
        for r in results:
            for c in r.get("categories", []):
                if c not in categories:
                    categories.append(c)
        return {
            "result": worst["result"],
            "score": max(float(r.get("score", 0)) for r in results),
            "categories": categories[:10],
            "reason": worst.get("reason", ""),
            "model": worst.get("model", ""),
        }

    # ---- 文本审核 ----

    async def audit_text(self, content: str, *, title: str | None = None) -> dict[str, Any]:
        """异步审核文本（FastAPI 请求内调用）。"""
        self._ensure_enabled(content)
        if self.is_mock:
            return self._mock_result(f"标题：{title}\n内容：{content}" if title else content)
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=self._build_payload(content, title),
                headers=self._headers(),
            )
            resp.raise_for_status()
            return self._parse(resp.json())

    def audit_text_sync(self, content: str, *, title: str | None = None) -> dict[str, Any]:
        """同步审核文本（Celery Worker 内调用）。"""
        self._ensure_enabled(content)
        if self.is_mock:
            return self._mock_result(f"标题：{title}\n内容：{content}" if title else content)
        with httpx.Client(timeout=settings.ai_timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=self._build_payload(content, title),
                headers=self._headers(),
            )
            resp.raise_for_status()
            return self._parse(resp.json())

    # ---- 图片审核 ----

    async def audit_image(self, media_url: str, *, context: str = "") -> dict[str, Any]:
        """异步审核单张图片（视觉模型）。"""
        self._ensure_enabled(media_url)
        if self.is_mock:
            return self._mock_image_result(media_url)
        async with httpx.AsyncClient(timeout=settings.ai_timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=self._build_image_payload(media_url, context),
                headers=self._headers(),
            )
            resp.raise_for_status()
            result = self._parse_lenient(resp.json())
        result["media_url"] = media_url
        return result

    def audit_image_sync(self, media_url: str, *, context: str = "") -> dict[str, Any]:
        """同步审核单张图片（Celery Worker 内调用）。"""
        self._ensure_enabled(media_url)
        if self.is_mock:
            return self._mock_image_result(media_url)
        with httpx.Client(timeout=settings.ai_timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                json=self._build_image_payload(media_url, context),
                headers=self._headers(),
            )
            resp.raise_for_status()
            result = self._parse_lenient(resp.json())
        result["media_url"] = media_url
        return result

    # ---- 帖子组合审核（文本 + 图片） ----

    async def audit_post(
        self,
        content: str,
        *,
        title: str | None = None,
        image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """异步审核帖子：正文文本 + 自动提取（或显式传入）的图片，汇总取最严结论。"""
        self._ensure_enabled(content)
        image_urls = image_urls or extract_image_urls(content)
        text_result = await self.audit_text(content, title=title)
        image_results: list[dict[str, Any]] = []
        for url in image_urls:
            try:
                image_results.append(await self.audit_image(url, context=title or ""))
            except (AuditError, httpx.HTTPError) as exc:
                # 单张图片失败不阻断整体：记录并跳过（仍可人工复审）
                logger.warning("图片审核跳过 %s: %s", url, exc)
        merged = self._merge([text_result, *(r for r in image_results)])
        merged["image_results"] = image_results
        return merged

    def audit_post_sync(
        self,
        content: str,
        *,
        title: str | None = None,
        image_urls: list[str] | None = None,
    ) -> dict[str, Any]:
        """同步审核帖子（Celery Worker 内调用）。"""
        self._ensure_enabled(content)
        image_urls = image_urls or extract_image_urls(content)
        text_result = self.audit_text_sync(content, title=title)
        image_results: list[dict[str, Any]] = []
        for url in image_urls:
            try:
                image_results.append(self.audit_image_sync(url, context=title or ""))
            except (AuditError, httpx.HTTPError) as exc:
                logger.warning("图片审核跳过 %s: %s", url, exc)
        merged = self._merge([text_result, *(r for r in image_results)])
        merged["image_results"] = image_results
        return merged

    def _ensure_enabled(self, content: str) -> None:
        if not self.enabled:
            raise AuditError("AI 审核未启用：请配置 AI_ENABLED=true 与 AI_API_KEY（或 AI_MODE=mock）")
        if not content or not content.strip():
            raise AuditError("待审核内容为空")
