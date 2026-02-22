# IPTV Proxy Admin 生产环境部署指南

本文档基于当前代码实现，说明 Linux 服务器部署方式。

## 1. 环境要求

### 硬件

- CPU：2 核及以上
- 内存：2 GB 及以上
- 磁盘：20 GB 及以上

### 软件

- Ubuntu 20.04/22.04（或同类 Linux）
- Python 3.9+
- Node.js 18+
- Nginx 1.18+
- SQLite（默认）或 MySQL 5.7+

## 2. 服务器准备

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx curl wget build-essential
```

可选安装 UDPxy（仅 RTP/UDP 组播转 HTTP 需要）：

```bash
sudo apt install -y udpxy
sudo systemctl enable --now udpxy
curl http://127.0.0.1:3680/status
```

安装 Node.js 18：

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

创建目录：

```bash
sudo mkdir -p /var/www/iptv-proxy-admin
sudo chown -R $USER:$USER /var/www/iptv-proxy-admin
```

## 3. 部署后端

### 3.1 获取代码与安装依赖

```bash
cd /var/www/iptv-proxy-admin
git clone https://github.com/cjdxb/iptv-proxy-admin .

cd backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.2 配置环境变量

```bash
cp .env.example .env
nano .env
```

生产建议：

```bash
SERVER_HOST=127.0.0.1
SERVER_PORT=5000
SERVER_DEBUG=false

DATABASE_TYPE=sqlite
DATABASE_PATH=data/db.db

JWT_SECRET_KEY=<replace-with-random-secret>
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRES_HOURS=24
JWT_REFRESH_EXPIRES_DAYS=7

HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=1800

HEARTBEAT_INTERVAL_SECONDS=10
ACTIVE_HEARTBEAT_TIMEOUT_SECONDS=45
HISTORY_WORKER_INTERVAL_SECONDS=15

GUNICORN_LOG_LEVEL=info
```

> 说明：`create_app()` 启动时会自动 `db.create_all()`、创建默认管理员（若不存在）并加载运行时配置。

### 3.3 本地验证后端

终端 1（Web/API）：

```bash
cd /var/www/iptv-proxy-admin/backend
source venv/bin/activate
gunicorn -c gunicorn.conf.py run:app
```

终端 2（history-worker）：

```bash
cd /var/www/iptv-proxy-admin/backend
source venv/bin/activate
python history_worker.py
```

终端 3（health-worker）：

```bash
cd /var/www/iptv-proxy-admin/backend
source venv/bin/activate
python health_worker.py
```

验证接口：

```bash
curl http://127.0.0.1:5000/api/dashboard/version
```

## 4. 部署前端

```bash
cd /var/www/iptv-proxy-admin/frontend
npm install
npm run build

sudo mkdir -p /var/www/html/iptv-admin
sudo cp -r dist/* /var/www/html/iptv-admin/
sudo chown -R www-data:www-data /var/www/html/iptv-admin
```

## 5. 配置 Nginx

创建配置：

```bash
sudo nano /etc/nginx/sites-available/iptv-admin
```

示例：

```nginx
upstream iptv_backend {
    server 127.0.0.1:5000;
    keepalive 32;
}

server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 50M;

    access_log /var/log/nginx/iptv-admin-access.log;
    error_log /var/log/nginx/iptv-admin-error.log;

    location / {
        root /var/www/html/iptv-admin;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

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

    location /api/proxy/stream/ {
        proxy_pass http://iptv_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_buffering off;
        proxy_request_buffering off;

        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;

        proxy_http_version 1.1;
        proxy_set_header Connection "";
    }
}
```

启用并检查：

```bash
sudo ln -sf /etc/nginx/sites-available/iptv-admin /etc/nginx/sites-enabled/iptv-admin
sudo nginx -t
sudo systemctl reload nginx
```

## 6. 配置 systemd（推荐）

生产建议至少 3 个服务：

- `iptv-proxy-admin-web.service`：Gunicorn Web/API
- `iptv-proxy-admin-worker.service`：history-worker
- `iptv-proxy-admin-health-worker.service`：health-worker

### 6.1 Web 服务

```bash
sudo nano /etc/systemd/system/iptv-proxy-admin-web.service
```

```ini
[Unit]
Description=IPTV Proxy Admin Web Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/iptv-proxy-admin/backend
Environment="PATH=/var/www/iptv-proxy-admin/backend/venv/bin"
ExecStart=/var/www/iptv-proxy-admin/backend/venv/bin/gunicorn -c gunicorn.conf.py run:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.2 History Worker 服务

```bash
sudo nano /etc/systemd/system/iptv-proxy-admin-worker.service
```

```ini
[Unit]
Description=IPTV Proxy Admin History Worker Service
After=network.target iptv-proxy-admin-web.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/iptv-proxy-admin/backend
Environment="PATH=/var/www/iptv-proxy-admin/backend/venv/bin"
ExecStart=/var/www/iptv-proxy-admin/backend/venv/bin/python history_worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.3 Health Worker 服务

```bash
sudo nano /etc/systemd/system/iptv-proxy-admin-health-worker.service
```

```ini
[Unit]
Description=IPTV Proxy Admin Health Worker Service
After=network.target iptv-proxy-admin-web.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/iptv-proxy-admin/backend
Environment="PATH=/var/www/iptv-proxy-admin/backend/venv/bin"
ExecStart=/var/www/iptv-proxy-admin/backend/venv/bin/python health_worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 6.4 启动服务

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now iptv-proxy-admin-web
sudo systemctl enable --now iptv-proxy-admin-worker
sudo systemctl enable --now iptv-proxy-admin-health-worker

sudo systemctl status iptv-proxy-admin-web
sudo systemctl status iptv-proxy-admin-worker
sudo systemctl status iptv-proxy-admin-health-worker
```

日志查看：

```bash
sudo journalctl -u iptv-proxy-admin-web -f
sudo journalctl -u iptv-proxy-admin-worker -f
sudo journalctl -u iptv-proxy-admin-health-worker -f
```

## 7. MySQL（可选）

安装与建库：

```bash
sudo apt install -y mysql-server
sudo systemctl enable --now mysql
sudo mysql -u root -p
```

```sql
CREATE DATABASE iptv_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'iptv_user'@'localhost' IDENTIFIED BY 'your_strong_password';
GRANT ALL PRIVILEGES ON iptv_production.* TO 'iptv_user'@'localhost';
FLUSH PRIVILEGES;
```

更新 `backend/.env`：

```bash
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=iptv_user
MYSQL_PASSWORD=your_strong_password
MYSQL_DB=iptv_production
```

然后重启 Web 与两个 Worker：

```bash
sudo systemctl restart iptv-proxy-admin-web
sudo systemctl restart iptv-proxy-admin-worker
sudo systemctl restart iptv-proxy-admin-health-worker
```

## 8. 部署后检查

- 访问前端：`http://your-domain.com`
- 登录默认账户：`admin / admin123`
- 首次登录立即修改密码
- 在“系统设置”验证 UDPxy、健康检测参数、观看会话参数
- 检查活跃连接/历史记录是否刷新，以及健康状态是否按周期更新

## 9. 更新应用

```bash
cd /var/www/iptv-proxy-admin
git pull origin main

cd backend
source venv/bin/activate
pip install --upgrade -r requirements.txt

cd ../frontend
npm install
npm run build
sudo cp -r dist/* /var/www/html/iptv-admin/

sudo systemctl restart iptv-proxy-admin-web
sudo systemctl restart iptv-proxy-admin-worker
sudo systemctl reload nginx
```
