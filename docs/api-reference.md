# IPTV Proxy Admin API 文档

本文档描述了 IPTV Proxy Admin 管理系统的 API 接口。

---

## 基础信息

- **基础 URL**: `/api`
- **认证方式**: 大多数接口需要通过 `/api/auth/login` 获取的会话 Cookie 进行认证
- **请求头**: 默认使用 `application/json` 格式发送数据
- **响应格式**: JSON

---

## 认证接口 - `/auth`

### 用户登录
- **接口**: `POST /api/auth/login`
- **描述**: 用户身份验证并返回会话
- **参数**:
  - Request Body (JSON): `{username: String, password: String}`
- **响应**: `{success: Boolean, message: String, data: Object}`

### 用户登出
- **接口**: `POST /api/auth/logout`
- **描述**: 清除用户会话
- **参数**: 无
- **响应**: `{success: Boolean, message: String}`

### 获取当前用户信息
- **接口**: `GET /api/auth/me`
- **描述**: 获取当前已认证用户的信息
- **参数**: 无
- **响应**: `{success: Boolean, data: {id, username, created_at}}`

### 重置订阅 Token
- **接口**: `POST /api/auth/reset-token`
- **描述**: 重新生成订阅访问令牌
- **参数**: 无
- **响应**: `{success: Boolean, message: String, data: {token}}`

### 修改密码
- **接口**: `POST /api/auth/change-password`
- **描述**: 修改当前用户密码
- **参数**:
  - Request Body (JSON): `{old_password: String, new_password: String}`
- **响应**: `{success: Boolean, message: String}`

### 修改用户名
- **接口**: `POST /api/auth/change-username`
- **描述**: 修改当前用户名
- **参数**:
  - Request Body (JSON): `{username: String}`
- **响应**: `{success: Boolean, message: String}`

---

## 频道管理接口 - `/channels`

### 获取频道列表
- **接口**: `GET /api/channels`
- **描述**: 获取频道列表，支持分页和筛选
- **参数**:
  - Query: `group_id` (可选): 按分组筛选
  - Query: `is_active` (可选): 按活跃状态筛选
  - Query: `search` (可选): 搜索关键词
  - Query: `page` (可选): 页码，默认为1
  - Query: `per_page` (可选): 每页数量，默认为20
- **响应**: `{success: Boolean, data: {items: Array, pagination: Object}}`

### 创建频道
- **接口**: `POST /api/channels`
- **描述**: 创建新的频道
- **参数**:
  - Request Body (JSON): `{name: String, url: String, group_id: Number, logo: String, tvg_id: String, ...}`
- **响应**: `{success: Boolean, data: ChannelObject}`

### 获取频道详情
- **接口**: `GET /api/channels/{id}`
- **描述**: 获取指定频道的详细信息
- **参数**: 路径参数 `id`: 频道唯一标识符
- **响应**: `{success: Boolean, data: ChannelObject}`

### 更新频道
- **接口**: `PUT /api/channels/{id}`
- **描述**: 更新频道信息
- **参数**:
  - 路径参数 `id`: 频道唯一标识符
  - Request Body (JSON): `{name: String, url: String, ...}`
- **响应**: `{success: Boolean, data: ChannelObject}`

### 删除频道
- **接口**: `DELETE /api/channels/{id}`
- **描述**: 删除指定频道
- **参数**: 路径参数 `id`: 频道唯一标识符
- **响应**: `{success: Boolean, message: String}`

### 批量删除频道
- **接口**: `POST /api/channels/batch-delete`
- **描述**: 批量删除多个频道
- **参数**:
  - Request Body (JSON): `{ids: Array<Number>}`
- **响应**: `{success: Boolean, message: String}`

### 更新频道排序
- **接口**: `POST /api/channels/sort`
- **描述**: 更新频道的显示顺序
- **参数**:
  - Request Body (JSON): `{orders: Array<{id: Number, sort_order: Number}>}`
- **响应**: `{success: Boolean, message: String}`

---

## 分组管理接口 - `/groups`

### 获取分组列表
- **接口**: `GET /api/groups`
- **描述**: 获取所有分组列表
- **参数**:
  - Query: `include_channels` (可选): 是否包含频道信息 (Boolean)
- **响应**: `{success: Boolean, data: Array<GroupObject>}`

### 创建分组
- **接口**: `POST /api/groups`
- **描述**: 创建新分组
- **参数**:
  - Request Body (JSON): `{name: String, sort_order: Number}`
- **响应**: `{success: Boolean, data: GroupObject}`

### 获取分组详情
- **接口**: `GET /api/groups/{id}`
- **描述**: 获取指定分组的详细信息
- **参数**:
  - 路径参数 `id`: 分组唯一标识符
  - Query: `include_channels` (可选): 是否包含频道信息
- **响应**: `{success: Boolean, data: GroupObject}`

### 更新分组
- **接口**: `PUT /api/groups/{id}`
- **描述**: 更新分组信息
- **参数**:
  - 路径参数 `id`: 分组唯一标识符
  - Request Body (JSON): `{name: String, sort_order: Number}`
- **响应**: `{success: Boolean, data: GroupObject}`

### 删除分组
- **接口**: `DELETE /api/groups/{id}`
- **描述**: 删除指定分组
- **参数**: 路径参数 `id`: 分组唯一标识符
- **响应**: `{success: Boolean, message: String}`

### 更新分组排序
- **接口**: `POST /api/groups/sort`
- **描述**: 更新分组的显示顺序
- **参数**:
  - Request Body (JSON): `{orders: Array<{id: Number, sort_order: Number}>}`
- **响应**: `{success: Boolean, message: String}`

### 删除空分组
- **接口**: `DELETE /api/groups/empty`
- **描述**: 删除所有不包含频道的空分组
- **参数**: 无
- **响应**: `{success: Boolean, message: String}`

---

## 系统设置接口 - `/settings`

### 获取所有设置
- **接口**: `GET /api/settings`
- **描述**: 获取系统所有配置项
- **参数**: 无
- **响应**: `{success: Boolean, data: {key: value}}`

### 批量更新设置
- **接口**: `POST /api/settings`
- **描述**: 批量更新多个配置项
- **参数**:
  - Request Body (JSON): `{key1: value1, key2: value2, ...}`
- **响应**: `{success: Boolean, message: String}`

### 获取单项设置
- **接口**: `GET /api/settings/{key}`
- **描述**: 获取指定配置项的值
- **参数**: 路径参数 `key`: 配置项键名
- **响应**: `{success: Boolean, data: value}`

### 更新单项设置
- **接口**: `PUT /api/settings/{key}`
- **描述**: 更新指定配置项的值
- **参数**:
  - 路径参数 `key`: 配置项键名
  - Request Body (JSON): `{value: newValue}`
- **响应**: `{success: Boolean, message: String}`

---

## 仪表盘接口 - `/dashboard`

### 获取仪表盘统计
- **接口**: `GET /api/dashboard`
- **描述**: 获取系统整体统计数据
- **参数**: 无
- **响应**: `{success: Boolean, data: DashboardStatsObject}`

### 获取观看时长统计
- **接口**: `GET /api/dashboard/watch-stats`
- **描述**: 获取用户观看时长统计信息
- **参数**:
  - Query: `days` (可选): 统计天数，默认为7天
- **响应**: `{success: Boolean, data: WatchStatsArray}`

### 获取频道排行
- **接口**: `GET /api/dashboard/channel-ranking`
- **描述**: 获取最受欢迎频道排行
- **参数**:
  - Query: `days` (可选): 统计天数
  - Query: `limit` (可选): 返回结果数量限制
- **响应**: `{success: Boolean, data: ChannelRankingArray}`

---

## 健康检测接口 - `/health`

### 获取健康状态概览
- **接口**: `GET /api/health/status`
- **描述**: 获取系统健康状态总览
- **参数**: 无
- **响应**: `{success: Boolean, data: HealthStatusObject}`

### 触发全量检测
- **接口**: `POST /api/health/check-all`
- **描述**: 对所有频道执行可用性检测
- **参数**: 无
- **响应**: `{success: Boolean, message: String, data: DetectionResults}`

### 检测单个频道
- **接口**: `POST /api/health/check/{id}`
- **描述**: 对指定频道执行可用性检测
- **参数**: 路径参数 `id`: 频道唯一标识符
- **响应**: `{success: Boolean, message: String, data: ChannelHealth}`

---

## 代理服务接口 - `/proxy`

### 直播流代理
- **接口**: `GET /api/proxy/stream/{id}`
- **描述**: 代理直播流，提供统一播放入口
- **参数**:
  - 路径参数 `id`: 频道唯一标识符
  - Query: `token` (必填): 订阅令牌
- **响应**: 直接返回直播流数据

### 获取代理状态
- **接口**: `GET /api/proxy/status`
- **描述**: 获取当前代理连接状态
- **参数**: 无
- **响应**: `{success: Boolean, data: ProxyStatusObject}`

---

## 订阅服务接口 - `/subscription`

### 获取订阅链接
- **接口**: `GET /api/subscription/urls`
- **描述**: 获取各种格式的订阅链接地址
- **参数**: 无
- **响应**: `{success: Boolean, data: {m3u_url, txt_url}}`

### 下载 M3U 播放列表
- **接口**: `GET /api/subscription/m3u`
- **描述**: 以 M3U 格式下载播放列表
- **参数**: Query: `token` (必填): 订阅令牌
- **响应**: M3U 格式的播放列表文本

### 下载 TXT 播放列表
- **接口**: `GET /api/subscription/txt`
- **描述**: 以 TXT 格式下载播放列表
- **参数**: Query: `token` (必填): 订阅令牌
- **响应**: TXT 格式的播放列表文本

---

## 错误码说明

| 错误码 | 说明 |
| :--- | :--- |
| `200` | 成功 |
| `400` | 请求参数错误 |
| `401` | 未授权或会话过期 |
| `403` | 权限不足 |
| `404` | 资源不存在 |
| `422` | 数据验证失败 |
| `500` | 服务器内部错误 |

---

## 使用示例

### JavaScript 示例
```javascript
// 获取频道列表
fetch('/api/channels?page=1&per_page=20', {
  method: 'GET',
  credentials: 'include'
})
.then(response => response.json())
.then(data => console.log(data));

// 创建频道
fetch('/api/channels', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'credentials': 'include'
  },
  body: JSON.stringify({
    name: '测试频道',
    url: 'http://example.com/stream',
    group_id: 1
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

### cURL 示例
```bash
# 获取当前用户信息
curl -X GET http://localhost:8000/api/auth/me \
  -H "Cookie: session=your_session_cookie"

# 创建新频道
curl -X POST http://localhost:8000/api/channels \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{"name":"测试频道","url":"http://example.com/stream","group_id":1}'
```