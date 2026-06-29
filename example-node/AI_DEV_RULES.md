# AI 开发规则 - MCP 服务

生成代码前，请严格遵守以下规则。

---

## 一、服务函数签名（不可变）

```python
async def handle(request_params: dict) -> dict:
    """
    request_params = {
        "input":  {...},   # 用户填写的参数
        "options": {...}   # 可选配置
    }
    返回: {"code": 0, "data": {...}}  或  {"code": -1, "message": "错误原因", "data": None}
    """
```

签名永远不能变。平台按此约定传参和解析结果。

---

## 二、异常铁律

**所有异常必须内部消化，永不泄漏到主循环。**

```python
async def handle(request_params: dict) -> dict:
    try:
        ...
        return {"code": 0, "data": {...}}
    except SomeExpectedError as e:
        return {"code": -1, "message": str(e), "data": None}
    except Exception as e:
        logger.error(f"未预期异常: {e}", exc_info=True)
        return {"code": -3, "message": "服务内部异常", "data": None}
```

严禁写不带 try/except 的 handler。一次未捕获的异常会导致节点崩掉。

---

## 三、超时控制（强制）

**所有服务 handler 必须用 `asyncio.wait_for` 包裹执行逻辑。** 超时时间从 `_get_timeout(service_type)` 读取，而不是硬编码。违反此规则会导致平台修改超时后节点不生效。

```python
from core.ws_client import _get_timeout

async def handle(request_params: dict) -> dict:
    service_type = request_params.get("service_type", "unknown")
    timeout = _get_timeout(service_type)  # 从热重载后的配置读取
    try:
        result = await asyncio.wait_for(do_work(...), timeout=timeout)
        return {"code": 0, "data": result}
    except asyncio.TimeoutError:
        return {"code": -4, "message": f"任务执行超时（{timeout}秒）", "data": None}
```

**为什么必须这样做：**
1. 平台可通过 `config_sync` 实时修改超时时间
2. `_get_timeout` 读取的是热重载后的配置，始终是最新值
3. 不用 `asyncio.wait_for` 的服务，修改超时不会生效
4. 超时返回 `code: -4`，平台会自动退款

**禁止的做法：**
```python
# ✗ 没有超时控制
result = await do_work(...)

# ✗ 硬编码超时
result = await asyncio.wait_for(do_work(...), timeout=60)

# ✗ 从 request_params 取超时（那是平台侧的，不是节点侧要用的）
timeout = request_params.get("options", {}).get("timeout", 60)
```

---

## 四、返回数据格式

`data` 字段中的值必须可 JSON 序列化：
- ✓ dict、list、str、int、float、bool、None
- ✗ datetime、bytes、自定义对象、Decimal

遇到不可序列化的对象，先转字符串或格式化：

```python
return {"code": 0, "data": {"created_at": created_at.isoformat()}}
```

---

## 五、路径禁止硬编码

```python
# ✓ 正确
import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
config_path = os.path.join(BASE, "configs", "settings.json")

# ✗ 错误
config_path = "/home/user/my-node/configs/settings.json"
```

---

## 六、文件写入规则

- 所有输出文件写入 `output/` 目录（按 task_id 分子目录防冲突）
- 不要往节点根目录写临时文件
- 写完后清理临时文件

```python
import os, tempfile
task_dir = os.path.join("output", str(task_id)) if task_id else tempfile.mkdtemp()
os.makedirs(task_dir, exist_ok=True)
# ... 写入 task_dir ...
```

---

## 七、禁止引入平台侧概念

服务 handler 不要引用平台代码（app.modules、app.core 等）。节点是独立进程，和平台零依赖。

```python
# ✗ 禁止
from app.modules.task.models import Task
from app.core.security import hash_password

# ✓ 允许
import requests, aiohttp, playwright, PIL, pdfplumber, openpyxl
```

---

## 八、依赖声明

新增第三方库必须在节点根目录 `requirements.txt` 中声明，且注明版本下限。

---

## 九、日志规范

```python
from utils.logger import get_logger
logger = get_logger("service-{name}")

logger.info(f"开始处理 task_id={task_id}")
logger.error(f"处理失败: {e}", exc_info=True)
```

不要用 `print()`。日志会自动写入 `logs/年/月/日.log`。

---

## 十、错误码约定

| code | 含义 |
|------|------|
| 0 | 成功 |
| -1 | 通用/业务错误（参数非法、条件不满足等） |
| -2 | 参数缺失 |
| -3 | 服务内部异常（代码 bug） |
| -4 | 超时（框架已处理，业务代码不用返回） |
