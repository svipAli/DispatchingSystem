"""
应用配置模块
-----------
从 .env 文件和环境变量中读取所有配置项。
使用 pydantic-settings 实现类型安全，所有配置项有默认值。
改了需要重启服务的配置放 .env，改了不需要重启的放 system_config 表。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置，所有值均可通过 .env 文件或环境变量覆盖"""

    # ========== 数据库 ==========
    # PostgreSQL 异步连接字符串（使用 asyncpg 驱动）
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/dispatching"

    # ========== Redis ==========
    # 用于：用户状态缓存、节点心跳、Celery Broker
    REDIS_URL: str = "redis://localhost:6379/0"

    # ========== JWT 认证 ==========
    # 签发和校验 Token 的密钥，生产环境务必更换为随机字符串
    JWT_SECRET_KEY: str = "change-me"
    # Token 过期时间（分钟），默认 30 分钟
    JWT_EXPIRE_MINUTES: int = 10080

    # ========== 应用信息 ==========
    APP_NAME: str = "DispatchingSystem"
    APP_VERSION: str = "1.0.0"
    # 调试模式：开启后 SQL 会输出到控制台
    DEBUG: bool = False

    # ========== Celery 异步任务 ==========
    # Broker：任务队列存在 Redis 1 号库
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    # Backend：任务结果存在 Redis 2 号库
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ========== 文件上传 ==========
    # 未配置腾讯云 COS 时的默认本地上传目录
    UPLOAD_DIR: str = "app/static/upload"

    # ========== 时区 ==========
    TZ_OFFSET: int = 8  # 时区偏移（小时），8=北京时间

    # 告诉 pydantic-settings 从项目根目录的 .env 文件读取配置
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# 全局单例，其他模块直接 from app.config import settings 即可使用
settings = Settings()
