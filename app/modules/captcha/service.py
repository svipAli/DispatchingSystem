"""
图形验证码模块 - 生成器
"""
import io
import random
import string
from PIL import Image, ImageDraw, ImageFont


def _random_color():
    return tuple(random.randint(0, 120) for _ in range(3))


def generate_captcha() -> tuple[str, bytes]:
    """返回 (答案文本, PNG图片字节)"""
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    text = "".join(random.choice(chars) for _ in range(4))

    w, h = 120, 44
    img = Image.new("RGB", (w, h), color=(245, 245, 245))
    draw = ImageDraw.Draw(img)

    for _ in range(3):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = random.randint(0, w), random.randint(0, h)
        draw.line([(x1, y1), (x2, y2)], fill=_random_color(), width=1)

    for _ in range(30):
        draw.point((random.randint(0, w), random.randint(0, h)), fill=_random_color())

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except Exception:
        font = ImageFont.load_default()

    for i, ch in enumerate(text):
        x = 10 + i * 26 + random.randint(-3, 3)
        y = random.randint(4, 10)
        draw.text((x, y), ch, fill=_random_color(), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return text, buf.getvalue()
