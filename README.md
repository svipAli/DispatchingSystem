# DispatchingSystem — MCP 服务调度与计费平台

管理局域网内多台 MCP 服务器的调度中台，提供统一 API、Web 管理界面、Dify 智能体对接。

## 技术栈

| 层面 | 选型 |
|------|------|
| 后端框架 | FastAPI (Python 3.11) |
| 数据库 | PostgreSQL + asyncpg + SQLAlchemy 2.0 async |
| 缓存 | Redis |
| 任务调度 | asyncio（内建异步） |
| 认证 | JWT (python-jose) |
| 前端 | Jinja2 + Tailwind CSS + Alpine.js |
| 图表 | ECharts |
| 部署 | Docker Compose |

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/svipAli/DispatchingSystem.git
cd DispatchingSystem

# 2. 配置环境变量
cp .env.example .env
vim .env  # 修改数据库连接、Redis 地址、JWT 密钥

# 3. 安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. 数据库迁移
alembic upgrade head

# 5. 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

或使用 Docker：

```bash
docker compose up -d
```

## 功能模块

### 用户系统
- 注册/登录、JWT 鉴权
- 个人信息编辑、实名认证
- 忘记密码（邮件重置）

### MCP 网关（Dify 对接）
- 标准 MCP 协议 SSE 传输
- `GET /mcp/sse` + `POST /mcp/messages`
- 工具列表自动发现、任务提交、状态查询
- 短任务同步返回，长任务异步轮询

### 节点与服务管理
- MCP 节点心跳 + 配置同步
- 服务参数定义与校验
- 超时控制（平台端可配）
- WebSocket 实时通信

### AI 运维助手
- WebSocket 流式对话
- Agent 模式：自动调用工具查询系统状态
- 支持 OpenAI 兼容接口（DeepSeek / GPT）

### 运维监控
- 平台 + 节点双维度监控
- ECharts 仪表盘 + 趋势图
- CPU、内存、磁盘、网络实时采集

### 计费系统
- 预扣费 + 退款
- 充值管理、流水记录
- 余额显示、消费明细

## 项目结构

```
DispatchingSystem/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── core/                   # 安全、数据库、WebSocket
│   ├── modules/                # 业务模块（14 个）
│   │   ├── user/               # 用户
│   │   ├── mcp_node/           # MCP 节点 + 服务
│   │   ├── task/               # 任务调度
│   │   ├── billing/            # 计费流水
│   │   ├── recharge/           # 充值
│   │   ├── api_token/          # API Token
│   │   ├── mcp_gateway/        # MCP 网关
│   │   ├── ai_admin/           # AI 助手
│   │   ├── ws/                 # WebSocket
│   │   └── ...
│   ├── templates/              # Jinja2 页面
│   └── static/                 # 静态文件
├── docs/                       # 开发文档
├── example-node/               # MCP 节点开发示例
├── tests/                      # 单元测试（73 个）
└── alembic/                    # 数据库迁移
```

## 开发文档

详细开发文档：[docs/mcp-node-guide.md](docs/mcp-node-guide.md)

## License

MIT
