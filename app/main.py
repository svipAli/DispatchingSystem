"""
FastAPI 应用入口
---------------
- 生命周期管理：启动时连接 Redis + 创建数据库引擎，关闭时释放
- 动态路由注册：自动扫描 modules/ 下所有模块的 router.py 并注册到 /api/v1/
- 全局异常处理：捕获所有未处理异常，返回统一格式的 JSON
- 静态文件挂载：/static 对应 app/static/ 目录
"""
import importlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期上下文管理器
    在服务启动时执行 yield 之前的代码，关闭时执行 yield 之后的代码。
    如果 Redis 或数据库连接失败，服务直接无法启动（fail-fast）。
    """
    # === 启动时 ===
    # 连接 Redis：用于用户状态缓存、节点心跳、Celery Broker
    app.state.redis = Redis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )

    # 创建异步数据库引擎和会话工厂
    engine = create_async_engine(
        settings.DATABASE_URL, echo=settings.DEBUG,
        connect_args={"server_settings": {"timezone": "Asia/Shanghai"}}
    )
    app.state.db_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # 启动时把所有节点标记为离线（因为 WS 连接已全部断开），等节点重连后恢复
    async with app.state.db_session_factory() as db:
        from app.modules.mcp_node.crud import McpNodeCRUD
        from app.modules.mcp_node.models import McpNode
        from sqlalchemy import update
        await db.execute(update(McpNode).values(node_status="offline", current_load=0))
        await db.commit()

    yield

    # === 关闭时 ===
    await app.state.redis.close()
    await engine.dispose()


# 初始化 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 挂载静态文件目录，访问路径 /static/xxx → app/static/xxx
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/favicon.ico")
async def favicon():
    import os
    path = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    return FileResponse(path)


# ========== 全局异常处理 ==========
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    兜底异常处理器
    所有未被路由层或中间件捕获的异常最终到达这里。
    返回统一格式的 500 错误 JSON，避免暴露内部堆栈信息。
    """
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": str(exc), "data": None},
    )


# ========== 动态路由注册 ==========
MODULES_DIR = Path(__file__).parent / "modules"


def auto_register_modules():
    """
    自动发现并注册所有模块路由
    扫描 app/modules/ 下的每个子目录，如果该目录包含 router.py 且其中有 router 对象，
    则自动 include 到 /api/v1/ 前缀下。

    新增模块时只需要：
        1. 创建 app/modules/新模块/router.py
        2. 在里面定义 router = APIRouter(...)
    无需修改本文件或任何其他代码。
    """
    for module_path in sorted(MODULES_DIR.iterdir()):
        # 跳过非目录和以下划线开头的目录
        if not module_path.is_dir() or module_path.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"app.modules.{module_path.name}.router")
            if hasattr(mod, "router"):
                app.include_router(mod.router, prefix="/api/v1")
            # 支持模块导出额外的路由列表（如 mcp_node 同时注册 /mcp-services）
            if hasattr(mod, "extra_routers"):
                for r in mod.extra_routers:
                    app.include_router(r, prefix="/api/v1")
        except ModuleNotFoundError:
            # 该模块没有 router.py，正常，跳过即可
            pass


# 执行注册（在模块加载时运行一次）
auto_register_modules()

# ========== 前端页面路由 ==========
from app.pages.auth import router as auth_page_router
from app.pages.user import router as user_page_router

app.include_router(auth_page_router, prefix="")
app.include_router(user_page_router, prefix="")

# WebSocket 路由（独立模块）
from app.modules.ws.router import router as ws_router
app.include_router(ws_router)

from app.modules.mcp_gateway.router import mcp_router
app.include_router(mcp_router)


@app.get("/api/v1/stats")
async def get_stats():
    """首页统计接口"""
    from sqlalchemy import select, func
    from datetime import datetime
    from app.modules.user.models import User
    from app.modules.task.models import Task
    from app.modules.mcp_node.models import McpNode
    from app.modules.billing.models import BillingRecord

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    async with app.state.db_session_factory() as db:
        total_users = (await db.execute(select(func.count(User.id)).where(User.status==True))).scalar() or 0
        online_nodes = (await db.execute(select(func.count(McpNode.id)).where(McpNode.node_status=="online", McpNode.status==True))).scalar() or 0
        today_tasks = (await db.execute(select(func.count(Task.id)).where(Task.created_at>=today))).scalar() or 0
        today_completed = (await db.execute(select(func.count(Task.id)).where(Task.created_at>=today, Task.status=="completed"))).scalar() or 0
        today_revenue = (await db.execute(select(func.coalesce(func.sum(BillingRecord.amount),0)).where(BillingRecord.created_at>=today, BillingRecord.type=="deduct"))).scalar() or 0

    return {"code":0, "data":{
        "total_users": total_users, "online_nodes": online_nodes,
        "today_tasks": today_tasks, "today_completed": today_completed,
        "today_revenue": round(float(today_revenue), 2),
    }}

@app.get("/api/v1/monitor/platform")
async def get_platform_monitor():
    """平台自身运维指标，同时存储到 Redis 供历史查询"""
    global _PLATFORM_NET_LAST
    try:
        import psutil, os, time as _time, json as _json
        from datetime import datetime
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()
        proc = psutil.Process(os.getpid())
        now = _time.time()
        rx_speed = tx_speed = 0
        global _PLATFORM_NET_LAST
        now = _time.time()
        try:
            dt = now - _PLATFORM_NET_LAST["time"]
            if dt > 0:
                rx_speed = round((net.bytes_recv - _PLATFORM_NET_LAST["rx"]) / dt, 1)
                tx_speed = round((net.bytes_sent - _PLATFORM_NET_LAST["tx"]) / dt, 1)
        except (NameError, KeyError):
            pass
        _PLATFORM_NET_LAST = {"time": now, "rx": net.bytes_recv, "tx": net.bytes_sent}
        data = {
            "cpu": cpu,
            "memory_total": mem.total, "memory_used": mem.used, "memory_percent": mem.percent,
            "disk_total": disk.total, "disk_used": disk.used, "disk_percent": disk.percent,
            "process_memory": proc.memory_info().rss,
            "uptime": int(now - proc.create_time()),
            "network_rx_speed": rx_speed, "network_tx_speed": tx_speed,
            "load_avg": round(psutil.getloadavg()[0], 2),
            "pid": os.getpid(), "_time": datetime.now().isoformat(),
        }
        # 存储到 Redis
        try:
            redis = app.state.redis
            await redis.lpush("platform_metrics", _json.dumps(data))
            await redis.ltrim("platform_metrics", 0, 59)
            raw = await redis.lrange("platform_metrics", 0, 59)
            history = [_json.loads(r) for r in raw]
        except Exception:
            history = [data]
        return {"code": 0, "data": {"latest": data, "history": history}}
    except Exception as e:
        return {"code": -1, "message": str(e)}
@app.get("/api/v1/monitor")
async def get_monitor():
    """运维监控 API：返回所有节点的实时指标"""
    import json as _json
    from app.modules.mcp_node.models import McpNode
    from sqlalchemy import select

    async with app.state.db_session_factory() as db:
        result = await db.execute(select(McpNode).where(McpNode.status == True).order_by(McpNode.id))
        db_nodes = {n.id: {"name": n.name, "host": n.host, "status": n.node_status, "max_concurrent": n.max_concurrent} for n in result.scalars()}

    redis = app.state.redis
    nodes = []
    for nid, info in db_nodes.items():
        metrics_list = []
        try:
            raw = await redis.lrange(f"node_metrics:{nid}", 0, 59)
            for r in raw:
                try: metrics_list.append(_json.loads(r))
                except: pass
        except Exception:
            pass
        latest = metrics_list[0] if metrics_list else {}
        nodes.append({
            "id": nid, "name": info["name"], "host": info["host"],
            "status": info["status"], "max_concurrent": info["max_concurrent"],
            "latest": latest, "history": metrics_list,
        })
    return {"code": 0, "data": {"nodes": nodes}}
    """首页统计接口"""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    from app.modules.user.models import User
    from app.modules.task.models import Task
    from app.modules.mcp_node.models import McpNode
    from app.modules.billing.models import BillingRecord

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    async with app.state.db_session_factory() as db:
        # 用户总数
        total_users = (await db.execute(select(func.count(User.id)).where(User.status == True))).scalar() or 0

        # 在线节点数
        online_nodes = (await db.execute(
            select(func.count(McpNode.id)).where(McpNode.node_status == "online", McpNode.status == True)
        )).scalar() or 0

        # 今日任务数
        today_tasks = (await db.execute(
            select(func.count(Task.id)).where(Task.created_at >= today)
        )).scalar() or 0

        # 今日完成数
        today_completed = (await db.execute(
            select(func.count(Task.id)).where(Task.created_at >= today, Task.status == "completed")
        )).scalar() or 0

        # 今日收入（deduct 流水总和）
        today_revenue = (await db.execute(
            select(func.coalesce(func.sum(BillingRecord.amount), 0))
            .where(BillingRecord.created_at >= today, BillingRecord.type == "deduct")
        )).scalar() or 0

    return {
        "code": 0,
        "data": {
            "total_users": total_users,
            "online_nodes": online_nodes,
            "today_tasks": today_tasks,
            "today_completed": today_completed,
            "today_revenue": round(float(today_revenue), 2),
        },
    }


@app.get("/api/v1/debug/smtp-test")
async def debug_smtp_test(email: str = ""):
    """诊断接口：测试 SMTP 邮件发送。?email=xxx@xxx.com"""
    from app.core.mail import _send_mail, _get_smtp_config
    from app.modules.system_config.crud import SystemConfigCRUD

    cfg = await _get_smtp_config(app.state.db_session_factory)

    # 同时读取原始数据库记录，检查 status
    async with app.state.db_session_factory() as db:
        smtp_keys = ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_from_name"]
        records = {}
        for k in smtp_keys:
            item = await SystemConfigCRUD().get_by_key(db, k)
            records[k] = {"value": item.value if item else None, "status": item.status if item else None}

    result = {
        "merged_config": {k: v for k, v in cfg.items() if k != "password"},
        "db_records": records,
    }

    if not email:
        result["message"] = "未提供 email 参数，跳过发送测试"
        return result

    if not cfg["host"] or not cfg["user"]:
        result["message"] = "SMTP 未配置"
        return result

    ok = await _send_mail(
        app.state.db_session_factory,
        email,
        f"{cfg['from_name']} - SMTP 测试",
        "<p>如果你收到此邮件，说明 SMTP 配置正确。</p>",
    )
    result["send_ok"] = ok
    result["message"] = "发送成功" if ok else "发送失败，请查看服务端日志"
    return result


# ========== 健康检查 ==========
@app.get("/api/v1/health")
async def health_check():
    """运维健康检查端点，返回当前服务版本号"""
    return {"code": 0, "message": "ok", "data": {"version": settings.APP_VERSION}}
