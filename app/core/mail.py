"""
邮件发送工具
从 system_config 读取 SMTP 配置
"""
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from app.config import settings

logger = logging.getLogger(__name__)


async def _get_smtp_config(db_factory) -> dict:
    from app.modules.system_config.crud import SystemConfigCRUD
    async with db_factory() as db:
        cfgs = await SystemConfigCRUD().get_all_grouped(db)
    return {
        "host": cfgs.get("smtp_host", ""),
        "port": int(cfgs.get("smtp_port", "465")),
        "user": cfgs.get("smtp_user", ""),
        "password": cfgs.get("smtp_password", ""),
        "from_name": cfgs.get("smtp_from_name", settings.APP_NAME),
    }


async def _send_mail(db_factory, to_email: str, subject: str, body_html: str) -> bool:
    """发送邮件，返回是否成功"""
    cfg = await _get_smtp_config(db_factory)
    if not cfg["host"] or not cfg["user"]:
        logger.warning("SMTP 未配置（host/user 为空），跳过邮件发送")
        return False

    import aiosmtplib

    msg = MIMEMultipart()
    msg["From"] = formataddr((cfg["from_name"], cfg["user"]))
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    logger.info(f"正在发送邮件: to={to_email}, host={cfg['host']}:{cfg['port']}, user={cfg['user']}")

    try:
        await aiosmtplib.send(
            msg,
            recipients=[to_email],
            hostname=cfg["host"],
            port=cfg["port"],
            username=cfg["user"],
            password=cfg["password"],
            use_tls=True,
        )
        logger.info(f"邮件发送成功: {to_email}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败 to={to_email}: {type(e).__name__}: {e}")
        return False


async def send_reset_email(db_factory, to_email: str, reset_url: str) -> bool:
    """发送密码重置邮件"""
    cfg = await _get_smtp_config(db_factory)
    return await _send_mail(
        db_factory,
        to_email,
        cfg["from_name"],
        f"<p>点击以下链接重置密码（有效期15分钟）：</p>"
        f"<p><a href='{reset_url}'>{reset_url}</a></p>"
        f"<p>如非本人操作，请忽略此邮件。</p>",
    )


async def send_verify_code(db_factory, to_email: str, code: str) -> bool:
    """发送邮箱验证码"""
    cfg = await _get_smtp_config(db_factory)
    return await _send_mail(
        db_factory,
        to_email,
        cfg["from_name"],
        f"<p>您的邮箱验证码为：</p>"
        f"<h2 style='letter-spacing:4px;color:#4f46e5'>{code}</h2>"
        f"<p>有效期5分钟，如非本人操作请忽略。</p>",
    )
