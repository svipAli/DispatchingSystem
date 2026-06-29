"""
图形验证码 API
GET /api/v1/captcha → 返回 base64 图片 + captcha_id
"""
import base64
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from app.modules.captcha.service import generate_captcha

router = APIRouter(prefix="/captcha", tags=["验证码"])


@router.get("")
async def get_captcha(request: Request):
    text, img_bytes = generate_captcha()
    captcha_id = uuid.uuid4().hex[:12]

    redis: Redis = request.app.state.redis
    await redis.set(f"captcha:{captcha_id}", text, ex=300)

    b64 = base64.b64encode(img_bytes).decode()
    return JSONResponse({
        "code": 0,
        "data": {
            "captcha_id": captcha_id,
            "image": f"data:image/png;base64,{b64}",
        }
    })
