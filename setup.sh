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

# 自动生成 JWT 密钥
if ! grep -q "JWT_SECRET_KEY=change-me" .env 2>/dev/null; then
    true  # 已修改，跳过
else
    NEW_KEY=$(openssl rand -hex 32)
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$NEW_KEY/" .env
    echo "已自动生成 JWT_SECRET_KEY"
fi

mkdir -p app/static/upload

$COMPOSE up -d --build

echo ""
echo "=== 部署完成 ==="
echo "访问: http://localhost:8000"
echo "管理员: admin / Admin123456"
