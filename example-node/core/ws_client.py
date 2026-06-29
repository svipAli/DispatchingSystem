"""
WebSocket 连接 + 心跳 + 任务收发
"""
import json
import asyncio
import os

import yaml
import websockets

from core.registry import build_hello_message, sync_config_from_platform
from utils.logger import get_logger

# ---- 系统指标采集 ----
import time as _time
try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

_NET_LAST = {"time": 0, "rx": 0, "tx": 0}

def get_metrics() -> dict:
    if not _PSUTIL:
        return {}
    global _NET_LAST
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    now = _time.time()
    m = {
        "cpu": cpu,
        "memory_total": mem.total, "memory_used": mem.used, "memory_percent": mem.percent,
        "disk_total": disk.total, "disk_used": disk.used, "disk_percent": disk.percent,
        "network_rx": net.bytes_recv, "network_tx": net.bytes_sent,
        "uptime": int(now - psutil.boot_time()),
    }
    try: m["load_avg"] = round(psutil.getloadavg()[0], 2)
    except: pass
    if _NET_LAST["time"] > 0:
        dt = now - _NET_LAST["time"]
        if dt > 0:
            m["network_rx_speed"] = round((net.bytes_recv - _NET_LAST["rx"]) / dt, 1)
            m["network_tx_speed"] = round((net.bytes_sent - _NET_LAST["tx"]) / dt, 1)
    _NET_LAST = {"time": now, "rx": net.bytes_recv, "tx": net.bytes_sent}
    return m

# ---- 配置加载 ----
_CFG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "node_config.yaml")


def _read_config():
    with open(_CFG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


_cfg = _read_config()
_node = _cfg["node"]
NODE_ID = _node["id"]
WS_URL = _node["platform_ws_url"]
INTERVAL = _node.get("heartbeat_interval", 5)
MAX_CONCURRENT = _node.get("max_concurrent", 5)

log = get_logger(f"node-{NODE_ID}")
_active_tasks: set[asyncio.Task] = set()


# ---- 热重载 ----

def _reload_config():
    """config_sync 后重新加载运行时配置变量"""
    global _cfg, _node, WS_URL, INTERVAL, MAX_CONCURRENT
    _cfg = _read_config()
    _node = _cfg["node"]
    WS_URL = _node["platform_ws_url"]
    INTERVAL = _node.get("heartbeat_interval", 5)
    MAX_CONCURRENT = _node.get("max_concurrent", 5)
    log.info("配置已热重载")


def _get_timeout(service_type: str) -> int:
    for s in _cfg.get("services", []):
        if s.get("type") == service_type:
            return s.get("timeout", 60)
    return 60


# ---- 服务路由（各节点自行扩展） ----

# TODO: 在此定义 SERVICE_MAP，将 service_type 映射到实际处理函数
# 示例：
# from services.xxx import handle as xxx_handle
# SERVICE_MAP = {"xxx": xxx_handle}

# TODO: 在此定义 _REQUIRED_PARAMS，声明各服务的必填参数
# _REQUIRED_PARAMS = {
#     "_common": ["param1", "param2"],       # 所有服务通用的必填参数
#     "service-type": ["param3"],            # 特定服务的必填参数
# }

_REQUIRED_PARAMS: dict = {"_common": []}


def _check_required(service_type: str, kwargs: dict) -> list[str]:
    """检查必填参数，返回缺失的字段名列表"""
    missing = []
    for field in _REQUIRED_PARAMS.get("_common", []):
        if not kwargs.get(field):
            missing.append(field)
    for field in _REQUIRED_PARAMS.get(service_type, []):
        if not kwargs.get(field):
            missing.append(field)
    return missing


# ---- 任务执行 ----

async def handle_one_task(ws, task_id, service_type, request_params, load_counter):
    """
    单个任务完整生命周期：路由 → 参数校验 → 执行 → 回传
    所有异常内部消化，永不泄漏到主循环。
    """
    result: dict
    try:
        # TODO: 替换为实际的服务路由
        # handler = SERVICE_MAP.get(service_type)
        # if handler is None:
        #     result = {"code": -1, "message": f"未知服务类型: {service_type}", "data": None}
        # else:
        #     input_data = request_params.get("input", {})
        #     missing = _check_required(service_type, input_data)
        #     if missing:
        #         result = {"code": -2, "message": f"缺少必填参数: {', '.join(missing)}", "data": None}
        #     else:
        #         timeout = _get_timeout(service_type)
        #         data = await asyncio.wait_for(handler(request_params), timeout=timeout)
        #         result = {"code": 0, "message": "success", "data": data}

        # 占位实现
        await asyncio.sleep(0.1)
        result = {"code": 0, "message": "success", "data": {}}

    except asyncio.TimeoutError:
        timeout = _get_timeout(service_type)
        result = {"code": -4, "message": f"任务执行超时（{timeout}秒）", "data": None}
    except asyncio.CancelledError:
        result = {"code": -5, "message": "任务被取消", "data": None}
    except BaseException as e:
        log.error(f"任务异常 task_id={task_id}: {e}", exc_info=True)
        result = {"code": -3, "message": f"{type(e).__name__}: {e}", "data": None}

    try:
        await ws.send(json.dumps({"type": "result", "task_id": task_id, "result": result}))
    except BaseException as e:
        log.error(f"回传失败 task_id={task_id}: {e}")

    load_counter["value"] = max(0, load_counter["value"] - 1)
    log.info(f"任务完成 task_id={task_id} load={load_counter['value']}")


def fire_task(ws, task_id, service_type, request_params, load_counter):
    """发射后台任务，不阻塞主循环"""
    coro = handle_one_task(ws, task_id, service_type, request_params, load_counter)
    task = asyncio.create_task(coro)
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)


# ---- 主入口 ----

async def run_node():
    log.info(f"节点 {NODE_ID} 启动 → {WS_URL}")
    log.info(f"max_concurrent={MAX_CONCURRENT}")

    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                log.info("已连接平台")

                await ws.send(json.dumps(build_hello_message()))
                log.info("配置已上报")

                load_counter = {"value": 0}
                hb_count = 0

                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=INTERVAL)
                        data = json.loads(msg)

                        if data.get("type") == "task":
                            task_id = data["task_id"]
                            service_type = data.get("service_type", "")
                            request_params = data.get("request_params", {})

                            if load_counter["value"] >= MAX_CONCURRENT:
                                log.warning(f"并发已满 task_id={task_id}")
                                await ws.send(json.dumps({
                                    "type": "result", "task_id": task_id,
                                    "result": {"code": -6,
                                               "message": f"节点繁忙 {load_counter['value']}/{MAX_CONCURRENT}",
                                               "data": None},
                                }))
                            else:
                                load_counter["value"] += 1
                                log.info(f"启动任务 task_id={task_id} type={service_type} "
                                         f"load={load_counter['value']}")
                                fire_task(ws, task_id, service_type, request_params, load_counter)

                        elif data.get("type") == "config_sync":
                            platform_config = data.get("config", {})
                            platform_services = data.get("services", [])
                            if platform_config or platform_services:
                                if sync_config_from_platform(platform_config, platform_services):
                                    _reload_config()
                                    log.info("本地 yaml 已更新，重新上报 hello")
                                    await ws.send(json.dumps(build_hello_message()))
                            else:
                                # 触发信号：请求平台返回完整配置
                                log.info("平台触发 config_sync，请求完整配置")
                                await ws.send(json.dumps({"type": "config_sync"}))

                    except asyncio.TimeoutError:
                        pass

                    # 心跳
                    hb_count += 1
                    if hb_count % 5 == 0:
                        hello = build_hello_message()
                        hello["load"] = load_counter["value"]
                        hello["metrics"] = get_metrics()
                        await ws.send(json.dumps(hello))
                    else:
                        await ws.send(json.dumps({"load": load_counter["value"], "metrics": get_metrics()}))

                    if hb_count % 12 == 0:
                        await ws.send(json.dumps({"type": "config_sync"}))
                        log.debug("请求 config_sync")

                    log.debug(f"心跳 load={load_counter['value']}"
                              + (" +hello" if hb_count % 5 == 0 else ""))

        except asyncio.CancelledError:
            break
        except websockets.exceptions.ConnectionClosed as e:
            log.warning(f"连接断开: {e}，3秒后重连...")
        except BaseException as e:
            log.error(f"异常断开: {type(e).__name__}: {e}，3秒后重连...")
        await asyncio.sleep(3)

    log.info("正在关闭...")
    if _active_tasks:
        log.info(f"等待 {len(_active_tasks)} 个任务完成...")
        for t in list(_active_tasks):
            t.cancel()
        await asyncio.gather(*_active_tasks, return_exceptions=True)
    log.info("节点已停止")
