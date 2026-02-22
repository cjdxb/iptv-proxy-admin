# IPTV Proxy Admin 数据库文档

## 数据库概述

IPTV Proxy Admin 使用 SQLAlchemy ORM 管理数据库，支持 SQLite 和 MySQL 两种数据库。

- 默认数据库：SQLite（`backend/data/db.db`，若未配置则回退到 `backend/data/iptv.db`）
- 生产推荐：MySQL 5.7+ / MariaDB 10.3+
- 字符集：`utf8mb4`（MySQL）
- 当前核心表：7 张
- 关系类型：全部使用应用层逻辑关联（不启用数据库外键约束）

---

## 数据库架构图

```text
┌───────────────┐        ┌──────────────────┐
│     users     │ 1    n │  refresh_tokens  │
│   (用户表)    ├────────┤   (刷新令牌表)    │
└───────┬───────┘        └──────────────────┘
        │
        │ 1
        │
        │ n
┌───────▼──────────┐      ┌──────────────────┐
│   watch_history  │ 1  1 │ active_connections│
│   (观看历史表)    ├──────┤  (活跃连接表)     │
└───────▲──────────┘      └──────────────────┘
        │
        │ n
        │
        │ 1
┌───────┴───────┐        ┌──────────────────┐
│   channels    │ n    1 │  channel_groups  │
│   (频道表)     ├────────┤    (分组表)      │
└───────────────┘        └──────────────────┘

┌───────────────┐
│   settings    │
│   (系统设置表) │
└───────────────┘
```

---

## 表结构详细说明

### 1. `users`（用户表）

存储后台登录用户、订阅 Token 以及是否必须改密状态。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `id` | Integer | 否 | 自增 | 主键 | 用户 ID |
| `username` | String(80) | 否 | - | 唯一索引 | 登录用户名 |
| `password_hash` | String(256) | 否 | - | - | 密码哈希（Werkzeug） |
| `must_change_password` | Boolean | 否 | `false` | - | 是否必须先修改密码 |
| `token` | String(64) | 是 | `NULL` | 唯一索引 | 订阅/播放 Token |
| `created_at` | DateTime | 否 | 应用写入 | - | 创建时间（UTC） |

关键说明：
- 默认管理员 `admin` 初始密码 `admin123`，并会标记 `must_change_password=true`。
- 旧版本数据库启动时会自动补齐 `must_change_password` 列。

---

### 2. `refresh_tokens`（刷新令牌表）

存储 JWT refresh token 的哈希值（不存明文），支持轮换与吊销。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `id` | Integer | 否 | 自增 | 主键 | 记录 ID |
| `user_id` | Integer | 否 | - | 普通索引 | 所属用户 ID（逻辑关联 `users.id`） |
| `token_hash` | String(64) | 否 | - | 唯一索引 | refresh token 的 SHA-256 哈希 |
| `expires_at` | DateTime | 否 | - | 普通索引 | 过期时间（UTC） |
| `revoked_at` | DateTime | 是 | `NULL` | 普通索引 | 吊销时间（UTC） |
| `created_at` | DateTime | 否 | 应用写入 | - | 创建时间（UTC） |

关键说明：
- 每次刷新会轮换 refresh token，旧令牌立即标记为 revoked。
- 登出时可按 refresh token 定位并吊销对应记录。

---

### 3. `channel_groups`（频道分组表）

频道分组定义。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `id` | Integer | 否 | 自增 | 主键 | 分组 ID |
| `name` | String(100) | 否 | - | - | 分组名称 |
| `sort_order` | Integer | 否 | `0` | - | 排序值 |
| `created_at` | DateTime | 否 | 应用写入 | - | 创建时间（UTC） |

---

### 4. `channels`（频道表）

IPTV 频道主数据。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `id` | Integer | 否 | 自增 | 主键 | 频道 ID |
| `name` | String(200) | 否 | - | - | 频道名称 |
| `url` | String(500) | 否 | - | - | 播放源 URL |
| `logo` | String(500) | 是 | `NULL` | - | Logo URL |
| `group_id` | Integer | 是 | `NULL` | 普通索引 | 分组 ID（逻辑关联 `channel_groups.id`） |
| `sort_order` | Integer | 否 | `0` | - | 排序值 |
| `is_active` | Boolean | 否 | `true` | - | 是否启用 |
| `protocol` | String(20) | 否 | `http` | - | 协议类型：`http/https/rtp/udp` |
| `tvg_id` | String(100) | 是 | `NULL` | - | EPG 标识 |
| `last_check` | DateTime | 是 | `NULL` | - | 最后健康检测时间（UTC） |
| `is_healthy` | Boolean | 否 | `true` | - | 健康状态 |
| `created_at` | DateTime | 否 | 应用写入 | - | 创建时间（UTC） |
| `updated_at` | DateTime | 否 | 应用写入 | - | 更新时间（UTC） |

---

### 5. `watch_history`（观看历史表）

记录观看会话的起止时间与时长。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `id` | Integer | 否 | 自增 | 主键 | 记录 ID |
| `user_id` | Integer | 否 | - | 普通索引 | 用户 ID（逻辑关联 `users.id`） |
| `channel_id` | Integer | 否 | - | 普通索引 | 频道 ID（逻辑关联 `channels.id`） |
| `start_time` | DateTime | 否 | - | - | 开始时间（UTC） |
| `end_time` | DateTime | 是 | `NULL` | - | 结束时间（UTC） |
| `duration` | Integer | 否 | `0` | - | 时长（秒） |
| `watch_date` | Date | 否 | - | 普通索引 | 观看日期（用于聚合） |

关键说明：
- `duration < 5` 秒的记录会在结束阶段被自动忽略（删除）。
- 活跃会话不再通过 `end_time IS NULL` 判断，统一看 `active_connections`。

---

### 6. `active_connections`（活跃连接表）

保存当前正在播放的会话，供跨进程共享状态与心跳回收。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `connection_id` | String(64) | 否 | - | 主键 | 连接 ID（`user_channel_uuid`） |
| `watch_history_id` | Integer | 否 | - | 唯一约束 | 对应 `watch_history.id` |
| `user_id` | Integer | 否 | - | 普通索引 | 用户 ID |
| `channel_id` | Integer | 否 | - | 普通索引 | 频道 ID |
| `start_time` | DateTime | 否 | - | - | 会话开始时间（UTC） |
| `last_heartbeat` | DateTime | 否 | - | 普通索引 | 最近心跳时间（UTC） |
| `created_at` | DateTime | 否 | 应用写入 | - | 创建时间（UTC） |

索引与约束：
- `PRIMARY KEY (connection_id)`
- `UNIQUE (watch_history_id)`（`uk_active_watch_history_id`）
- `INDEX idx_active_user_id (user_id)`
- `INDEX idx_active_channel_id (channel_id)`
- `INDEX idx_active_last_heartbeat (last_heartbeat)`
- `INDEX idx_active_user_channel (user_id, channel_id)`

---

### 7. `settings`（系统设置表）

键值型配置表。

| 字段名 | 类型 | 允许空 | 默认值 | 索引 | 说明 |
|---|---|---|---|---|---|
| `id` | Integer | 否 | 自增 | 主键 | 设置 ID |
| `key` | String(100) | 否 | - | 唯一索引 | 配置键 |
| `value` | Text | 是 | `NULL` | - | 配置值 |

常见配置键（部分）：
- `epg_url`
- `server_name`
- `site_name`
- `watch_history_retention_days`
- `proxy_buffer_size`
- `health_check_timeout`
- `health_check_max_retries`
- `health_check_threads`
- `udpxy_enabled`
- `udpxy_url`
- `heartbeat_interval_seconds`
- `active_heartbeat_timeout_seconds`
- `history_worker_interval_seconds`

---

## 数据写入流程（观看相关）

### 播放开始
1. 写入一条 `watch_history`（`start_time`，`duration=0`）。
2. 写入一条 `active_connections`（包含 `last_heartbeat`）。

### 播放中
1. 流代理按心跳间隔更新 `active_connections.last_heartbeat`。
2. `history-worker` 定时刷新 `watch_history.duration`（不写 `end_time`）。

### 播放结束/异常回收
1. 会话关闭时补齐 `watch_history.end_time` 和最终 `duration`。
2. 若时长 < 5 秒，删除该 `watch_history`。
3. 删除对应 `active_connections`。

---

## 初始化与迁移

### 自动初始化
应用启动时会执行：
- `db.create_all()`
- （MySQL）自动移除历史版本遗留的外键约束
- 兼容性补列：`users.must_change_password`（旧库缺失时自动 `ALTER TABLE`）
- 创建默认管理员（若不存在）

### 版本升级注意
- 从旧版本升级后，`users` 表会新增 `must_change_password`。
- 启用 JWT 刷新后会新增 `refresh_tokens` 表。
- 活跃连接能力依赖 `active_connections` 表。

---

## 常用 SQL

### 查看必须改密用户
```sql
SELECT id, username, must_change_password
FROM users
WHERE must_change_password = 1;
```

### 查看当前活跃连接（推荐）
```sql
SELECT
  ac.connection_id,
  u.username,
  c.name AS channel_name,
  ac.start_time,
  ac.last_heartbeat
FROM active_connections ac
LEFT JOIN users u ON ac.user_id = u.id
LEFT JOIN channels c ON ac.channel_id = c.id
ORDER BY ac.start_time DESC;
```

### 查看近 7 天频道观看排行
```sql
SELECT
  c.name AS channel_name,
  COUNT(w.id) AS watch_count,
  SUM(w.duration) AS total_duration
FROM watch_history w
JOIN channels c ON w.channel_id = c.id
WHERE w.watch_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY w.channel_id, c.name
ORDER BY total_duration DESC
LIMIT 10;
```

### 清理过期且已吊销的 refresh token
```sql
DELETE FROM refresh_tokens
WHERE revoked_at IS NOT NULL
   OR expires_at < NOW();
```

---

## 备份与恢复

### SQLite 备份
```bash
sqlite3 backend/data/db.db ".backup 'backup_$(date +%Y%m%d).db'"
```

### MySQL 备份
```bash
mysqldump -u iptv_user -p iptv_production > backup_$(date +%Y%m%d).sql
```

---

## 总结

当前数据库核心对象为 7 张表：

1. `users`（用户）
2. `refresh_tokens`（JWT 刷新令牌）
3. `channel_groups`（频道分组）
4. `channels`（频道）
5. `watch_history`（历史）
6. `active_connections`（活跃连接）
7. `settings`（系统配置）

如有新增模型字段或新表，需同步更新本文件，避免文档与实际结构偏差。
