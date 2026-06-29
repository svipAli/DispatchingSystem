#!/bin/bash
# DispatchingSystem 一键部署脚本
set -e

echo "=== DispatchingSystem 一键部署 ==="

if ! command -v docker &>/dev/null; then
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检测 Compose 版本
if docker compose version &>/dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    COMPOSE="docker-compose"
else
    echo "请安装 Docker Compose"
    exit 1
fi

# 创建 .env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "已创建 .env，请编辑修改 JWT_SECRET_KEY"
fi

mkdir -p app/static/upload

$COMPOSE up -d --build

echo ""
echo "=== 部署完成 ==="
echo "访问: http://localhost:8000"
echo "管理员: admin / Admin123456"
