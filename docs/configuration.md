# IPTV Proxy Admin 配置文档

本文档详细说明 IPTV Proxy Admin 系统的所有配置选项。

---

## 配置文件

配置通过环境变量加载，主要配置文件：

- **生产环境**: `backend/.env`
- **配置模板**: `backend/.env.example`

---

## 环境变量配置

### 服务器配置

#### SERVER_HOST
- **说明**: 服务器监听地址
- **类型**: String
- **默认值**: `0.0.0.0`
- **示例**: `127.0.0.1` (仅本地访问) / `0.0.0.0` (允许外部访问)

#### SERVER_PORT
- **说明**: 服务器监听端口
- **类型**: Integer
- **默认值**: `5000`
- **示例**: `8000`

#### SERVER_DEBUG
- **说明**: 是否启用调试模式
- **类型**: Boolean
- **默认值**: `false`
- **示例**: `true` / `false`
- **注意**: 生产环境必须设置为 `false`

---

### 数据库配置

#### DATABASE_TYPE
- **说明**: 数据库类型
- **类型**: String
- **默认值**: `sqlite`
- **可选值**: `sqlite` / `mysql`
- **示例**: `mysql`

#### DATABASE_PATH
- **说明**: SQLite 数据库文件路径（仅当 DATABASE_TYPE=sqlite 时有效）
- **类型**: String
- **默认值**: `data/iptv.db`
- **示例**: `/var/lib/iptv/iptv.db`

#### MYSQL_HOST
- **说明**: MySQL 服务器地址（仅当 DATABASE_TYPE=mysql 时需要）
- **类型**: String
- **默认值**: `localhost`
- **示例**: `192.168.1.100`

#### MYSQL_PORT
- **说明**: MySQL 服务器端口（仅当 DATABASE_TYPE=mysql 时需要）
- **类型**: Integer
- **默认值**: `3306`
- **示例**: `3306`

#### MYSQL_USER
- **说明**: MySQL 数据库用户名（仅当 DATABASE_TYPE=mysql 时需要）
- **类型**: String
- **默认值**: `root`
- **示例**: `iptv_user`

#### MYSQL_PASSWORD
- **说明**: MySQL 数据库密码（仅当 DATABASE_TYPE=mysql 时需要）
- **类型**: String
- **默认值**: `root`
- **示例**: `your_secure_password`

#### MYSQL_DB
- **说明**: MySQL 数据库名称（仅当 DATABASE_TYPE=mysql 时需要）
- **类型**: String
- **默认值**: `iptv`
- **示例**: `iptv_production`

---

### 会话配置

#### SESSION_SECRET_KEY
- **说明**: Flask Session 密钥（用于加密会话数据）
- **类型**: String
- **默认值**: `default-secret-key`
- **示例**: `your-random-secret-key-change-in-production`
- **注意**: 生产环境必须更改为随机字符串
- **生成方法**:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

---

### UDPxy 配置

#### UDPXY_ENABLED
- **说明**: 是否启用 UDPxy 代理（用于组播转 HTTP）
- **类型**: Boolean
- **默认值**: `false`
- **示例**: `true` / `false`

#### UDPXY_URL
- **说明**: UDPxy 代理服务器地址
- **类型**: String (URL)
- **默认值**: `http://localhost:3680`
- **示例**: `http://192.168.1.1:4022`
- **注意**: 仅当 UDPXY_ENABLED=true 时生效

---

### 健康检测配置

#### HEALTH_CHECK_ENABLED
- **说明**: 是否启用定时健康检测
- **类型**: Boolean
- **默认值**: `true`
- **示例**: `true` / `false`

#### HEALTH_CHECK_INTERVAL
- **说明**: 健康检测间隔时间（秒）
- **类型**: Integer
- **默认值**: `1800` (30分钟)
- **示例**: `3600` (1小时) / `600` (10分钟)
- **建议值**: 600-3600 秒之间

#### HEALTH_CHECK_TIMEOUT
- **说明**: 单个频道健康检测超时时间（秒）
- **类型**: Integer
- **默认值**: `10`
- **示例**: `5` / `15`
- **建议值**: 5-30 秒之间

#### HEALTH_CHECK_MAX_RETRIES
- **说明**: 健康检测失败后的重试次数
- **类型**: Integer
- **默认值**: `1`
- **示例**: `2` / `3`
- **说明**: 设置为 1 表示失败后重试 1 次（共检测 2 次）

---

### 代理配置

#### PROXY_BUFFER_SIZE
- **说明**: 代理流传输缓冲区大小（字节）
- **类型**: Integer
- **默认值**: `8192` (8KB)
- **示例**: `16384` (16KB) / `4096` (4KB)
- **建议值**: 4096-16384 之间

---

### 观看历史配置

#### WATCH_HISTORY_SAVE_INTERVAL
- **说明**: 观看历史自动保存间隔（秒）
- **类型**: Integer
- **默认值**: `60` (1分钟)
- **示例**: `30` / `120`
- **说明**: 定期将活跃连接的观看时长保存到数据库
- **建议值**: 30-300 秒之间
- **注意**: 间隔越短，数据越准确，但数据库写入频率越高

---

## 配置示例

### 开发环境配置

```bash
# Server Config
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
SERVER_DEBUG=true

# Database Config
DATABASE_TYPE=sqlite
DATABASE_PATH=data/iptv.db

# Session Config
SESSION_SECRET_KEY=dev-secret-key

# UDPxy Config
UDPXY_ENABLED=false
UDPXY_URL=http://localhost:4022

# Health Check Config
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=1800
HEALTH_CHECK_TIMEOUT=10
HEALTH_CHECK_MAX_RETRIES=1

# Proxy Config
PROXY_BUFFER_SIZE=8192

# Watch History Config
WATCH_HISTORY_SAVE_INTERVAL=60
```

### 生产环境配置

```bash
# Server Config
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
SERVER_DEBUG=false

# Database Config
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=iptv_user
MYSQL_PASSWORD=your_secure_password_here
MYSQL_DB=iptv_production

# Session Config
SESSION_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# UDPxy Config
UDPXY_ENABLED=true
UDPXY_URL=http://192.168.1.1:4022

# Health Check Config
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=3600
HEALTH_CHECK_TIMEOUT=15
HEALTH_CHECK_MAX_RETRIES=2

# Proxy Config
PROXY_BUFFER_SIZE=16384

# Watch History Config
WATCH_HISTORY_SAVE_INTERVAL=120
```

---

## 配置加载顺序

1. 系统从 `backend/.env` 文件加载环境变量
2. 如果某个变量未定义，使用默认值
3. 配置在应用启动时加载一次，修改后需重启服务生效

---

## 配置修改

### 修改配置步骤

1. 编辑 `backend/.env` 文件
2. 修改需要变更的配置项
3. 重启应用服务：
   ```bash
   # 开发环境
   cd backend
   source venv/bin/activate
   python run.py

   # 生产环境（Systemd）
   sudo systemctl restart iptv-admin
   ```

### 验证配置

启动应用后，查看日志确认配置是否正确加载：

```bash
# 查看应用日志
tail -f backend/logs/app.log

# 或查看 Systemd 日志
sudo journalctl -u iptv-admin -f
```

---

## 数据库配置说明

### SQLite vs MySQL

| 特性 | SQLite | MySQL |
|------|--------|-------|
| **适用场景** | 开发测试、小规模部署 | 生产环境、大规模部署 |
| **并发性能** | 低 | 高 |
| **数据量** | < 10GB | > 10GB |
| **备份恢复** | 简单（复制文件） | 需要 mysqldump |
| **运维成本** | 低 | 中等 |

### 切换数据库

从 SQLite 切换到 MySQL：

1. 创建 MySQL 数据库和用户
2. 修改 `.env` 配置：
   ```bash
   DATABASE_TYPE=mysql
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=iptv_user
   MYSQL_PASSWORD=your_password
   MYSQL_DB=iptv_production
   ```
3. 重启应用（自动创建表结构）
4. 如需迁移数据，使用导入导出功能

---

## 性能调优建议

### 健康检测优化

- **小规模（< 50 频道）**: 间隔 1800 秒，超时 10 秒，重试 1 次
- **中等规模（50-200 频道）**: 间隔 3600 秒，超时 15 秒，重试 2 次
- **大规模（> 200 频道）**: 间隔 7200 秒，超时 20 秒，重试 1 次

### 观看历史优化

- **实时性要求高**: 保存间隔 30-60 秒
- **平衡模式**: 保存间隔 60-120 秒
- **性能优先**: 保存间隔 300 秒

### 代理缓冲优化

- **低延迟网络**: 4096-8192 字节
- **普通网络**: 8192-16384 字节
- **高带宽网络**: 16384-32768 字节

---

## 安全建议

1. **生产环境必须修改的配置：**
   - `SESSION_SECRET_KEY` - 使用随机密钥
   - `SERVER_DEBUG` - 必须设置为 `false`
   - 数据库密码 - 使用强密码

2. **数据库安全：**
   - MySQL 不要使用 root 用户
   - 创建专用数据库用户并限制权限
   - 定期备份数据库

3. **网络安全：**
   - 使用 Nginx 反向代理
   - 配置 HTTPS（SSL/TLS）
   - 限制管理后台访问 IP

---

## 故障排查

### 配置未生效

1. 检查 `.env` 文件是否存在
2. 检查环境变量语法是否正确（无空格、引号）
3. 确认已重启服务
4. 查看日志确认配置加载情况

### 数据库连接失败

1. 检查 `DATABASE_TYPE` 配置
2. SQLite: 检查文件路径和权限
3. MySQL: 检查连接信息（主机、端口、用户名、密码）
4. MySQL: 确认数据库已创建且用户有权限

### 健康检测不工作

1. 检查 `HEALTH_CHECK_ENABLED=true`
2. 查看日志是否有错误信息
3. 检查频道 URL 是否可访问
4. 调整超时和重试次数

---

## 总结

IPTV Proxy Admin 提供了灵活的配置选项，可以根据不同的部署环境和需求进行调整。建议：

- 开发环境使用 SQLite + 默认配置
- 生产环境使用 MySQL + 优化配置
- 定期检查和备份配置文件
- 根据实际负载调整性能参数
