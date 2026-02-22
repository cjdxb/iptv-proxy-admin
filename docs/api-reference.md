# IPTV Proxy Admin API 文档

本文档基于当前后端实现（`backend/app/api/*.py`）整理。

## 基础信息

- 基础路径：`/api`
- 数据格式：JSON（订阅/流媒体接口除外）
- 管理端认证：JWT Bearer Token
- 播放/订阅认证：URL Query 中的 `token`

管理端请求头示例：

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

## 认证接口 `/auth`

### `POST /api/auth/login`

登录并返回 Access/Refresh Token。

请求体：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

成功响应：

```json
{
  "message": "登录成功",
  "user": {
    "id": 1,
    "username": "admin",
    "must_change_password": true,
    "token": "<subscription_token>",
    "created_at": "2026-02-01T10:00:00Z"
  },
  "token_type": "Bearer",
  "access_token": "<jwt_access>",
  "refresh_token": "<refresh_token>",
  "expires_in": 86400,
  "refresh_expires_in": 604800
}
```

### `POST /api/auth/logout`

可选吊销 refresh token。

请求体（可选）：

```json
{
  "refresh_token": "<refresh_token>"
}
```

响应：

```json
{
  "message": "登出成功"
}
```

### `POST /api/auth/refresh`

使用 refresh token 换新令牌对（旧 refresh token 会被吊销）。

请求体：

```json
{
  "refresh_token": "<refresh_token>"
}
```

响应结构与 `login` 类似。

### `GET /api/auth/me`

获取当前登录用户信息。

响应：用户对象（`id/username/must_change_password/token/created_at`）。

### `POST /api/auth/reset-token`

重置订阅 token。

响应：

```json
{
  "message": "Token 已重置",
  "token": "<new_subscription_token>"
}
```

### `POST /api/auth/change-password`

修改密码，成功后返回新的 Access/Refresh Token。

请求体：

```json
{
  "old_password": "old",
  "new_password": "new123456"
}
```

响应结构与 `login` 类似。

### `POST /api/auth/change-username`

修改用户名。

请求体：

```json
{
  "username": "new_name"
}
```

响应：

```json
{
  "message": "用户名修改成功",
  "username": "new_name"
}
```

### 强制改密约束

当用户 `must_change_password=true` 时，除以下接口外，其他受保护接口会返回：

```json
{
  "error": "首次登录请先修改密码",
  "code": "must_change_password"
}
```

状态码：`403`

允许访问：

- `GET /api/auth/me`
- `POST /api/auth/change-password`

## 频道接口 `/channels`

### `GET /api/channels`

查询参数：

- `group_id`（int，可选）
- `is_active`（bool，可选）
- `protocol`（`http|https|rtp|udp`，可选）
- `is_healthy`（bool，可选）
- `search`（可选，按频道名模糊搜索）
- `page`（默认 `1`）
- `per_page`（默认 `50`）

响应：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "per_page": 50,
  "pages": 0
}
```

### `GET /api/channels/{id}`

响应：频道对象。

### `POST /api/channels`

请求体示例：

```json
{
  "name": "CCTV-1",
  "url": "http://example.com/live.m3u8",
  "group_id": 1,
  "logo": "",
  "tvg_id": "cctv1",
  "sort_order": 0,
  "is_active": true
}
```

响应：

```json
{
  "message": "频道创建成功",
  "channel": {}
}
```

### `PUT /api/channels/{id}`

按字段局部更新。

响应：

```json
{
  "message": "频道更新成功",
  "channel": {}
}
```

### `DELETE /api/channels/{id}`

响应：

```json
{
  "message": "频道删除成功"
}
```

### `POST /api/channels/batch-delete`

请求体：

```json
{
  "ids": [1, 2, 3]
}
```

### `POST /api/channels/sort`

请求体：

```json
{
  "orders": [
    {"id": 1, "sort_order": 10},
    {"id": 2, "sort_order": 20}
  ]
}
```

## 分组接口 `/groups`

### `GET /api/groups`

查询参数：`include_channels=true|false`（默认 `false`）

响应：分组数组。

### `GET /api/groups/{id}`

响应：分组对象。

### `POST /api/groups`

请求体：

```json
{
  "name": "央视",
  "sort_order": 0
}
```

### `PUT /api/groups/{id}`

请求体：`name`、`sort_order` 任意组合。

### `DELETE /api/groups/{id}`

分组下仍有频道时返回 `400`。

### `POST /api/groups/sort`

请求体同频道排序。

### `DELETE /api/groups/empty`

删除空分组。

## 系统设置接口 `/settings`

### `GET /api/settings`

返回 settings 键值对象：

```json
{
  "site_name": "IPTV Proxy Admin",
  "udpxy_enabled": "false"
}
```

### `GET /api/settings/{key}`

```json
{
  "key": "site_name",
  "value": "IPTV Proxy Admin"
}
```

### `POST /api/settings`

批量写入。

请求体示例：

```json
{
  "site_name": "My IPTV",
  "health_check_threads": "3"
}
```

### `PUT /api/settings/{key}`

请求体：

```json
{
  "value": "new_value"
}
```

### `POST /api/settings/reload`

重载运行时配置。

成功：

```json
{
  "message": "配置已重新加载"
}
```

### `POST /api/settings/test-udpxy`

请求体：

```json
{
  "url": "http://192.168.1.10:3680"
}
```

成功响应示例：

```json
{
  "success": true,
  "message": "UDPxy 服务器连接成功",
  "status_code": 200,
  "tested_url": "http://192.168.1.10:3680/status",
  "resolved_base_url": "http://192.168.1.10:3680"
}
```

失败响应示例：

```json
{
  "success": false,
  "message": "无法连接到 UDPxy 服务器，请检查地址、端口和网络连通性",
  "attempted_urls": [
    "http://192.168.1.10:3680/status"
  ]
}
```

## 仪表盘接口 `/dashboard`

### `GET /api/dashboard`

返回频道、分组、协议分布、活跃连接与不健康频道列表。

### `GET /api/dashboard/watch-stats?days=7`

返回最近 N 天每日观看时长（秒）。

### `GET /api/dashboard/channel-ranking?days=7&limit=10`

返回观看排行（按总时长降序）。

### `GET /api/dashboard/version`

无需登录，返回版本信息：

```json
{
  "version": "0.2.0",
  "name": "IPTV Proxy Admin"
}
```

## 健康检测接口 `/health`

### `POST /api/health/check/{id}`

检测单个频道。

### `POST /api/health/check-all`

检测所有启用频道。

### `GET /api/health/status`

返回总数、健康数、不健康数及不健康频道列表。

## 代理接口 `/proxy`

### `GET /api/proxy/stream/{id}?token=...`

- 无需 Bearer
- 需要订阅 token
- 返回实际流媒体内容

常见错误：

- `401`：缺少或无效 token
- `403`：频道被禁用
- `404`：频道不存在
- `500`：组播但 UDPxy 未配置 / 会话创建失败

### `GET /api/proxy/status`

需要 Bearer，返回当前活跃连接列表：

```json
{
  "active_connections": 1,
  "connections": [
    {
      "connection_id": "1_2_xxx",
      "watch_record_id": 100,
      "user_id": 1,
      "username": "admin",
      "channel_id": 2,
      "channel_name": "CCTV-1",
      "start_time": "2026-02-22T10:00:00Z",
      "last_heartbeat": "2026-02-22T10:00:10Z"
    }
  ]
}
```

## 订阅接口 `/subscription`

### `GET /api/subscription/urls`

需要 Bearer，返回当前用户订阅地址：

```json
{
  "m3u_url": "http://host/api/subscription/m3u?token=...",
  "txt_url": "http://host/api/subscription/txt?token=...",
  "token": "..."
}
```

### `GET /api/subscription/m3u?token=...`

返回 M3U 文本（`audio/x-mpegurl`）。

### `GET /api/subscription/txt?token=...`

返回 TXT 文本（`text/plain`）。

## 观看历史接口 `/history`

### `GET /api/history/list?page=1&per_page=20`

返回已结束且时长 `>= 5` 秒的历史记录分页。

### `GET /api/history/stats`

返回总记录数、最早记录时间、最新记录时间。

### `POST /api/history/cleanup`

清理“已结束”的历史记录（不会删除进行中的活跃连接记录）。

## 导入导出接口 `/import-export`

### `POST /api/import-export/import`

两种方式：

1. `multipart/form-data` 上传 `file`
2. JSON 内容导入

JSON 示例：

```json
{
  "content": "...",
  "format": "m3u",
  "overwrite": false,
  "auto_create_group": true,
  "include_regex": "",
  "exclude_regex": ""
}
```

### `POST /api/import-export/import-url`

```json
{
  "url": "http://example.com/list.m3u",
  "overwrite": false,
  "auto_create_group": true,
  "format": "auto",
  "include_regex": "",
  "exclude_regex": ""
}
```

### `GET /api/import-export/export?format=m3u|txt`

返回导出文件流（需要 Bearer）。

## 常见状态码

- `200`：请求成功
- `201`：资源创建成功
- `400`：参数错误
- `401`：未登录/令牌无效
- `403`：无权限或需先改密
- `404`：资源不存在
- `500`：服务端错误
