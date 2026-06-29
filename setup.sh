#!/bin/bash
# DispatchingSystem 一键部署脚本
set -e

echo "=== DispatchingSystem 一键部署 ==="

if ! command -v docker &>/dev/null; then
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

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
    echo ""
    echo ">>> .env 已创建，请先编辑修改以下配置："
    echo "    JWT_SECRET_KEY   — 随机字符串（必改）"
    echo "    DATABASE_URL     — 数据库连接"
    echo "    REDIS_URL        — Redis 地址"
    echo ""
    read -p "编辑完成后按 Enter 继续部署，Ctrl+C 取消..." _
fi

mkdir -p app/static/upload

$COMPOSE up -d --build

echo ""
echo "=== 部署完成 ==="
echo "访问: http://服务器IP:9900"
echo "管理员: admin / Admin123456"
