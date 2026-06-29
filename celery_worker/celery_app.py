"""
Celery 异步任务队列配置
-----------------------
Celery 负责处理所有异步任务：
- MCP 任务调度：将用户提交的任务分发到对应的 MCP 节点
- 定时任务：检查用户月租到期、清理过期数据等
- 耗时操作：发送邮件、生成报表等

启动方式：
    celery -A celery_worker.celery_app worker -l info -c 4    # Worker 进程
    celery -A celery_worker.celery_app beat -l info            # 定时任务调度器

关键配置说明：
- task_acks_late=True：任务执行完成后才确认，防止 Worker 崩溃导致任务丢失
- worker_prefetch_multiplier=1：每个 Worker 一次只取一个任务，适合长任务场景
- timezone="Asia/Shanghai"：北京时间，定时任务按这个时区执行
"""
from celery import Celery
from app.config import settings

# 创建 Celery 实例
celery_app = Celery(
    "dispatching",                          # 应用名称
    broker=settings.CELERY_BROKER_URL,       # 任务队列：Redis 1 号库
    backend=settings.CELERY_RESULT_BACKEND,  # 结果存储：Redis 2 号库
)

# Celery 全局配置
celery_app.conf.update(
    task_serializer="json",             # 任务参数用 JSON 序列化
    accept_content=["json"],            # 只接受 JSON 格式的任务
    result_serializer="json",           # 任务结果用 JSON 序列化
    timezone="Asia/Shanghai",           # 时区：北京时间
    enable_utc=True,                    # 内部使用 UTC 时间
    task_track_started=True,               # 跟踪任务开始状态
    task_acks_late=True,                   # 任务执行完才确认（防止丢任务）
    worker_prefetch_multiplier=1,          # 每次只预取一个任务
)

# 自动发现 celery_worker/tasks/ 目录下的所有任务模块
celery_app.autodiscover_tasks(["celery_worker.tasks"])

# 加载定时任务调度配置
try:
    from celery_worker.tasks.periodic import CELERY_BEAT_SCHEDULE
    celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
except ImportError:
    pass
