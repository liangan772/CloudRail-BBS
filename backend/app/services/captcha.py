"""图形验证码服务（安全加固 v0.1.0）。

- 生成：随机 4 位字母数字（去易混淆字符），SVG 绘制（无需 Pillow）
- 存储：Redis 优先（key: captcha:{id}，5 分钟 TTL）；Redis 不可用时降级内存
- 校验：一次性（校验后即删除）；错误 5 次作废；跨实例共享（多 worker 可用）
"""

import base64
import json
import logging
import random
import string
import time
import uuid

from app.core.cache import get_redis, memory_store

logger = logging.getLogger(__name__)

CAPTCHA_TTL = 300  # 5 分钟
MAX_ATTEMPTS = 5

# 内存降级存储（Redis 不可用时）: key "captcha:{id}" -> {"code": str, "attempts": int}
_PREFIX = "captcha:"


def _generate_code(length: int = 4) -> str:
    alphabet = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
    return "".join(random.choice(alphabet) for _ in range(length))


def _render_svg(code: str) -> str:
    width, height = 120, 40
    chars = list(code)
    xs = [18 + i * 24 for i in range(len(chars))]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" rx="6" fill="#f4f8ff"/>',
    ]
    rnd = random.Random(code)
    for _ in range(4):
        y1, y2 = rnd.randint(4, 36), rnd.randint(4, 36)
        parts.append(f'<line x1="0" y1="{y1}" x2="{width}" y2="{y2}" stroke="#b0c4ff" stroke-width="1.2"/>')
    for _ in range(24):
        cx, cy = rnd.randint(0, width), rnd.randint(0, height)
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="1.4" fill="#85a5ff" opacity="0.7"/>')
    colors = ["#2656cc", "#1d3f8f", "#2f6bff"]
    for ch, x in zip(chars, xs, strict=True):
        y = 22 + rnd.randint(-4, 4)
        color = rnd.choice(colors)
        angle = rnd.randint(-18, 18)
        parts.append(
            f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial, sans-serif" '
            f'font-size="24" font-weight="700" transform="rotate({angle} {x} {y})">{ch}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


async def _set_item(captcha_id: str, item: dict) -> None:
    redis = await get_redis()
    if redis is not None:
        try:
            await redis.setex(f"{_PREFIX}{captcha_id}", CAPTCHA_TTL, json.dumps(item))
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 写入验证码失败，降级内存: %s", exc)
    memory_store.set(f"{_PREFIX}{captcha_id}", item, ttl=CAPTCHA_TTL)


async def _get_item(captcha_id: str) -> dict | None:
    redis = await get_redis()
    if redis is not None:
        try:
            raw = await redis.get(f"{_PREFIX}{captcha_id}")
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 读取验证码失败，降级内存: %s", exc)
    item = memory_store.get(f"{_PREFIX}{captcha_id}")
    return item


async def _del_item(captcha_id: str) -> None:
    redis = await get_redis()
    if redis is not None:
        try:
            await redis.delete(f"{_PREFIX}{captcha_id}")
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis 删除验证码失败，降级内存: %s", exc)
    memory_store.delete(f"{_PREFIX}{captcha_id}")


async def create_captcha() -> dict:
    """生成验证码，返回 captcha_id 与 base64(SVG)。"""
    code = _generate_code()
    captcha_id = uuid.uuid4().hex
    await _set_item(captcha_id, {"code": code, "attempts": 0})
    svg = _render_svg(code)
    image_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    logger.debug("captcha %s -> %s", captcha_id, code)
    return {"captcha_id": captcha_id, "image": f"data:image/svg+xml;base64,{image_b64}"}


async def verify_captcha(captcha_id: str, code: str) -> bool:
    """校验验证码（一次性；失败计数，超限作废）。"""
    if not captcha_id or not code:
        return False
    item = await _get_item(captcha_id)
    if item is None:
        return False
    if item["attempts"] >= MAX_ATTEMPTS:
        await _del_item(captcha_id)
        return False
    if item["code"].lower() != code.strip().lower():
        item["attempts"] += 1
        if item["attempts"] >= MAX_ATTEMPTS:
            await _del_item(captcha_id)
        else:
            await _set_item(captcha_id, item)
        return False
    await _del_item(captcha_id)  # 一次性
    return True


# 测试/联调辅助：读取验证码明文（仅开发环境使用）
def get_code_for_test(captcha_id: str) -> str | None:
    item = memory_store.get(f"{_PREFIX}{captcha_id}")
    if item is None:
        return None
    return str(item["code"])
