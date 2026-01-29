# IPTV Proxy Admin 数据库文档

## 数据库概述

IPTV Proxy Admin 使用 SQLAlchemy ORM 管理数据库，支持 SQLite 和 MySQL 两种数据库。

- **默认数据库：** SQLite (`backend/data/iptv.db`)
- **生产推荐：** MySQL 5.7+ / MariaDB 10.3+
- **字符集：** utf8mb4
- **表数量：** 5 张表
- **关系类型：** 一对多、外键关联

---

## 数据库架构图

```
┌─────────────┐         ┌──────────────┐
│   users     │         │channel_groups│
│  (用户表)   │         │ (分组表)     │
└──────┬──────┘         └───────┬──────┘
       │                        │
       │ 1                    1 │
       │                        │
       │ n                    n │
       │                 ┌──────┴──────┐
       │                 │  channels   │
       │                 │  (频道表)   │
       │                 └──────┬──────┘
       │                        │
       │                      1 │
       │                        │
       │                      n │
       │                ┌───────┴────────┐
       └────────────────┤ watch_history  │
                        │ (观看历史表)   │
                        └────────────────┘

                        ┌──────────────┐
                        │   settings   │
                        │ (系统设置表) │
                        └──────────────┘
```

---

## 表结构详细说明

### 1. users（用户表）

用户账户信息表，存储管理员和用户的登录凭证及订阅 Token。

#### 表结构

| 字段名 | 类型 | 长度 | 允许空 | 默认值 | 索引 | 说明 |
|--------|------|------|--------|--------|------|------|
| `id` | Integer | - | 否 | 自增 | 主键 | 用户ID |
| `username` | String | 80 | 否 | - | 唯一索引 | 用户名 |
| `password_hash` | String | 256 | 否 | - | - | 密码哈希（bcrypt） |
| `token` | String | 64 | 是 | NULL | 唯一索引 | 订阅Token（64字节） |
| `created_at` | DateTime | - | 否 | CURRENT_TIMESTAMP | - | 创建时间 |

#### 索引

- **主键索引：** `id`
- **唯一索引：** `username`
- **唯一索引：** `token`

#### 约束

- `username` 必须唯一
- `token` 必须唯一（允许 NULL）
- `password_hash` 使用 Werkzeug 的 `generate_password_hash()` 生成

#### 默认数据

```sql
-- 默认管理员账户
INSERT INTO users (username, password_hash, token)
VALUES ('admin', '<bcrypt_hash>', '<random_token>');
-- 默认密码: admin123（首次登录后必须修改）
```

#### 关联关系

- **一对多：** 一个用户可以有多条观看历史记录 (`watch_history`)

#### 示例查询

```sql
-- 查询所有用户
SELECT id, username, created_at FROM users;

-- 通过 Token 查找用户
SELECT * FROM users WHERE token = 'your_token_here';

-- 查询用户的观看历史
SELECT u.username, COUNT(w.id) as watch_count
FROM users u
LEFT JOIN watch_history w ON u.id = w.user_id
GROUP BY u.id;
```

---

### 2. channel_groups（频道分组表）

频道分组表，用于组织和管理频道分类。

#### 表结构

| 字段名 | 类型 | 长度 | 允许空 | 默认值 | 索引 | 说明 |
|--------|------|------|--------|--------|------|------|
| `id` | Integer | - | 否 | 自增 | 主键 | 分组ID |
| `name` | String | 100 | 否 | - | - | 分组名称 |
| `sort_order` | Integer | - | 否 | 0 | - | 排序顺序 |
| `created_at` | DateTime | - | 否 | CURRENT_TIMESTAMP | - | 创建时间 |

#### 索引

- **主键索引：** `id`

#### 约束

- `name` 不能为空
- `sort_order` 用于前端显示排序，数值越小越靠前

#### 关联关系

- **一对多：** 一个分组可以包含多个频道 (`channels`)

#### 示例查询

```sql
-- 查询所有分组及频道数量
SELECT
    g.id,
    g.name,
    g.sort_order,
    COUNT(c.id) as channel_count
FROM channel_groups g
LEFT JOIN channels c ON g.id = c.group_id
GROUP BY g.id
ORDER BY g.sort_order;

-- 查询空分组（没有频道的分组）
SELECT * FROM channel_groups g
WHERE NOT EXISTS (
    SELECT 1 FROM channels c WHERE c.group_id = g.id
);

-- 删除空分组
DELETE FROM channel_groups
WHERE id NOT IN (SELECT DISTINCT group_id FROM channels WHERE group_id IS NOT NULL);
```

---

### 3. channels（频道表）

频道信息表，存储 IPTV 直播源的详细信息。

#### 表结构

| 字段名 | 类型 | 长度 | 允许空 | 默认值 | 索引 | 说明 |
|--------|------|------|--------|--------|------|------|
| `id` | Integer | - | 否 | 自增 | 主键 | 频道ID |
| `name` | String | 200 | 否 | - | - | 频道名称 |
| `url` | String | 500 | 否 | - | - | 直播源URL |
| `logo` | String | 500 | 是 | NULL | - | 频道Logo URL |
| `group_id` | Integer | - | 是 | NULL | 外键 | 所属分组ID |
| `sort_order` | Integer | - | 否 | 0 | - | 排序顺序 |
| `is_active` | Boolean | - | 否 | TRUE | - | 是否启用 |
| `protocol` | String | 20 | 否 | 'http' | - | 协议类型 |
| `tvg_id` | String | 100 | 是 | NULL | - | EPG节目单ID |
| `last_check` | DateTime | - | 是 | NULL | - | 最后检测时间 |
| `is_healthy` | Boolean | - | 否 | TRUE | - | 健康状态 |
| `created_at` | DateTime | - | 否 | CURRENT_TIMESTAMP | - | 创建时间 |
| `updated_at` | DateTime | - | 否 | CURRENT_TIMESTAMP | - | 更新时间 |

#### 索引

- **主键索引：** `id`
- **外键索引：** `group_id` → `channel_groups.id`

#### 约束

- `name` 不能为空
- `url` 不能为空
- `protocol` 枚举值：`http`, `https`, `rtp`, `udp`
- `group_id` 外键关联 `channel_groups.id`（级联更新，不级联删除）

#### 字段说明

**protocol（协议类型）：**
- `http` - HTTP 直播源
- `https` - HTTPS 直播源
- `rtp` - RTP 组播源（如 `rtp://239.0.0.1:5000`）
- `udp` - UDP 组播源（如 `udp://@239.0.0.1:5000`）

**is_active（启用状态）：**
- `TRUE` - 启用（出现在订阅列表中）
- `FALSE` - 禁用（不出现在订阅列表中）

**is_healthy（健康状态）：**
- `TRUE` - 频道可用
- `FALSE` - 频道不可用（最近一次检测失败）

#### 关联关系

- **多对一：** 多个频道属于一个分组 (`channel_groups`)
- **一对多：** 一个频道可以有多条观看历史记录 (`watch_history`)

#### 示例查询

```sql
-- 查询所有启用的频道
SELECT * FROM channels WHERE is_active = 1 ORDER BY sort_order;

-- 查询不健康的频道
SELECT id, name, url, last_check
FROM channels
WHERE is_healthy = 0;

-- 按分组统计频道数量
SELECT
    g.name as group_name,
    COUNT(c.id) as channel_count,
    SUM(CASE WHEN c.is_active = 1 THEN 1 ELSE 0 END) as active_count,
    SUM(CASE WHEN c.is_healthy = 1 THEN 1 ELSE 0 END) as healthy_count
FROM channel_groups g
LEFT JOIN channels c ON g.id = c.group_id
GROUP BY g.id;

-- 查询组播源
SELECT * FROM channels WHERE protocol IN ('rtp', 'udp');

-- 按协议统计
SELECT protocol, COUNT(*) as count FROM channels GROUP BY protocol;

-- 查询最近更新的频道
SELECT * FROM channels ORDER BY updated_at DESC LIMIT 10;
```

---

### 4. watch_history（观看历史表）

用户观看历史记录表，用于统计观看时长和频道热度。

#### 表结构

| 字段名 | 类型 | 长度 | 允许空 | 默认值 | 索引 | 说明 |
|--------|------|------|--------|--------|------|------|
| `id` | Integer | - | 否 | 自增 | 主键 | 记录ID |
| `user_id` | Integer | - | 否 | - | 外键、索引 | 用户ID |
| `channel_id` | Integer | - | 否 | - | 外键 | 频道ID |
| `start_time` | DateTime | - | 否 | - | - | 开始观看时间 |
| `end_time` | DateTime | - | 是 | NULL | - | 结束观看时间 |
| `duration` | Integer | - | 否 | 0 | - | 观看时长（秒） |
| `watch_date` | Date | - | 否 | - | 索引 | 观看日期 |

#### 索引

- **主键索引：** `id`
- **外键索引：** `user_id` → `users.id`
- **外键索引：** `channel_id` → `channels.id`
- **普通索引：** `watch_date`

#### 约束

- `user_id` 外键关联 `users.id`
- `channel_id` 外键关联 `channels.id`
- `duration` 单位为秒，通过 `end_time - start_time` 计算

#### 数据更新机制

**自动保存机制（v1.1.0+）：**
1. 用户开始观看时创建记录（`start_time`）
2. 每 60 秒自动更新 `end_time` 和 `duration`
3. 用户断开连接时最后一次更新

**优点：**
- 实时统计观看数据
- 防止服务器重启丢失数据
- 准确记录观看时长

#### 关联关系

- **多对一：** 多条观看历史属于一个用户 (`users`)
- **多对一：** 多条观看历史对应一个频道 (`channels`)

#### 示例查询

```sql
-- 查询用户总观看时长（按天统计）
SELECT
    watch_date,
    SUM(duration) as total_duration_seconds,
    SUM(duration) / 3600.0 as total_duration_hours
FROM watch_history
WHERE user_id = 1
GROUP BY watch_date
ORDER BY watch_date DESC;

-- 查询频道热度排行（最近7天）
SELECT
    c.name as channel_name,
    COUNT(w.id) as watch_count,
    SUM(w.duration) as total_duration,
    SUM(w.duration) / 3600.0 as total_hours
FROM watch_history w
JOIN channels c ON w.channel_id = c.id
WHERE w.watch_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
GROUP BY w.channel_id
ORDER BY total_duration DESC
LIMIT 10;

-- 查询正在观看的用户（end_time 为空）
SELECT
    u.username,
    c.name as channel_name,
    w.start_time,
    TIMESTAMPDIFF(SECOND, w.start_time, NOW()) as watching_seconds
FROM watch_history w
JOIN users u ON w.user_id = u.id
JOIN channels c ON w.channel_id = c.id
WHERE w.end_time IS NULL;

-- 按日期统计观看次数和时长
SELECT
    watch_date,
    COUNT(*) as watch_count,
    SUM(duration) / 60 as total_minutes
FROM watch_history
GROUP BY watch_date
ORDER BY watch_date DESC;

-- 查询观看时长超过1小时的记录
SELECT
    u.username,
    c.name,
    start_time,
    duration / 60 as duration_minutes
FROM watch_history w
JOIN users u ON w.user_id = u.id
JOIN channels c ON w.channel_id = c.id
WHERE duration > 3600
ORDER BY duration DESC;
```

---

### 5. settings（系统设置表）

键值对形式的系统配置表。

#### 表结构

| 字段名 | 类型 | 长度 | 允许空 | 默认值 | 索引 | 说明 |
|--------|------|------|--------|--------|------|------|
| `id` | Integer | - | 否 | 自增 | 主键 | 设置ID |
| `key` | String | 100 | 否 | - | 唯一索引 | 设置键 |
| `value` | Text | - | 是 | NULL | - | 设置值 |

#### 索引

- **主键索引：** `id`
- **唯一索引：** `key`

#### 约束

- `key` 必须唯一
- `value` 存储为文本，支持长内容

#### 预定义配置键

| 配置键 | 说明 | 示例值 |
|--------|------|--------|
| `epg_url` | EPG 节目单 XML 地址 | `http://epg.example.com/guide.xml` |
| `server_name` | 服务器名称 | `IPTV Proxy Server` |
| `site_name` | 网站名称 | `我的IPTV` |
| `health_check_interval` | 健康检测间隔（秒） | `1800` |

#### 示例查询

```sql
-- 查询所有设置
SELECT * FROM settings;

-- 查询指定配置
SELECT value FROM settings WHERE key = 'epg_url';

-- 更新配置
INSERT INTO settings (key, value) VALUES ('site_name', '我的IPTV')
ON DUPLICATE KEY UPDATE value = '我的IPTV';

-- 删除配置
DELETE FROM settings WHERE key = 'old_config';
```

---

## 数据库初始化

### SQLite 初始化

```bash
cd backend
source venv/bin/activate

python << EOF
from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all()

    # 创建默认管理员
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin')
        admin.set_password('admin123')
        admin.generate_token()
        db.session.add(admin)
        db.session.commit()
        print('Database initialized successfully')
EOF
```

### MySQL 初始化

```sql
-- 1. 创建数据库
CREATE DATABASE iptv_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. 创建用户
CREATE USER 'iptv_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON iptv_production.* TO 'iptv_user'@'localhost';
FLUSH PRIVILEGES;
```

然后执行 Python 初始化脚本（同上）。

---

## 数据库维护

### 备份

**SQLite 备份：**

```bash
# 在线备份
sqlite3 backend/data/iptv.db ".backup 'backup_$(date +%Y%m%d).db'"

# 压缩备份
sqlite3 backend/data/iptv.db ".backup '/tmp/backup.db'" && gzip /tmp/backup.db
```

**MySQL 备份：**

```bash
# 导出数据库
mysqldump -u iptv_user -p iptv_production > backup_$(date +%Y%m%d).sql

# 压缩备份
mysqldump -u iptv_user -p iptv_production | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 恢复

**SQLite 恢复：**

```bash
# 恢复备份
cp backup_20260129.db backend/data/iptv.db
```

**MySQL 恢复：**

```bash
# 恢复数据库
mysql -u iptv_user -p iptv_production < backup_20260129.sql
```

### 优化

**SQLite 优化：**

```sql
-- 清理碎片
VACUUM;

-- 分析查询计划
ANALYZE;
```

**MySQL 优化：**

```sql
-- 优化表
OPTIMIZE TABLE channels, watch_history, users;

-- 分析表
ANALYZE TABLE channels, watch_history;

-- 查看表状态
SHOW TABLE STATUS WHERE Name IN ('channels', 'watch_history');
```

### 清理数据

```sql
-- 删除 30 天前的观看历史
DELETE FROM watch_history WHERE watch_date < DATE_SUB(CURDATE(), INTERVAL 30 DAY);

-- 删除未使用的分组
DELETE FROM channel_groups
WHERE id NOT IN (SELECT DISTINCT group_id FROM channels WHERE group_id IS NOT NULL);

-- 清理孤立的观看记录（频道已删除）
DELETE FROM watch_history
WHERE channel_id NOT IN (SELECT id FROM channels);
```

---

## 常用 SQL 查询

### 统计查询

```sql
-- 系统概览统计
SELECT
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM channels) as total_channels,
    (SELECT COUNT(*) FROM channels WHERE is_active = 1) as active_channels,
    (SELECT COUNT(*) FROM channels WHERE is_healthy = 0) as unhealthy_channels,
    (SELECT COUNT(*) FROM channel_groups) as total_groups,
    (SELECT COUNT(*) FROM watch_history) as total_watch_records;

-- 今日观看统计
SELECT
    COUNT(DISTINCT user_id) as active_users,
    COUNT(*) as watch_count,
    SUM(duration) / 3600 as total_hours
FROM watch_history
WHERE watch_date = CURDATE();

-- 频道协议分布
SELECT protocol, COUNT(*) as count
FROM channels
GROUP BY protocol;
```

### 性能查询

```sql
-- 查询慢查询（需要开启慢查询日志）
-- 查看最常访问的频道
SELECT
    c.id,
    c.name,
    COUNT(w.id) as access_count,
    MAX(w.start_time) as last_access
FROM channels c
LEFT JOIN watch_history w ON c.id = w.channel_id
GROUP BY c.id
ORDER BY access_count DESC
LIMIT 20;

-- 查询从未被观看的频道
SELECT c.* FROM channels c
WHERE NOT EXISTS (
    SELECT 1 FROM watch_history w WHERE w.channel_id = c.id
);
```

---

## 故障排查

### 数据库连接问题

```bash
# 检查 SQLite 文件权限
ls -la backend/data/iptv.db

# 检查 MySQL 连接
mysql -u iptv_user -p iptv_production -e "SELECT 1"

# 查看错误日志
tail -f /var/log/mysql/error.log  # MySQL
```

### 数据一致性检查

```sql
-- 检查孤立的频道（分组已删除）
SELECT c.* FROM channels c
LEFT JOIN channel_groups g ON c.group_id = g.id
WHERE c.group_id IS NOT NULL AND g.id IS NULL;

-- 检查孤立的观看记录
SELECT w.* FROM watch_history w
LEFT JOIN channels c ON w.channel_id = c.id
WHERE c.id IS NULL;
```

---

## 总结

IPTV Proxy Admin 的数据库设计简洁高效，包含 5 张核心表：

1. **users** - 用户管理
2. **channel_groups** - 频道分组
3. **channels** - 频道信息
4. **watch_history** - 观看历史
5. **settings** - 系统配置

所有表之间通过外键关联，保证数据一致性。支持 SQLite 和 MySQL 两种数据库。
