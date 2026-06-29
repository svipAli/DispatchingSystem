"""
{服务名称: 如"文本生成"}
功能: {一句话描述}
"""
import asyncio
import os
from utils.logger import get_logger

logger = get_logger("service-{service_type}")


async def handle(request_params: dict) -> dict:
    """
    服务入口（签名不可变）
    request_params = {
        "task_id": 123,
        "input":  {"field1": "value1", ...},  # 用户在平台前端填写的参数
        "options": {"source": "mcp_gateway", ...}   # 可选配置
    }
    返回: {"code": 0, "data": {...}}  或  {"code": -1, "message": "...", "data": None}
    """
    task_id = request_params.get("task_id", "?")
    input_data = request_params.get("input", {})

    try:
        # ===== 1. 参数提取 =====
        # param1 = input_data.get("field1", "默认值")
        # if not param1:
        #     return {"code": -2, "message": "缺少必填参数 field1", "data": None}

        # ===== 2. 业务逻辑 =====
        # result = await do_something(param1, param2, ...)

        # ===== 3. 返回结果 =====
        logger.info(f"处理完成 task_id={task_id}")
        return {"code": 0, "message": "success", "data": {}}

    except asyncio.TimeoutError:
        logger.warning(f"超时 task_id={task_id}")
        return {"code": -4, "message": "任务执行超时", "data": None}
    except Exception as e:
        logger.error(f"异常 task_id={task_id}: {e}", exc_info=True)
        return {"code": -3, "message": f"{type(e).__name__}: {e}", "data": None}
