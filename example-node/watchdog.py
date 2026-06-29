"""
节点进程看门狗
- 守护 main.py 进程，挂了自动重启
- 60 秒内最多重启 5 次，超限则停止（防止代码 bug 导致死循环）
- 每次重启间隔 5 秒
- Ctrl+C 正常退出
- 跨平台（纯 Python，Windows/macOS/Linux 通用）
"""
import sys
import time
import subprocess
import signal

MAX_RESTARTS = 5       # 60秒内最多重启次数
RESTART_WINDOW = 60     # 统计窗口（秒）
RESTART_DELAY = 5       # 重启间隔（秒）

running = True


def shutdown(sig, frame):
    global running
    running = False
    print("\n看门狗退出")


signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    cmd = [sys.executable, "main.py"]
    restart_times = []

    while running:
        print(f"启动节点: {' '.join(cmd)}")
        proc = subprocess.Popen(cmd)
        proc.wait()

        if not running:
            proc.terminate()
            break

        now = time.time()
        restart_times = [t for t in restart_times if now - t < RESTART_WINDOW]
        restart_times.append(now)

        if len(restart_times) >= MAX_RESTARTS:
            print(f"60秒内重启了 {len(restart_times)} 次，疑似代码问题，看门狗停止")
            sys.exit(1)

        print(f"节点退出，{RESTART_DELAY}秒后重启（60秒内第 {len(restart_times)} 次）")
        time.sleep(RESTART_DELAY)
