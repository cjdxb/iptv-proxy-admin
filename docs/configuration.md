# IPTV Proxy Admin 配置文档

本文档说明当前版本的配置项、优先级与生效方式。

## 配置来源与优先级

系统配置有两层：

1. 环境变量（`backend/.env`）
2. 数据库设置（`settings` 表，通过 Web 界面写入）

优先级：

```text
数据库运行时配置 > .env 环境变量 > 代码默认值
```

## 生效机制

- 通过 Web 界面保存后，调用 `POST /api/settings/reload` 可立即刷新 Web 进程内运行时配置。
- 独立 `health_worker.py` 每轮执行前会主动从数据库刷新健康检测运行参数（超时/重试/线程）。
- `history_worker_interval_seconds` 由独立 `history_worker.py` 调度器读取，修改后需重启 history-worker 才会使用新间隔。
- 纯环境变量项（如数据库连接、JWT 密钥）需重启对应进程。

## 可在 Web 界面配置的运行时项

对应 Settings 键名如下：

| 键名 | 说明 | 默认值 | 生效方式 |
|---|---|---|---|
| `udpxy_enabled` | 是否启用 UDPxy 转发 | `false` | 立即生效 |
| `udpxy_url` | UDPxy 地址 | `http://localhost:3680` | 立即生效 |
| `proxy_buffer_size` | 流代理缓冲区（字节） | `8192` | 立即生效 |
| `health_check_timeout` | 健康检测超时（秒） | `10` | 立即生效 |
| `health_check_max_retries` | 健康检测重试次数 | `1` | 立即生效 |
| `health_check_threads` | 健康检测线程数 | `3` | 立即生效 |
| `heartbeat_interval_seconds` | 播放连接心跳上报间隔（秒） | `10` | 立即生效 |
| `active_heartbeat_timeout_seconds` | 活跃连接心跳超时阈值（秒） | `45` | 立即生效 |
| `history_worker_interval_seconds` | history-worker 调度间隔（秒） | `15` | 重启 history-worker 后生效 |
| `site_name` | 站点显示名称 | `IPTV Proxy Admin` | 立即生效（前端重新拉取） |
| `epg_url` | 订阅 M3U 的 EPG 地址 | 空 | 立即生效 |
| `watch_history_retention_days` | 历史保留天数（用于策略配置） | `30` | 立即生效（不会自动删除历史） |

## 环境变量配置（`backend/.env`）

下面是后端支持的环境变量。

### 服务器

#### `SERVER_HOST`
- 默认值：`0.0.0.0`
- 说明：服务监听地址。

#### `SERVER_PORT`
- 默认值：`5000`
- 说明：服务监听端口。

#### `SERVER_DEBUG`
- 默认值：`false`（`.env.example` 中为 `true`，仅用于开发）
- 说明：Flask 调试模式，生产必须为 `false`。

### 数据库

#### `DATABASE_TYPE`
- 默认值：`sqlite`
- 可选值：`sqlite` / `mysql`

#### `DATABASE_PATH`
- 默认值：`data/iptv.db`（代码默认）
- 模板值：`data/db.db`（`.env.example`）
- 说明：当 `DATABASE_TYPE=sqlite` 时生效，相对路径基于 `backend/`。

#### `MYSQL_HOST`
- 默认值：`localhost`

#### `MYSQL_PORT`
- 默认值：`3306`

#### `MYSQL_USER`
- 默认值：`root`

#### `MYSQL_PASSWORD`
- 默认值：`root`

#### `MYSQL_DB`
- 默认值：`iptv`

### JWT

#### `JWT_SECRET_KEY`
- 默认值：`default-jwt-secret-key`
- 说明：JWT 签名密钥，生产环境必须更换为强随机值。

#### `JWT_ALGORITHM`
- 默认值：`HS256`

#### `JWT_ACCESS_EXPIRES_HOURS`
- 默认值：`24`

#### `JWT_REFRESH_EXPIRES_DAYS`
- 默认值：`7`

### 健康检测调度

#### `HEALTH_CHECK_ENABLED`
- 默认值：`true`
- 说明：是否启用独立 `health_worker.py` 的定时健康检测任务。

#### `HEALTH_CHECK_INTERVAL`
- 默认值：`1800`
- 说明：`health_worker.py` 的定时检测间隔（秒）。

### UDPxy（环境变量回退值）

#### `UDPXY_ENABLED`
- 默认值：`false`

#### `UDPXY_URL`
- 默认值：`http://localhost:3680`

### 代理配置（环境变量回退值）

#### `PROXY_BUFFER_SIZE`
- 默认值：`8192`

### 健康检测运行参数（环境变量回退值）

#### `HEALTH_CHECK_TIMEOUT`
- 默认值：`10`

#### `HEALTH_CHECK_MAX_RETRIES`
- 默认值：`1`

#### `HEALTH_CHECK_THREADS`
- 默认值：`3`

### 观看会话与 worker

#### `HEARTBEAT_INTERVAL_SECONDS`
- 默认值：`10`
- 说明：流代理上报心跳的周期（秒）。

#### `ACTIVE_HEARTBEAT_TIMEOUT_SECONDS`
- 默认值：`45`
- 说明：超过该阈值未收到心跳将视为僵尸连接并回收。

#### `HISTORY_WORKER_INTERVAL_SECONDS`
- 默认值：`15`
- 说明：独立 `history_worker.py` 的调度周期。

### Gunicorn

#### `GUNICORN_LOG_LEVEL`
- 默认值：`info`

## 配置示例

### 开发环境

```bash
SERVER_HOST=0.0.0.0
SERVER_PORT=5000
SERVER_DEBUG=true

DATABASE_TYPE=sqlite
DATABASE_PATH=data/db.db

JWT_SECRET_KEY=dev-jwt-secret-key
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

### 生产环境（MySQL）

```bash
SERVER_HOST=127.0.0.1
SERVER_PORT=5000
SERVER_DEBUG=false

DATABASE_TYPE=mysql
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=iptv_user
MYSQL_PASSWORD=replace_with_strong_password
MYSQL_DB=iptv_production

JWT_SECRET_KEY=replace_with_random_32_bytes_or_more
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

## 修改配置后的操作建议

1. 修改了数据库/JWT/服务监听等环境变量：重启 Web、history-worker、health-worker。
2. 修改了 Web 设置中的运行时项：保存后执行“保存并应用”（前端已调用 `/api/settings/reload`）。
3. 修改了 `history_worker_interval_seconds`：额外重启 history-worker 进程。
4. 修改了 `HEALTH_CHECK_INTERVAL` 或 `HEALTH_CHECK_ENABLED`：额外重启 health-worker 进程。

## 故障排查

### 配置看起来没生效

- 检查是否保存到了 `settings` 表（Web 设置页刷新确认）。
- 检查是否已调用 `POST /api/settings/reload`。
- 检查是否重启了 history-worker（仅针对 worker 调度间隔）。

### 健康检测状态不更新

- 检查 `health_worker.py` 是否运行。
- 检查 `HEALTH_CHECK_ENABLED` 是否为 `true`。

### 数据库连接失败

- SQLite：检查 `backend/data/` 目录权限。
- MySQL：检查主机/端口/用户名/密码/库名是否可连接。

### 观看历史回收异常

- 检查 `history_worker.py` 是否运行。
- 检查 `heartbeat_interval_seconds` 是否小于 `active_heartbeat_timeout_seconds`。
