"""图形验证码服务。

- 生成：随机 4 位字母数字，绘制为 SVG（无需 Pillow），返回 base64 图片 + captcha_id
- 存储：内存 dict + TTL（开发/单实例）；生产建议切换 Redis（key: captcha:{id}）
- 校验：一次性（校验后即删除），5 分钟有效，错误 5 次作废
"""

import base64
import logging
import random
import string
import time
import uuid

logger = logging.getLogger(__name__)

CAPTCHA_TTL = 300  # 5 分钟
MAX_ATTEMPTS = 5

# captcha_id -> {"code": str, "expires_at": float, "attempts": int}
_store: dict[str, dict] = {}


def _purge_expired() -> None:
    now = time.time()
    expired = [cid for cid, item in _store.items() if item["expires_at"] < now]
    for cid in expired:
        _store.pop(cid, None)


def _generate_code(length: int = 4) -> str:
    # 去掉易混淆字符 0/O/1/I
    alphabet = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")
    return "".join(random.choice(alphabet) for _ in range(length))


def _render_svg(code: str) -> str:
    """绘制简单的干扰线 + 文字 SVG。"""
    width, height = 120, 40
    chars = list(code)
    xs = [18 + i * 24 for i in range(len(chars))]

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" rx="6" fill="#f4f8ff"/>',
    ]
    # 干扰线
    rnd = random.Random(code)
    for _ in range(4):
        y1, y2 = rnd.randint(4, 36), rnd.randint(4, 36)
        parts.append(
            f'<line x1="0" y1="{y1}" x2="{width}" y2="{y2}" stroke="#b0c4ff" stroke-width="1.2"/>'
        )
    # 干扰点
    for _ in range(24):
        cx, cy = rnd.randint(0, width), rnd.randint(0, height)
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="1.4" fill="#85a5ff" opacity="0.7"/>')
    # 文字（随机微偏移与颜色）
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


def create_captcha() -> dict:
    """生成验证码，返回 captcha_id 与 base64(SVG)。"""
    _purge_expired()
    code = _generate_code()
    captcha_id = uuid.uuid4().hex
    _store[captcha_id] = {"code": code, "expires_at": time.time() + CAPTCHA_TTL, "attempts": 0}
    svg = _render_svg(code)
    image_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    logger.debug("captcha %s -> %s", captcha_id, code)
    return {"captcha_id": captcha_id, "image": f"data:image/svg+xml;base64,{image_b64}"}


def verify_captcha(captcha_id: str, code: str) -> bool:
    """校验验证码（一次性；失败计数，超限作废）。"""
    if not captcha_id or not code:
        return False
    item = _store.get(captcha_id)
    if item is None:
        return False
    if item["expires_at"] < time.time():
        _store.pop(captcha_id, None)
        return False
    if item["attempts"] >= MAX_ATTEMPTS:
        _store.pop(captcha_id, None)
        return False
    if item["code"].lower() != code.strip().lower():
        item["attempts"] += 1
        if item["attempts"] >= MAX_ATTEMPTS:
            _store.pop(captcha_id, None)
        return False
    _store.pop(captcha_id, None)  # 一次性
    return True
