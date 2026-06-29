"""
WebSocket 节点测试脚本
模拟 MCP 节点：连接平台 → 心跳 → 接收任务 → 回传结果
用法: python ws_node_test.py
"""
import asyncio
import json
import websockets

NODE_ID = 1
WS_URL = f"ws://localhost:8000/ws/node/{NODE_ID}"


async def process_task(task_id, service_type, params):
    """处理任务（实际节点在这里调用 MCP 服务）"""
    print(f"  📥 收到任务 #{task_id}: {service_type}")
    print(f"     参数: {json.dumps(params, ensure_ascii=False)}")

    # 模拟执行
    await asyncio.sleep(2)

    # 返回结果
    return {
        "code": 0,
        "message": "success",
        "data": {
            "output": f"任务 #{task_id} 执行完成",
            "service": service_type,
            "input": params,
        }
    }


async def main():
    print(f"节点 {NODE_ID} 启动 → {WS_URL}")

    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                print("✅ 已连接平台")

                # 首次连接：发送 hello 消息上报节点配置和服务列表
                await ws.send(json.dumps({
                    "type": "hello",
                    "config": {
                        "name": "GPU服务器01",
                        "port": 8899,
                        "description": "测试节点，支持文本生成和代码执行",
                    },
                    "services": ["text-generation", "code-execution"],
                }))
                print("📋 节点配置已上报")

                heartbeat_count = 0

                while True:
                    # 等待消息（可能是任务下发）
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=5)
                        data = json.loads(msg)

                        if data.get("type") == "task":
                            result = await process_task(...)
                            await ws.send(json.dumps({"type": "result", "task_id": data["task_id"], "result": result}))

                        if data.get("type") == "config_update":
                            print("📝 收到配置更新指令，重新加载")
                            # 实际节点：重新读 node_config.yaml → 发 hello
                            await ws.send(json.dumps({"type": "hello", "config": {...}, "services": [...]}))

                    except asyncio.TimeoutError:
                        pass  # 超时，继续发心跳

                    # 发送心跳
                    heartbeat_count += 1
                    msg = {"load": heartbeat_count % 3}
                    # 每5次心跳重发一次 hello 同步配置
                    if heartbeat_count % 5 == 0:
                        msg["type"] = "hello"
                        msg["config"] = {"name": "GPU服务器01", "port": 8899, "max_concurrent": 10, "description": "测试节点"}
                        msg["services"] = ["text-generation", "code-execution"]
                        print(f"📋 第 {heartbeat_count} 次心跳，配置已同步")
                    await ws.send(json.dumps(msg))
                    print(f"💓 心跳 #{heartbeat_count}")

        except Exception as e:
            print(f"❌ 连接断开: {e}，3秒后重连...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
