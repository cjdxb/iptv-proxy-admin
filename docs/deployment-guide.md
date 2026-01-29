# IPTV Proxy Admin 生产环境部署指南

本文档介绍如何在 Linux 服务器上部署 IPTV Proxy Admin 系统。

## 环境要求

### 硬件要求

- **CPU:** 2 核及以上
- **内存:** 2GB 及以上
- **磁盘:** 20GB 及以上
- **网络:** 100Mbps 及以上

### 软件要求

- **操作系统:** Ubuntu 20.04/22.04 LTS（推荐）
- **Python:** 3.9 或以上
- **Node.js:** 16.x 或以上
- **Nginx:** 1.18 或以上
- **数据库:** SQLite（默认）或 MySQL 5.7+

---

## 服务器准备

### 1. 更新系统

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. 安装基础依赖

```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    curl \
    wget \
    build-essential
```

### 3. 安装 UDPxy（可选）

**说明：** 仅当需要组播转 HTTP 功能时安装。

```bash
# 安装 UDPxy
sudo apt install -y udpxy

# 启动 UDPxy 服务（使用默认端口 3680）
sudo systemctl start udpxy
sudo systemctl enable udpxy

# 验证 UDPxy 服务状态
curl http://localhost:3680/status
```

**配置说明：**
- UDPxy 默认监听端口：3680
- 可通过修改 `/etc/default/udpxy` 来调整参数
- 在系统设置中配置 UDPxy 服务地址（例如：`http://192.168.1.1:3680`）

### 4. 安装 Node.js

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

### 4. 创建应用目录

```bash
sudo mkdir -p /var/www/iptv-proxy-admin
sudo chown -R $USER:$USER /var/www/iptv-proxy-admin
```

---

## 后端部署

### 1. 上传代码

```bash
cd /var/www/iptv-proxy-admin

# 从 Git 克隆
git clone https://github.com/cjdxb/iptv-proxy-admin .

# 或使用 rsync/scp 上传
```

### 2. 创建 Python 虚拟环境

```bash
cd /var/www/iptv-proxy-admin/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

**生产环境配置：**

```bash
# 服务器配置
SERVER_HOST=127.0.0.1
SERVER_PORT=5000
SERVER_DEBUG=false

# 数据库配置（SQLite）
DATABASE_TYPE=sqlite
DATABASE_PATH=data/iptv.db

# Session 密钥（必须修改！）
SESSION_SECRET_KEY=$(openssl rand -base64 32)

# UDPxy 配置（如果需要组播转换）
UDPXY_ENABLED=false
UDPXY_URL=http://localhost:3680

# 健康检测配置
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=1800
HEALTH_CHECK_THREADS=3

# 代理配置
PROXY_BUFFER_SIZE=8192

# 观看历史配置
WATCH_HISTORY_SAVE_INTERVAL=60

# 注意：以下配置项可在 Web 界面中配置，此处的值会被数据库配置覆盖：
# - HEALTH_CHECK_THREADS, HEALTH_CHECK_TIMEOUT, HEALTH_CHECK_MAX_RETRIES
# - UDPXY_ENABLED, UDPXY_URL
# - PROXY_BUFFER_SIZE
```

**重要：** 必须修改 `SESSION_SECRET_KEY`，使用 `openssl rand -base64 32` 生成强密钥。

### 4. 初始化数据库

```bash
cd /var/www/iptv-proxy-admin/backend
source venv/bin/activate

python << EOF
from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Database initialized successfully')
EOF
```

### 5. 测试后端服务

```bash
gunicorn -c gunicorn.conf.py run:app

# 在另一个终端测试
curl http://127.0.0.1:5000/api/health/status

# 按 Ctrl+C 停止测试
```

---

## 前端部署

### 1. 安装依赖并构建

```bash
cd /var/www/iptv-proxy-admin/frontend

# 安装依赖
npm install

# 构建生产版本
npm run build
```

### 2. 部署静态文件

```bash
# 创建 Nginx 静态文件目录
sudo mkdir -p /var/www/html/iptv-admin

# 复制构建文件
sudo cp -r /var/www/iptv-proxy-admin/frontend/dist/* /var/www/html/iptv-admin/

# 设置权限
sudo chown -R www-data:www-data /var/www/html/iptv-admin
```

---

## Nginx 配置

### 1. 创建 Nginx 站点配置

```bash
sudo nano /etc/nginx/sites-available/iptv-admin
```

**基础配置：**

```nginx
# 上游后端服务器
upstream iptv_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

# HTTP 服务器
server {
    listen 80;
    server_name your-domain.com;

    # 客户端最大上传大小
    client_max_body_size 50M;

    # 日志
    access_log /var/log/nginx/iptv-admin-access.log;
    error_log /var/log/nginx/iptv-admin-error.log;

    # 前端静态文件
    location / {
        root /var/www/html/iptv-admin;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api/ {
        proxy_pass http://iptv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 流代理特殊配置
    location /api/proxy/stream/ {
        proxy_pass http://iptv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # 禁用缓冲，实时流传输
        proxy_buffering off;
        proxy_request_buffering off;

        # 增加超时时间
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;

        # HTTP/1.1 长连接
        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

### 2. 启用站点配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/iptv-admin /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

---

## Systemd 服务配置

### 1. 创建 Systemd 服务文件

```bash
sudo nano /etc/systemd/system/iptv-proxy-admin.service
```

**服务配置：**

```ini
[Unit]
Description=IPTV Proxy Admin Backend Service
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/iptv-proxy-admin/backend

Environment="PATH=/var/www/iptv-proxy-admin/backend/venv/bin"

ExecStart=/var/www/iptv-proxy-admin/backend/venv/bin/gunicorn \
    -c gunicorn.conf.py \
    run:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. 启动服务

```bash
# 重载 systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable iptv-proxy-admin

# 启动服务
sudo systemctl start iptv-proxy-admin

# 检查状态
sudo systemctl status iptv-proxy-admin

# 查看日志
sudo journalctl -u iptv-proxy-admin -f
```

---

## 数据库配置

### 使用 MySQL（可选，推荐生产环境）

#### 1. 安装 MySQL

```bash
sudo apt install -y mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

#### 2. 创建数据库和用户

```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE iptv_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'iptv_user'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON iptv_production.* TO 'iptv_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### 3. 更新后端配置

编辑 `backend/.env`：

```bash
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=iptv_user
MYSQL_PASSWORD=your_strong_password
MYSQL_DB=iptv_production
```

#### 4. 初始化数据库表

```bash
cd /var/www/iptv-proxy-admin/backend
source venv/bin/activate

python << EOF
from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Database initialized')
EOF
```

---


完成后，访问 `https://your-domain.com` 即可。

---

## 故障排查

### 1. 后端服务无法启动

```bash
# 查看错误日志
sudo journalctl -u iptv-proxy-admin -xe

# 检查端口是否被占用
sudo lsof -i :5000

# 检查权限
ls -la /var/www/iptv-proxy-admin/backend

# 检查 Python 依赖
source venv/bin/activate
pip list
```

### 2. Nginx 502 Bad Gateway

```bash
# 检查后端是否运行
sudo systemctl status iptv-proxy-admin
curl http://127.0.0.1:5000/api/health/status

# 检查 Nginx 错误日志
sudo tail -f /var/log/nginx/iptv-admin-error.log

# 检查 Nginx 配置
sudo nginx -t
```

### 3. 前端页面无法加载

```bash
# 检查静态文件
ls -la /var/www/html/iptv-admin

# 检查 Nginx 配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 4. 数据库连接失败

```bash
# 检查 .env 配置
cat /var/www/iptv-proxy-admin/backend/.env

# 测试数据库连接（MySQL）
mysql -u iptv_user -p iptv_production

# 检查数据库文件权限（SQLite）
ls -la /var/www/iptv-proxy-admin/backend/data/
```

---

## 快速命令参考

```bash
# 服务管理
sudo systemctl start iptv-proxy-admin     # 启动
sudo systemctl stop iptv-proxy-admin      # 停止
sudo systemctl restart iptv-proxy-admin   # 重启
sudo systemctl status iptv-proxy-admin    # 状态

# 日志查看
sudo journalctl -u iptv-proxy-admin -f                      # 后端日志
sudo tail -f /var/log/nginx/iptv-admin-access.log          # Nginx 访问日志
sudo tail -f /var/log/nginx/iptv-admin-error.log           # Nginx 错误日志

# Nginx 管理
sudo nginx -t                              # 测试配置
sudo systemctl reload nginx                # 重载配置
sudo systemctl restart nginx               # 重启
```

---

## 部署检查清单

### 基础配置
- [ ] 修改默认管理员密码（admin/admin123）
- [ ] 生成并配置 SESSION_SECRET_KEY
- [ ] 配置正确的域名

### 服务配置
- [ ] 后端服务正常启动
- [ ] Nginx 配置无错误
- [ ] 前端静态文件部署成功
- [ ] API 接口可访问

### 功能配置
- [ ] 配置健康检测线程数（推荐 3-5）
- [ ] 配置观看历史保存间隔（推荐 60-120 秒）
- [ ] 测试 UDPxy 连接（如果启用了组播功能）
- [ ] 验证观看历史记录正常保存
- [ ] 确认多线程健康检测正常运行
- [ ] 测试频道筛选功能（按分组、协议、状态）

### 数据库
- [ ] 数据库初始化成功
- [ ] 数据库连接正常
- [ ] 设置自动备份

### 安全
- [ ] 配置 HTTPS（建议）
- [ ] 修改默认密码
- [ ] 配置防火墙（仅开放 80/443/22）

### 监控
- [ ] 配置自动备份
- [ ] 测试日志查看
- [ ] 验证服务开机自启

---

完成以上步骤后，你的 IPTV Proxy Admin 系统已成功部署。

**重要提醒：立即修改默认管理员密码（admin/admin123）**

访问 `https://your-domain.com` 开始使用！

---

## 更新应用

```bash
# 1. 备份数据库
/usr/local/bin/backup-iptv-db.sh

# 2. 拉取最新代码
cd /var/www/iptv-proxy-admin
git pull origin main

# 3. 更新后端依赖
cd backend
source venv/bin/activate
pip install --upgrade -r requirements.txt

# 4. 更新前端
cd ../frontend
npm install
npm run build
sudo cp -r dist/* /var/www/html/iptv-admin/

# 5. 重启服务
sudo systemctl restart iptv-proxy-admin
sudo systemctl reload nginx
```
