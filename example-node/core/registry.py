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


def _node() -> dict:
    return _load_config().get("node", {})


# ---- 节点配置（模块级，启动时加载） ----
CFG = _load_config()
NODE = CFG.get("node", {})
NODE_ID = NODE.get("id", 0)
NODE_PORT = NODE.get("port", 8101)
MAX_CONCURRENT = NODE.get("max_concurrent", 5)
WS_URL = NODE.get("platform_ws_url", f"ws://localhost:8000/ws/node/{NODE_ID}")
INTERVAL = NODE.get("heartbeat_interval", 5)


# ---- hello 消息 ----

def build_hello_message() -> dict:
    """组装 hello 消息，每次调用重新读 yaml（支持热更新）"""
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


# ---- config_sync：平台配置同步 ----

def sync_config_from_platform(platform_config: dict, platform_services: list[dict]) -> bool:
    """
    对比平台下发的配置与本地 node_config.yaml。
    有差异则更新本地 yaml 并返回 True，无差异返回 False。
    """
    config_path = os.path.join(_BASE_DIR, "node_config.yaml")
    with open(config_path, encoding="utf-8") as f:
        local = yaml.safe_load(f)

    local_node = local.get("node", {})
    local_services = local.get("services", [])

    changed = False

    # 对比 node 配置
    if platform_config:
        for key in ("name", "port", "max_concurrent", "description"):
            new_val = platform_config.get(key)
            if new_val is not None and local_node.get(key) != new_val:
                local_node[key] = new_val
                changed = True

    # 对比 services（以 type 为 key 匹配）
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
        # 保持字段顺序：node
        ordered_node = {}
        for key in ("id", "name", "port", "max_concurrent", "platform_ws_url", "heartbeat_interval", "description"):
            if key in local_node:
                ordered_node[key] = local_node[key]
        for k, v in local_node.items():
            if k not in ordered_node:
                ordered_node[k] = v

        # 保持字段顺序：services → name, type, version, description, timeout, params
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
