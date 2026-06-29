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
