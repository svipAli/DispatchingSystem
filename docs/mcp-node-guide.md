# MCP 节点开发文档

## 一、架构概览

```
┌─────────────────────┐         WebSocket          ┌──────────────────────┐
│   调度平台（主控）    │ ◄──────────────────────────► │    MCP 节点          │
│   localhost:8000     │    心跳 + 服务注册 + 结果回传   │   多个服务 / 多节点   │
└─────────────────────┘                             └──────────────────────┘
```

- 一个物理机可以跑多个节点实例，用端口区分
- 每个节点通过 `node_config.yaml` 声明自己支持哪些 MCP 服务
- 节点启动时自动连接平台、注册服务、维持心跳

---

## 二、目录结构

```
my-mcp-node/                     # 节点根目录
├── node_config.yaml             # 唯一配置文件（核心）
├── requirements.txt             # Python 依赖
├── main.py                      # 入口文件（极简，只启动）
├── watchdog.py                  # 进程看门狗（守护 + 自动重启）
├── core/                        # 核心模块
│   ├── __init__.py
│   ├── ws_client.py             # WebSocket 连接 + 心跳
│   └── registry.py              # 读取配置、组装 hello
├── services/                    # MCP 服务实现代码
│   ├── __init__.py
│   ├── text_generation.py
│   └── code_execution.py
└── utils/
    └── logger.py                # 日志工具（按年月日分目录）
```

**各文件职责：**

| 文件 | 职责 |
|------|------|
| `node_config.yaml` | 唯一配置文件，节点和服务所有配置都在这里 |
| `main.py` | 入口，只负责启动，含代理绕过和异常兜底 |
| `watchdog.py` | 进程看门狗，守护 + 自动重启 + 信号处理 |
| `core/ws_client.py` | WebSocket 连接、心跳、任务收发、并发控制、超时管理 |
| `core/registry.py` | 读取 yaml、组装 hello 消息、配置同步 |
| `services/*.py` | 每个 MCP 服务的实际执行代码 |
| `utils/logger.py` | 日志工具（控制台 + 文件，按年月日分目录） |

### 多节点部署目录示例

```
/mcp-nodes/
├── node-01/
│   ├── node_config.yaml   # id: 2001, port: 8201
│   ├── main.py
│   ├── requirements.txt
│   └── services/
├── node-02/
│   ├── node_config.yaml   # id: 2002, port: 8202
│   ├── main.py
│   ├── requirements.txt
│   └── services/
└── shared/
    └── mcp_base.py
```

---

## 三、node_config.yaml（唯一配置文件）

不需要 .env 文件，所有配置统一在 yaml 中管理。

```yaml
# ===== 节点配置 =====
node:
  id: 2001                        # 节点唯一标识
  name: "GPU服务器-01"             # 节点名称
  port: 8201                      # 节点端口
  max_concurrent: 10              # 最大并发任务数
  platform_ws_url: "ws://192.168.1.100:8000/ws/node/2001"  # 平台地址
  heartbeat_interval: 5           # 心跳间隔（秒）
  description: "4×A100"           # 节点描述

# ===== 服务列表 =====
services:
  - name: "文本生成"
    type: "text-generation"
    version: "1.0.0"
    description: "<h3>功能说明</h3><p>...</p>"
    timeout: 60                     # 超时时间（秒），超时自动终止并返回 timeout 错误
    params:
      - field: "prompt"
        label: "提示词"
        type: "string"
        required: true
        description: "输入给AI的提示文本"
      - field: "max_tokens"
        label: "最大长度"
        type: "int"
        required: false
        default: 1024
        description: "生成文本的最大token数"
      - field: "temperature"
        label: "采样温度"
        type: "float"
        required: false
        default: 0.7
        description: "0-1之间，越高越随机"
  - name: "代码执行"
    type: "code-execution"
    version: "1.0.0"
    description: "<h3>功能说明</h3><p>...</p>"
    timeout: 120                    # 超时时间（秒）
    params:
      - field: "language"
        label: "编程语言"
        type: "string"
        required: true
        description: "python / js / go"
      - field: "code"
        label: "代码内容"
        type: "string"
        required: true
        description: "要执行的代码"
```

### 3.1 参数类型（params）

| type 值 | Python 类型 | 前端表单 | 示例 |
|------|------|------|------|
| string | str | 文本输入框 | `"hello"` |
| int | int | 数字输入框（整数） | `1024` |
| float | float | 数字输入框（小数） | `0.7` |
| bool | bool | 开关选择 | `true` |
| list | list | JSON 数组文本 | `["a","b"]` |
| dict | dict | JSON 对象文本 | `{"key":"value"}` |

| params 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| field | string | 是 | 参数名（英文，与代码中一致） |
| label | string | 是 | 中文标签（前端表单显示） |
| type | string | 是 | 数据类型（string/int/float/bool/list/dict） |
| required | bool | 否 | 是否必填，默认 false |
| default | any | 否 | 默认值 |
| description | string | 否 | 参数说明 |

前端根据 params 自动生成表单，提交时组装为 `{"input": {"field1":"value1",...}}`。`list` 和 `dict` 类型上传时自动做 JSON 序列化后传给 MCP 节点。

| node 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| id | int | 是 | 节点唯一标识 |
| name | string | 是 | 节点名称 |
| port | int | 是 | 节点端口 |
| max_concurrent | int | 是 | 最大并发任务数 |
| platform_ws_url | string | 是 | 平台 WebSocket 地址 |
| heartbeat_interval | int | 否 | 心跳间隔，默认 5 秒 |
| description | string | 否 | 节点描述备注 |

| services[] 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 服务名称（中英文均可） |
| type | string | 是 | 服务标识（英文，调用时路由依据） |
| version | string | 否 | 版本号 |
| description | string | 否 | 服务详情（HTML 富文本） |
| timeout | int | 否 | 任务超时时间（秒），默认 60。≤60秒平台同步等结果，>60秒异步轮询。节点负责在超时后终止任务 |

**多节点示例**：不同节点各自一个目录，各有一个 `node_config.yaml`，改 `id` 和 `port` 即可。同一台机器上 NODE_ID 不能重复。

---

## 四、WebSocket 消息协议

### 4.1 Hello（节点→平台，连接时发送一次，之后每5次心跳重发）

节点首次连接时上报自身配置和服务列表。之后每5次心跳重新发一次 hello，确保平台数据始终同步。

```json
{
  "type": "hello",
  "config": {
    "name": "GPU服务器-01",
    "port": 8101,
    "max_concurrent": 10,
    "description": "4×A100，负责文本生成和代码执行"
  },
  "services": [
    {
      "name": "文本生成",
      "type": "text-generation",
      "version": "1.0.0",
      "description": "<h3>功能说明</h3><p>调用大语言模型生成文本...</p>",
      "timeout": 60,
      "params": [
        {"field":"prompt","label":"提示词","type":"string","required":true}
      ]
    },
    {
      "name": "代码执行",
      "type": "code-execution",
      "version": "1.0.0",
      "description": "<h3>功能说明</h3><p>沙箱执行代码...</p>",
      "timeout": 120
    }
  ]
}
```

| config 字段 | 类型 | 说明 |
|------|------|------|
| name | string | 节点名称 |
| port | int | 节点端口 |
| max_concurrent | int | 最大并发任务数 |
| description | string | 节点描述备注 |

| services[] 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 服务名称（中英文均可） |
| type | string | 是 | 服务标识（英文，调用时路由依据） |
| version | string | 否 | 版本号，如 "1.0.0" |
| description | string | 否 | 服务详情（HTML 富文本） |
| timeout | int | 否 | 超时时间（秒），默认 60。≤60秒平台同步等结果，>60秒平台异步返回 task_id。节点收到任务后必须在 timeout 秒内返回结果 |
| params | array | 否 | 参数定义列表，见 3.1 节 |

平台收到 hello 后自动注册/更新节点和服务信息。

### 4.2 Heartbeat（节点→平台，每 5 秒）

```json
{
  "load": 2
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| load | int | 当前正在执行的任务数，平台据此判断是否下发新任务（load < max_concurrent 才分配） |

`services` 列表变化时可携带，不变则省略。

### 4.3 Task（平台→节点，任务下发）

```json
{
  "type": "task",
  "task_id": 123,
  "service_type": "text-generation",
  "request_params": {
    "input": { "prompt": "你好" },
    "options": { "temperature": 0.7 }
  }
}
```

### 4.4 Result（节点→平台，任务结果回传）

```json
{
  "type": "result",
  "task_id": 123,
  "result": {
    "code": 0,
    "message": "success",
    "data": { "text": "你好！", "tokens": 5 }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| type | string | 固定 "result" |
| task_id | int | 对应任务的 ID |
| result.code | int | 0=成功，非0=失败 |
| result.message | string | 成功时为 "success"，失败时为错误描述 |
| result.data | object | 成功时的返回数据，失败可为 null |

**常见错误码：**

| code | 说明 |
|------|------|
| 0 | 成功 |
| -1 | 通用错误 |
| -2 | 参数错误 |
| -3 | 服务执行异常 |
| -4 | 超时 |
| -5 | 任务被取消 |
| -6 | 节点繁忙（并发已满） |

### 4.7 任务超时处理（重要）

**超时由节点侧负责控制**，平台下发任务时不设置超时时间，而是每个服务有自己的 `timeout` 字段（从 config_sync 获取）。

节点收到任务后：
1. 从服务配置中读取 `timeout` 值（秒）
2. 使用 `asyncio.wait_for` 包裹任务执行，超时则抛出 `TimeoutError`
3. 超时后**主动终止任务**并返回超时失败结果给平台

```python
async def handle_task(ws, task_data):
    service_type = task_data.get("service_type", "")
    timeout = get_service_timeout(service_type)  # 从本地配置/sync中读取
    try:
        result = await asyncio.wait_for(
            process_task(task_data),
            timeout=timeout
        )
        await ws.send(json.dumps({
            "type": "result",
            "task_id": task_data["task_id"],
            "result": result
        }))
    except asyncio.TimeoutError:
        # 超时：返回 code=-4，平台收到后会自动退款
        await ws.send(json.dumps({
            "type": "result",
            "task_id": task_data["task_id"],
            "result": {"code": -4, "message": f"任务执行超时（{timeout}秒）", "data": None}
        }))
    except Exception as e:
        await ws.send(json.dumps({
            "type": "result",
            "task_id": task_data["task_id"],
            "result": {"code": -1, "message": str(e), "data": None}
        }))
```

**平台侧处理**：收到 `code != 0` 的结果 → 标记任务失败 + 自动退款。

**管理端设置**：管理员可在后台服务管理页面修改每个服务的超时时间（单位：秒），修改后节点通过 config_sync 自动同步。

**注意**：`timeout` 由平台端管理，节点上报 hello 时不会覆盖已有的 timeout 值。节点应始终以 config_sync 返回的为准。

### 4.8 节点断连处理（平台侧）

当节点 WebSocket 断开时，平台自动执行以下操作：

1. **标记节点离线**：`node_status` → "offline"
2. **取消等待中的任务**：仍在 `_pending_tasks` 中等待 future 的任务收到"节点已断开"结果
3. **扫描 running 任务**：查询该节点上所有 `status="running"` 的任务，逐个标记为 `failed`（错误信息："节点断连，任务中断"）
4. **自动退款**：每个失败任务已扣的余额原路退回，写 refund 流水记录

节点重连后可继续接收新任务，之前被标记失败的旧任务不会恢复（已退款，用户可重新提交）。

**失败示例：**

```json
{
  "type": "result",
  "task_id": 123,
  "result": {
    "code": -2,
    "message": "缺少必填参数 prompt",
    "data": null
  }
}
```

### 4.5 Config Sync（两段式协议，配置同步）

**两段式协议**：配置同步分两步完成——

**第一步：触发（平台→节点）**
```json
{"type": "config_sync"}
```
平台在没有 config/services 数据的空消息作为触发信号。管理员修改配置后平台立即推送此信号。

**第二步：请求+响应（节点→平台→节点）**
节点收到触发信号后，回传同名请求：
```json
{"type": "config_sync"}
```
平台收到后以数据库为准返回完整配置：
```json
{
  "type": "config_sync",
  "config": {"name": "...", "port": 8201, "max_concurrent": 10, "description": "..."},
  "services": [
    {"name": "...", "type": "...", "version": "...", "description": "...", "params": [...], "timeout": 60}
  ]
}
```
节点收到后判断消息中有 `config` 或 `services` 字段，更新本地 `node_config.yaml` 并重载。

**触发方式**：

| 场景 | 触发方 | 说明 |
|------|--------|------|
| 管理端修改配置 | 平台主动推送 | 改节点/服务配置后立即触发 |
| 节点定期同步 | 节点主动请求 | 建议每 60 秒发一次 config_sync |
| 节点首次连接 | hello 上报 | hello 中包含完整服务列表，等效于初次同步 |

> ⚠️ **重要**：节点收到平台下发的完整配置后，**必须立即更新本地 `node_config.yaml` 文件**，并热重载运行时配置变量。延迟更新会导致后续任务使用过期参数，引发计费错误或执行失败。
>
> 同样，如果管理员**手动编辑了本地配置**，节点也能自动感知——`build_hello_message()` 每次调用都会重新读取 yaml，每 5 次心跳自动同步最新配置到平台。`sync_config_from_platform()` 比较平台下发与本地 yaml，有差异才写入，避免无意义 IO。

**节点实现示例**：
```python
elif data.get("type") == "config_sync":
    if "config" in data or "services" in data:
        # 完整配置响应：更新本地 yaml
        CFG["node"].update(data.get("config", {}))
        CFG["services"] = data.get("services", CFG["services"])
        yaml.dump(CFG, open("node_config.yaml", "w"), allow_unicode=True)
        logger.info("收到完整配置同步，已更新本地 yaml")
    else:
        # 触发信号：请求平台返回完整配置
        await ws.send(json.dumps({"type": "config_sync"}))
```

**注意**：更新 `node_config.yaml` 时保持字段顺序不变。每个 services 条目按 `name` → `type` → `version` → `description` → `params` 顺序写入，避免格式差异导致不必要的比对差异。

### 4.6 `service_type` 不可变更

`service_type` 是服务的唯一标识，一旦创建就不可修改。改名等于创建新服务。

---

## 五、服务注册流程

节点启动时读取 `node_config.yaml`，将服务元数据通过 WebSocket 上报平台：

```python
# main.py 核心逻辑
import yaml
with open('node_config.yaml') as f:
    config = yaml.safe_load(f)

# 连接 WebSocket
ws = await websockets.connect(PLATFORM_WS_URL)

# 首次上报：携带完整服务列表
service_types = [s['type'] for s in config['services']]
await ws.send(json.dumps({
    "load": 0,
    "services": service_types,
    "config": config['services']  # 完整元数据
}))

# 之后只上报负载（服务列表不变就不带）
while True:
    await asyncio.sleep(5)
    await ws.send(json.dumps({"load": current_load}))
```

---

## 六、请求与返回格式标准

### 6.1 用户提交任务（request_params）

```json
{
  "input": { ... },
  "options": { ... }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| input | object | 是 | 服务输入参数，字段由各服务定义 |
| options | object | 否 | 可选配置（超时、模型参数等） |

### 6.2 任务执行结果（result）

```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| code | int | 0=成功，非0=失败 |
| message | string | 结果描述 |
| data | object | 返回数据，字段由各服务定义 |

### 6.3 查询任务结果

用户提交任务后拿到 `task_id`，轮询查询：

```bash
# 查看任务状态
curl -H "Authorization: Bearer <token>" \
  http://平台IP:8000/api/v1/tasks/{task_id}
```

返回：

```json
{
  "code": 0,
  "data": {
    "id": 123,
    "status": "completed",
    "cost": 0.05,
    "result": {
      "code": 0,
      "message": "success",
      "data": { "text": "你好！", "tokens": 5 }
    },
    "created_at": "2026-06-26T10:00:00Z",
    "finished_at": "2026-06-26T10:00:02Z"
  }
}
```

---

## 七、完整入口代码示例

### main.py（入口，极简）

```python
"""
节点入口（极简，只负责启动）
"""
import os

# 绕过系统代理，localhost 直连
os.environ["no_proxy"] = "localhost,127.0.0.1,::1"

from core.ws_client import run_node

if __name__ == "__main__":
    import asyncio
    import traceback
    try:
        asyncio.run(run_node())
    except KeyboardInterrupt:
        pass
    except BaseException as e:
        print(f"节点进程异常退出: {type(e).__name__}: {e}")
        traceback.print_exc()
```

### core/registry.py（配置读取 + hello 组装 + 配置同步）

```python
"""
读取配置、组装 hello 消息、配置同步
"""
import os
import yaml

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_config() -> dict:
    config_path = os.path.join(_BASE_DIR, "node_config.yaml")
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# 启动时加载
CFG = _load_config()
NODE = CFG.get("node", {})
NODE_ID = NODE.get("id", 0)
NODE_PORT = NODE.get("port", 8101)
MAX_CONCURRENT = NODE.get("max_concurrent", 5)
WS_URL = NODE.get("platform_ws_url", f"ws://localhost:8000/ws/node/{NODE_ID}")
INTERVAL = NODE.get("heartbeat_interval", 5)


def build_hello_message() -> dict:
    """每次调用重新读 yaml，支持热更新"""
    cfg = _load_config()
    node = cfg.get("node", {})
    return {
        "type": "hello",
        "config": {
            "name": node.get("name", f"MCP节点-{node.get('id', 0)}"),
            "port": node.get("port", 0),
            "max_concurrent": node.get("max_concurrent", 5),
            "description": node.get("description", ""),
        },
        "services": cfg.get("services", []),
    }


def sync_config_from_platform(platform_config: dict, platform_services: list[dict]) -> bool:
    """对比平台配置与本地 yaml，有差异则更新并返回 True"""
    config_path = os.path.join(_BASE_DIR, "node_config.yaml")
    with open(config_path, encoding="utf-8") as f:
        local = yaml.safe_load(f)

    local_node = local.get("node", {})
    local_services = local.get("services", [])
    changed = False

    if platform_config:
        for key in ("name", "port", "max_concurrent", "description"):
            new_val = platform_config.get(key)
            if new_val is not None and local_node.get(key) != new_val:
                local_node[key] = new_val
                changed = True

    if platform_services:
        local_by_type = {s["type"]: s for s in local_services}
        for ps in platform_services:
            ptype = ps.get("type")
            if not ptype:
                continue
            if ptype in local_by_type:
                existing = local_by_type[ptype]
                for key in ("name", "version", "description", "params", "timeout"):
                    if ps.get(key) is not None and existing.get(key) != ps[key]:
                        existing[key] = ps[key]
                        changed = True
            else:
                local_services.append(ps)
                changed = True

    if changed:
        # 保持字段顺序写入
        ordered_node = {}
        for key in ("id", "name", "port", "max_concurrent", "platform_ws_url",
                     "heartbeat_interval", "description"):
            if key in local_node:
                ordered_node[key] = local_node[key]
        for k, v in local_node.items():
            if k not in ordered_node:
                ordered_node[k] = v

        ordered_services = []
        for s in local_services:
            item = {}
            for key in ("name", "type", "version", "description", "timeout", "params"):
                if key in s:
                    item[key] = s[key]
            for k, v in s.items():
                if k not in item:
                    item[k] = v
            ordered_services.append(item)

        local["node"] = ordered_node
        local["services"] = ordered_services
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(local, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    return changed
```

### core/ws_client.py（WebSocket 连接 + 心跳 + 任务收发）

```python
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


def _reload_config():
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


# ====== 开发者在此定义 SERVICE_MAP 和 _REQUIRED_PARAMS ======
# SERVICE_MAP = {"service-type": handler_function}
# _REQUIRED_PARAMS = {"_common": ["param1"], "service-type": ["param2"]}

_REQUIRED_PARAMS: dict = {"_common": []}


def _check_required(service_type: str, kwargs: dict) -> list[str]:
    missing = []
    for field in _REQUIRED_PARAMS.get("_common", []):
        if not kwargs.get(field):
            missing.append(field)
    for field in _REQUIRED_PARAMS.get(service_type, []):
        if not kwargs.get(field):
            missing.append(field)
    return missing


async def handle_one_task(ws, task_id, service_type, request_params, load_counter):
    """单任务生命周期：路由 → 参数校验 → 执行 → 回传。异常永不泄漏。"""
    result: dict
    try:
        # TODO: 替换为实际 SERVICE_MAP 路由
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
    coro = handle_one_task(ws, task_id, service_type, request_params, load_counter)
    task = asyncio.create_task(coro)
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)


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
                                log.info(f"启动任务 task_id={task_id} type={service_type}")
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
                                log.info("平台触发 config_sync，请求完整配置")
                                await ws.send(json.dumps({"type": "config_sync"}))

                    except asyncio.TimeoutError:
                        pass

                    hb_count += 1
                    if hb_count % 5 == 0:
                        await ws.send(json.dumps(build_hello_message()))
                    else:
                        await ws.send(json.dumps({"load": load_counter["value"]}))

                    if hb_count % 12 == 0:
                        await ws.send(json.dumps({"type": "config_sync"}))
                        log.debug("请求 config_sync")

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
```

### 业务接入点

开发者只需修改 `core/ws_client.py` 中的两处 TODO：

1. **SERVICE_MAP**：将 service_type 映射到 `services/` 下的处理函数
2. **REQUIRED_PARAMS**：声明各服务的必填参数，框架自动校验

服务处理函数签名为 `async def handle(request_params: dict) -> dict`，返回 `{"code": 0, "data": {...}}`。

**requirements.txt：**

```
websockets>=12.0
pyyaml>=6.0
```

---
## 八、并发处理（重要）

平台通过 `max_concurrent` 控制下发任务数，不会超过节点承载。**节点端必须支持并发执行**，不能单线程串行。

根据服务类型选择并发方式：

| 服务类型 | 推荐方式 | 示例 |
|------|------|------|
| API 调用、网页请求、数据库查询 | `asyncio.create_task` | 请求大模型 API、操作数据库 |
| 浏览器自动化（Playwright） | `asyncio.create_task` | 网页登录、表单填写 |
| 浏览器自动化（Selenium） | `asyncio.to_thread` | 只能用同步 Selenium 时 |
| CPU 密集计算、文件处理 | `asyncio.to_thread` | 图像处理、大文件读写 |

### 方案一：asyncio.create_task（推荐，IO 密集场景）

```python
if data.get("type") == "task":
    asyncio.create_task(handle_task(ws, data))
    current_load += 1

async def handle_task(ws, task_data):
    try:
        result = await process_task(...)  # 异步执行，不阻塞心跳
        await ws.send(json.dumps({"type": "result", "task_id": task_data["task_id"], "result": result}))
    except Exception as e:
        await ws.send(json.dumps({"type": "result", "task_id": task_data["task_id"], "result": {"code": -1, "message": str(e), "data": None}}))
```

### 方案二：asyncio.to_thread（CPU 密集或同步代码）

```python
if data.get("type") == "task":
    asyncio.create_task(handle_task(ws, data))
    current_load += 1

async def handle_task(ws, task_data):
    try:
        # 把同步阻塞代码丢到线程池，不阻塞事件循环
        result = await asyncio.to_thread(sync_process_task, task_data)
        await ws.send(json.dumps({"type": "result", "task_id": task_data["task_id"], "result": result}))
    except Exception as e:
        await ws.send(json.dumps({"type": "result", "task_id": task_data["task_id"], "result": {"code": -1, "message": str(e), "data": None}}))
```

### 错误做法：单线程阻塞

```python
# ❌ 直接 await，后面所有消息都得等这个任务跑完
result = await process_task(...)
```

### 浏览器自动化示例（Playwright 异步版）

```python
from playwright.async_api import async_playwright

async def auto_login(params):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(params["input"]["url"])
        await page.fill("#username", params["input"]["username"])
        await page.click("#login-btn")
        await browser.close()
    return {"code": 0, "data": {"status": "ok"}}
```

### 数据库操作

查数据库用异步驱动（`asyncpg`、`aiomysql`），同步驱动丢到 `asyncio.to_thread`。

---

## 九、部署步骤

```bash
# 1. 创建节点目录
mkdir node-01 && cd node-01

# 2. 复制模板文件
cp /path/to/template/main.py .
cp /path/to/template/node_config.yaml .
cp /path/to/template/requirements.txt .
cp /path/to/template/watchdog.py .
cp -r /path/to/template/core .
cp -r /path/to/template/utils .

# 3. 编辑配置
vim node_config.yaml  # 改节点 id、name、服务列表

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动（推荐用看门狗）
python watchdog.py
```

---

## 十、注意事项

1. **节点 ID 不要变**，换了 ID 平台就认不出来了
2. **同一机器多节点用不同目录 + 不同 node_config.yaml + 不同 id**
3. **服务描述用 HTML 富文本**，平台直接渲染给用户看，好好写
4. **服务列表变化时重新上报**，平台自动对比增删
5. **心跳 5 秒一次**，超时 20 秒标记离线
6. **断线自动重连**

---

## 十一、MCP 网关调用规则

平台对外暴露标准 MCP 协议，Dify 等智能体平台通过 SSE 连接后，可调用平台上的服务作为 MCP Tool。

### 11.1 工具列表

调用 `tools/list` 会返回所有已审核上线的服务，外加一个固定的 `query_task` 工具用于轮询异步任务结果。

### 11.2 同步 vs 异步

平台根据服务的 `timeout` 字段自动决定调用模式：

| 服务 timeout | 模式 | 行为 |
|-------------|------|------|
| ≤ 60 秒 | 同步 | 等待任务执行完成，直接返回最终结果 |
| > 60 秒 | 异步 | 立即返回 task_id，需用 query_task 轮询结果 |

### 11.3 统一响应格式

所有工具调用返回统一的 JSON 格式，用 `code` 字段标记成败：

**成功** `code=0`：
```json
{
  "code": 0,
  "task_id": 123,
  "status": "completed",
  "result": {"code": 0, "message": "success", "data": {...}},
  "cost": 0.05
}
```
```json
{
  "code": 0,
  "task_id": 124,
  "status": "queued",
  "estimated_cost": 0.05,
  "timeout_seconds": 600,
  "message": "任务已提交，预计耗时较长（600秒），请使用 query_task 查询执行结果"
}
```

**失败** `code=-1`：
```json
{
  "code": -1,
  "message": "服务 text-generation 暂无可用执行节点",
  "task_id": 125
}
```
```json
{
  "code": -1,
  "message": "余额不足，需要 ¥0.05，当前 ¥0.01",
  "task_id": 126,
  "required": 0.05,
  "balance": 0.01
}
```

### 11.4 query_task 轮询

AI 拿到 task_id 后调用 `query_task` 查询结果：

```json
// 请求
{"name": "query_task", "arguments": {"task_id": 123}}

// 进行中
{"code": 0, "task_id": 123, "status": "running", "message": "任务尚未完成，请稍后再查询"}

// 已完成
{"code": 0, "task_id": 123, "status": "completed", "result": {...}, "cost": 0.05}

// 失败
{"code": -1, "message": "任务失败: 节点断连，任务中断"}
```

---

## 十二、日志系统

### 12.1 日志目录结构

节点使用内置日志模块，按年月日自动分目录：

```
logs/
├── 2026/
│   ├── 06/
│   │   ├── 27.log
│   │   ├── 28.log
│   │   └── 30.log
│   ├── 07/
│   │   ├── 01.log
│   │   └── ...
```

每天一个 `.log` 文件，自动创建目录，无需手动管理。

### 12.2 使用方式

```python
from utils.logger import get_logger

logger = get_logger("node-2001")

logger.info("节点启动")
logger.warning("连接断开，3秒后重连")
logger.error("任务执行失败", exc_info=True)
```

同时输出到**控制台**和**文件**，文件按天滚动。

### 12.3 日志内容建议

| 事件 | 级别 | 示例 |
|------|------|------|
| 节点启动/停止 | INFO | `节点 2001 启动 → ws://...` |
| 平台连接/断开 | INFO/WARNING | `已连接平台` / `连接断开` |
| 收到任务 | INFO | `收到任务 task_id=123 service=text-generation` |
| 任务完成/失败 | INFO/ERROR | `任务完成 task_id=123` |
| 服务执行异常 | ERROR | `text-generation 执行异常: ...` |
| 配置同步 | INFO | `配置已重新加载` |

---

## 十三、进程守护

### 13.1 看门狗（推荐，跨平台）

项目自带 `watchdog.py`，纯 Python 实现，Windows/macOS/Linux 通用。

**规则**：60 秒内最多重启 5 次，超过则停止（防止代码 bug 导致无限重启死循环）。每次重启间隔 5 秒。

```bash
# 使用看门狗启动（替代 python main.py）
python watchdog.py
```

**流程图**：

```
启动 main.py → 进程退出
              ↓
         60秒内重启超过5次？
         ├── 否 → 等5秒 → 重启 main.py
         └── 是 → 报错退出（代码有问题，人工介入）
```

### 13.2 systemd（Linux 生产环境推荐）

```ini
# /etc/systemd/system/mcp-node@.service
[Unit]
Description=MCP Node %i
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/mcp-nodes/node-%i
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5
StartLimitInterval=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mcp-node@2001
sudo systemctl start mcp-node@2001
```

### 13.3 launchd（macOS）

```xml
<!-- ~/Library/LaunchAgents/com.mcp.node.plist -->
<key>KeepAlive</key><true/>
<key>ThrottleInterval</key><integer>5</integer>
```

### 13.4 supervisord（跨平台备选）

```ini
[program:mcp-node-2001]
command=python main.py
directory=/opt/mcp-nodes/node-2001
autorestart=true
startsecs=5
startretries=5
```

---

## 十四、运维监控

### 14.1 指标采集

节点启动后自动采集系统指标，通过心跳上报给平台。依赖 `psutil`：

```bash
pip install psutil
```

**心跳格式**（带 metrics）：

```json
{"load": 2, "metrics": {"cpu": 12.5, "memory_total": 17179869184, "memory_used": 8589934592, "memory_percent": 50.0, "disk_total": 499963174912, "disk_used": 50000000000, "disk_percent": 10.0, "network_rx": 123456789, "network_tx": 987654321, "network_rx_speed": 1024.5, "network_tx_speed": 512.3, "uptime": 86400, "load_avg": 0.5}}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `cpu` | float | CPU 使用率 % |
| `memory_total` | int | 总内存（字节） |
| `memory_used` | int | 已用内存（字节） |
| `memory_percent` | float | 内存使用率 % |
| `disk_total` | int | 磁盘总容量（字节） |
| `disk_used` | int | 磁盘已用（字节） |
| `disk_percent` | float | 磁盘使用率 % |
| `network_rx` | int | 累计接收字节 |
| `network_tx` | int | 累计发送字节 |
| `network_rx_speed` | float | 接收速率（B/s） |
| `network_tx_speed` | float | 发送速率（B/s） |
| `uptime` | int | 系统运行秒数 |
| `load_avg` | float | 1 分钟负载均值 |

### 14.2 代码实现

项目已内置 `get_metrics()` 函数（`core/ws_client.py`），无需额外编写。

### 14.3 平台端

平台收到心跳后自动存储最近 60 条指标到 Redis，管理端 `/admin/monitor` 页面实时展示仪表盘和趋势图。
