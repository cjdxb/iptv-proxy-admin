# IPTV Proxy Admin

> IPTV 直播源代理和管理系统，支持频道管理、导入导出、订阅生成、健康检测、观看统计与活跃连接监控。

[![License](https://img.shields.io/badge/license-AGPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.3+-green.svg)](https://vuejs.org/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

## 项目简介

IPTV Proxy Admin 提供统一 Web 管理界面，管理 IPTV 频道并提供可订阅的代理地址。

- 支持协议：`http` / `https` / `rtp` / `udp`
- 支持导入：文件上传与远程 URL（M3U/TXT）
- 支持导出：M3U/TXT
- 支持订阅：`/api/subscription/m3u` 与 `/api/subscription/txt`
- 支持统计：观看时长、频道排行、活跃连接

## 核心特性

- 频道与分组管理（CRUD、排序、筛选）
- 统一流代理入口（支持组播经 UDPxy 转换）
- JWT 登录认证（Access Token + Refresh Token）
- 首次默认管理员强制改密（`must_change_password`）
- 健康检测（手动 + 定时 + 重试 + 并发线程）
- 观看历史与活跃连接分离存储（支持僵尸连接回收）
- Web 设置热更新（无需重启 Web 进程）

## 技术栈

- 前端：Vue 3 + Vite + Element Plus + Pinia
- 后端：Flask + SQLAlchemy
- 数据库：SQLite（默认）/ MySQL

## 快速开始

### 环境要求

- Python `3.9+`
- Node.js `18+`
- npm `9+`

### 1. 克隆项目

```bash
git clone https://github.com/cjdxb/iptv-proxy-admin.git
cd iptv-proxy-admin
```

### 2. 启动后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

后端默认监听：`http://127.0.0.1:5000`

### 3. 启动 history-worker（建议同时启动）

```bash
cd backend
source venv/bin/activate
python history_worker.py
```

说明：

- `run.py` 负责 API 与流代理
- `history_worker.py` 负责活跃连接时长刷新与僵尸连接回收
- 生产环境建议两个进程都常驻

### 4. 启动前端

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

前端默认地址：`http://localhost:3000`

### 5. 登录

默认账户：

- 用户名：`admin`
- 密码：`admin123`

首次登录必须先改密，才能访问其他功能。

## 认证与订阅

### 后台 API 认证

- 登录接口：`POST /api/auth/login`
- 请求头：`Authorization: Bearer <access_token>`
- Access 过期后可使用 `POST /api/auth/refresh` 换新令牌

### 播放/订阅认证

- 订阅链接与流代理通过用户订阅 Token 鉴权（URL query 参数）
- 可在“订阅”页面重置 Token；重置后旧订阅链接失效

## 配置说明

后端配置文件：`backend/.env`

常用配置项（以 `backend/.env.example` 为准）：

```bash
# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
SERVER_DEBUG=true

# Database
DATABASE_TYPE=sqlite
DATABASE_PATH=data/db.db

# JWT
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRES_HOURS=24
JWT_REFRESH_EXPIRES_DAYS=7

# Health scheduler
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=1800

# Watch session / worker
HEARTBEAT_INTERVAL_SECONDS=10
ACTIVE_HEARTBEAT_TIMEOUT_SECONDS=45
HISTORY_WORKER_INTERVAL_SECONDS=15

# Gunicorn
GUNICORN_LOG_LEVEL=info
```

更多配置细节见：`docs/configuration.md`

## 项目结构

```text
iptv-proxy-admin/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── channels.py
│   │   │   ├── groups.py
│   │   │   ├── dashboard.py
│   │   │   ├── health.py
│   │   │   ├── history.py
│   │   │   ├── proxy.py
│   │   │   ├── settings.py
│   │   │   └── subscription.py
│   │   ├── models/
│   │   │   ├── active_connection.py
│   │   │   ├── channel.py
│   │   │   ├── channel_group.py
│   │   │   ├── refresh_token.py
│   │   │   ├── settings.py
│   │   │   ├── users.py
│   │   │   └── watch_history.py
│   │   ├── services/
│   │   │   ├── health_checker.py
│   │   │   ├── import_export.py
│   │   │   └── watch_history_saver.py
│   │   ├── utils/
│   │   ├── config.py
│   │   └── __init__.py
│   ├── history_worker.py
│   ├── run.py
│   ├── gunicorn.conf.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── styles/
│   │   ├── utils/
│   │   └── views/
│   └── package.json
└── docs/
    ├── api-reference.md
    ├── configuration.md
    ├── database.md
    ├── deployment-guide.md
    ├── requirements.md
    └── code-optimization.md
```

## 文档索引

- API 文档：`docs/api-reference.md`
- 配置文档：`docs/configuration.md`
- 数据库文档：`docs/database.md`
- 部署文档：`docs/deployment-guide.md`

## 常见问题

### 1. RTP/UDP 频道播放失败

请检查：

- 是否启用了 UDPxy
- UDPxy 地址是否可达（可在“系统设置”中测试）
- 组播网络是否已放通

### 2. 历史记录时长不更新或僵尸连接不回收

请确认 `history_worker.py` 进程正在运行。

### 3. 修改配置后没有生效

- Web 可热更新的配置：在“系统设置”保存后会立即生效（部分 worker 参数需重启 worker）
- 仅环境变量配置项：修改 `.env` 后需要重启相关进程

## 许可证

AGPL-3.0，详见 `LICENSE`。
