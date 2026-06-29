"""
图形验证码模块 - 生成器
跨平台（macOS / Linux / Windows）
"""
import io
import os
import random
import string
from PIL import Image, ImageDraw, ImageFont


FONT_PATHS = [
    "/System/Library/Fonts/Helvetica.ttc",     # macOS
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",       # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
    "C:\\Windows\\Fonts\\arial.ttf",           # Windows
]


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """尝试加载系统字体，失败则回退到默认字体"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _random_color():
    return tuple(random.randint(0, 120) for _ in range(3))


def generate_captcha() -> tuple[str, bytes]:
    """返回 (答案文本, PNG图片字节)"""
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    text = "".join(random.choice(chars) for _ in range(4))

    w, h = 140, 50
    img = Image.new("RGB", (w, h), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    for _ in range(3):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line([(x1, y1), (x2, y2)], fill=_random_color(), width=1)

    for _ in range(40):
        draw.point((random.randint(0, w), random.randint(0, h)), fill=_random_color())

    font = _get_font(32)

    for i, ch in enumerate(text):
        x = 10 + i * 32 + random.randint(-3, 3)
        y = random.randint(4, 12)
        draw.text((x, y), ch, fill=_random_color(), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return text, buf.getvalue()
