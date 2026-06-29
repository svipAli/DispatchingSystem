#!/bin/bash
# DispatchingSystem 一键部署脚本
# 用法: bash setup.sh

set -e

echo "=== DispatchingSystem 一键部署 ==="

# 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 创建 .env（如果不存在）
if [ ! -f .env ]; then
    cp .env.example .env
    echo "已创建 .env 文件，请编辑修改 JWT_SECRET_KEY 等重要配置"
fi

# 创建上传目录
mkdir -p app/static/upload

# 构建并启动
docker compose up -d --build

echo ""
echo "=== 部署完成 ==="
echo "访问地址: http://localhost:8000"
echo "管理员账号: admin / Admin123456"
echo "请立即登录并修改密码！"
