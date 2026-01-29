# IPTV Proxy Admin

> 一个 IPTV 直播源代理和管理系统，支持频道管理、订阅生成、健康检测和观看统计。

[![License](https://img.shields.io/badge/license-AGPL%20v3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.3+-green.svg)](https://vuejs.org/)
[![Node](https://img.shields.io/badge/node-16+-green.svg)](https://nodejs.org/)

## 项目简介

IPTV Proxy Admin 是一个 IPTV 直播源代理和管理系统，提供了直观的 Web 界面来统一管理 IPTV 源。系统支持多种直播协议（HTTP/HTTPS/RTP/UDP），能够自动检测频道健康状态，生成标准的 M3U/TXT 订阅链接，并提供详细的观看统计数据。

### 核心特性

- 📺 **频道管理** - 支持管理频道，自定义频道logo、分组、tvg-id、排序
- 🔄 **智能代理** - 统一流代理入口，支持 HTTP/HTTPS/RTP/UDP 多种协议
- 🌐 **订阅服务** - 自动生成 M3U/TXT 格式订阅链接，支持 EPG 配置
- 💚 **健康检测** - 定时自动检测频道可用性，实时显示健康状态
- 📊 **数据统计** - 观看时长统计、频道热度排行、实时连接监控
- 📥 **导入导出** - 支持 M3U/TXT 格式批量导入导出，正则过滤
- 🎨 **现代界面** - 基于 Vue 3 + Element Plus 的响应式界面
- 🔐 **安全认证** - 用户登录系统、Token 订阅验证

## 功能特性

### 频道管理

- ✅ 频道增删改查
- ✅ 分组管理和排序
- ✅ 批量操作（导入/导出/删除）
- ✅ 频道搜索和筛选
- ✅ 支持 Logo 和 EPG 配置
- ✅ 启用/禁用频道

### 协议支持

| 协议 | 说明 | 示例 |
|------|------|------|
| **HTTP** | 标准 HTTP 流 | `http://example.com/stream.m3u8` |
| **HTTPS** | 加密 HTTPS 流 | `https://example.com/stream.m3u8` |
| **RTP** | RTP 组播流 | `rtp://239.0.0.1:5000` |
| **UDP** | UDP 组播流 | `udp://@239.0.0.1:5000` |

**组播源转单播：** 支持通过 UDPxy 将 RTP/UDP 组播流转换为 HTTP 流。

**组播转单播需要安装UDPxy服务。**

### 健康检测

- 🔍 自动定时检测（可配置间隔）
- 🎯 智能检测策略（HTTP HEAD 请求、UDP Socket）
- 📈 实时健康状态显示
- ⚠️ 不健康频道提醒
- 🔧 手动触发检测

### 订阅服务

**M3U 格式：**
```m3u
#EXTM3U x-tvg-url="http://epg.example.com/guide.xml"
#EXTINF:-1 tvg-id="cctv1" tvg-name="CCTV-1" tvg-logo="http://logo.com/cctv1.png" group-title="央视",CCTV-1
http://your-server.com/api/proxy/stream/1?token=your_token
```

**TXT 格式：**
```
央视,#genre#
CCTV-1,http://your-server.com/api/proxy/stream/1?token=your_token
CCTV-2,http://your-server.com/api/proxy/stream/2?token=your_token
```

### 数据统计

- 📊 每日观看时长图表
- 🏆 频道热度排行榜
- 👥 实时连接数监控
- 📈 IPTV源协议分布统计
- 💾 观看历史记录

## 技术栈

- **前端：** Vue 3.3
- **后端：** Flask 3.0 
- **数据库：** SQLite / MySQL

## 快速开始

### 环境要求

- **Python:** 3.9+
- **Node.js:** 16+
- **数据库：** SQLite（默认）或 MySQL 5.7+
- **操作系统：** Linux / macOS / Windows

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/cjdxb/iptv-proxy-admin.git
cd iptv-proxy-admin
```

#### 2. 后端配置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置文件
```

**环境变量配置：**

```bash
# 服务器配置
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
SERVER_DEBUG=true

# 数据库配置
DATABASE_TYPE=sqlite
DATABASE_PATH=data/iptv.db

# Session 密钥
SESSION_SECRET_KEY=your-secret-key-here

# 健康检测
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=1800

# 观看历史保存间隔（秒）
WATCH_HISTORY_SAVE_INTERVAL=60
```

#### 3. 启动后端

```bash
cd backend
source venv/bin/activate
python run.py
```

后端服务将运行在 `http://localhost:5000`

#### 4. 前端配置

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 配置 API 地址
cp .env.example .env
nano .env
```

**前端环境变量：**

```bash
VITE_API_TARGET=http://localhost:5000
```

#### 5. 启动前端

```bash
cd frontend
npm run dev
```

前端服务将运行在 `http://localhost:3000`

#### 6. 访问系统

打开浏览器访问：`http://localhost:3000`

**默认账户：**
- 用户名：`admin`
- 密码：`admin123`

> ⚠️ **重要：** 首次登录后请立即修改默认密码！

## 项目结构

```
iptv-proxy-admin/
├── backend/                    # 后端代码
│   ├── app/                   # Flask 应用
│   │   ├── __init__.py       # 应用工厂
│   │   ├── config.py         # 配置加载
│   │   ├── api/              # API 路由
│   │   │   ├── auth.py       # 用户认证
│   │   │   ├── channels.py   # 频道管理
│   │   │   ├── groups.py     # 分组管理
│   │   │   ├── dashboard.py  # 仪表盘
│   │   │   ├── health.py     # 健康检测
│   │   │   ├── proxy.py      # 流代理
│   │   │   ├── settings.py   # 系统设置
│   │   │   └── subscription.py # 订阅服务
│   │   ├── models/           # 数据模型
│   │   │   ├── user.py       # 用户模型
│   │   │   ├── channel.py    # 频道模型
│   │   │   ├── watch_history.py # 观看历史
│   │   │   └── settings.py   # 设置模型
│   │   ├── services/         # 业务服务
│   │   │   ├── health_checker.py # 健康检测
│   │   │   ├── import_export.py  # 导入导出
│   │   │   └── watch_history_saver.py # 历史保存
│   │   └── utils/            # 工具函数
│   │       └── auth.py       # 认证工具
│   ├── data/                 # 数据目录（SQLite）
│   ├── venv/                 # Python 虚拟环境
│   ├── .env                  # 环境变量配置
│   ├── run.py                # 应用入口
│   ├── gunicorn.conf.py      # Gunicorn 配置
│   └── requirements.txt      # Python 依赖
│
├── frontend/                  # 前端代码
│   ├── src/
│   │   ├── api/              # API 封装
│   │   │   └── index.js
│   │   ├── layouts/          # 布局组件
│   │   │   └── MainLayout.vue
│   │   ├── views/            # 页面组件
│   │   │   ├── Login.vue     # 登录页
│   │   │   ├── Dashboard.vue # 仪表盘
│   │   │   ├── Channels.vue  # 频道管理
│   │   │   ├── Groups.vue    # 分组管理
│   │   │   ├── Settings.vue  # 系统设置
│   │   │   ├── Subscription.vue # 订阅管理
│   │   │   └── ProxyStatus.vue # 代理状态
│   │   ├── stores/           # Pinia 状态
│   │   │   ├── auth.js       # 认证状态
│   │   │   ├── site.js       # 站点状态
│   │   │   └── theme.js      # 主题状态
│   │   ├── router/           # 路由配置
│   │   │   └── index.js
│   │   ├── styles/           # 全局样式
│   │   │   └── index.css
│   │   ├── App.vue           # 根组件
│   │   └── main.js           # 入口文件
│   ├── public/               # 静态资源
│   ├── dist/                 # 构建输出
│   ├── .env                  # 环境变量
│   ├── package.json          # npm 依赖
│   └── vite.config.js        # Vite 配置
│
├── docs/                      # 项目文档
│   ├── api-reference.md      # API 文档
│   ├── database.md           # 数据库文档
│   └── deployment-guide.md   # 部署指南
│
├── .gitignore                # Git 忽略文件
└── README.md                 # 项目说明
```

## 开发指南

### API 开发

所有 API 接口遵循 RESTful 规范：

```
GET    /api/channels          # 获取频道列表
POST   /api/channels          # 创建频道
GET    /api/channels/:id      # 获取单个频道
PUT    /api/channels/:id      # 更新频道
DELETE /api/channels/:id      # 删除频道
```

详细 API 文档：[docs/api-reference.md](docs/api-reference.md)

### 数据库操作

使用 SQLAlchemy ORM：

```python
from app.models.channel import Channel

# 查询所有频道
channels = Channel.query.all()

# 查询单个频道
channel = Channel.query.get(channel_id)

# 创建频道
channel = Channel(name='CCTV-1', url='http://...')
db.session.add(channel)
db.session.commit()

# 更新频道
channel.name = 'CCTV-1 HD'
db.session.commit()

# 删除频道
db.session.delete(channel)
db.session.commit()
```

数据库文档：[docs/database.md](docs/database.md)

## 部署指南

### 生产环境部署

完整的生产环境部署指南请参考：[docs/deployment-guide.md](docs/deployment-guide.md)

**快速部署步骤：**

1. 安装系统依赖
2. 配置后端环境变量
3. 构建前端静态文件
4. 配置 Nginx 反向代理
5. 配置 Systemd 服务
6. 启用 HTTPS（推荐）

### Docker 部署（即将支持）

```bash
# 即将推出 Docker Compose 一键部署
docker-compose up -d
```

## 使用说明

### 添加频道

1. 登录系统
2. 进入「频道管理」页面
3. 点击「添加频道」按钮
4. 填写频道信息：
   - 频道名称
   - 直播源 URL
   - Logo URL（可选）
   - EPG ID（可选）
   - 所属分组
5. 保存

### 导入频道

1. 进入「频道管理」页面
2. 点击「导入频道」按钮
3. 选择导入方式：
   - 上传文件（M3U/TXT）
   - 从 URL 导入
4. 配置导入选项：
   - 是否覆盖现有频道
   - 是否自动创建分组
   - 包含/排除过滤规则
5. 开始导入

### 获取订阅链接

1. 进入「订阅管理」页面
2. 复制订阅链接：
   - M3U 格式：`http://your-server.com/api/subscription/m3u?token=xxx`
   - TXT 格式：`http://your-server.com/api/subscription/txt?token=xxx`
3. 在播放器中添加订阅链接

**支持的播放器：**
- IPTV（iOS/Android）
- VLC Media Player
- PotPlayer
- Kodi
- 其他支持 M3U 的播放器

### 配置 EPG

1. 进入「系统设置」页面
2. 设置 EPG URL：`http://epg.example.com/guide.xml`
3. 在频道编辑页面设置 `tvg-id`
4. 保存后重新下载订阅链接

## 常见问题

### 1. 后端无法启动

**检查步骤：**
```bash
# 查看日志
journalctl -u iptv-proxy-admin -f

# 检查端口占用
lsof -i :5000

# 检查 Python 依赖
pip list
```

### 2. 前端页面空白

**解决方法：**
```bash
# 清除缓存并重新构建
cd frontend
rm -rf node_modules dist
npm install
npm run build
```

### 3. 组播源无法播放

**配置 UDPxy：**
```bash
# 启用 UDPxy
UDPXY_ENABLED=true
UDPXY_URL=http://localhost:4022
```

### 4. 健康检测失败

**检查配置：**
- HTTP/HTTPS：检查 URL 是否可访问
- RTP/UDP：确保 UDPxy 已配置且运行
- 调整检测超时：`HEALTH_CHECK_TIMEOUT=10`

## 许可证

本项目采用 GNU Affero General Public License v3.0 (AGPL-3.0) 许可证 - 详见 [LICENSE](LICENSE) 文件

**简要说明：**
- ✅ 可以自由使用、修改和分发本项目
- ✅ 可以用于商业用途
- ⚠️ 如果修改代码并提供网络服务，必须开源修改后的代码
- ⚠️ 必须保留原作者版权信息
- ⚠️ 衍生项目必须使用相同的 AGPL-3.0 许可证

## 作者

- **GitHub:** [@cjdxb](https://github.com/cjdxb)

## 支持

如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！

---

**Made with ❤️ by [cjdxb](https://github.com/cjdxb)**
