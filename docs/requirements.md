# IPTV Proxy Admin - 产品需求文档（PRD）

---

## 📖 目录

1. [项目概述](#项目概述)
2. [功能需求](#功能需求)
3. [非功能需求](#非功能需求)
4. [用户角色与权限](#用户角色与权限)
5. [数据模型](#数据模型)
6. [界面设计要求](#界面设计要求)
7. [技术架构](#技术架构)

---

## 项目概述

### 产品名称
**IPTV Proxy Admin**（IPTV代理管理系统）

### 产品定位
一个全功能的 IPTV 直播源管理、流代理和转发的 Web 管理平台，为 IPTV 用户提供频道管理、健康检测、流代理转发、订阅生成等核心功能。

### 目标用户

| 用户类型 | 使用场景 | 核心需求 |
|---------|---------|---------|
| **IPTV服务提供商** | 管理大量频道，为用户提供服务 | 批量管理、稳定性、性能 |
| **个人IPTV爱好者** | 收集管理个人频道源 | 易用性、订阅生成 |
| **家庭网络管理员** | 家庭内部流媒体管理 | 简单配置、局域网访问 |
| **小型直播源运维** | 维护小规模直播平台 | 监控、健康检测、统计 |

### 核心价值主张

| 价值点 | 说明 | 优势 |
|-------|------|------|
| 🎯 **集中管理** | 统一Web界面管理所有IPTV频道 | 提高效率，降低管理成本 |
| 💊 **健康监控** | 自动检测频道可用性，及时发现故障 | 减少用户投诉，提升服务质量 |
| 🔄 **流代理转发** | 支持HTTP/HTTPS/RTP/UDP等多种协议 | 兼容性强，适应多种场景 |
| 📡 **灵活订阅** | 生成M3U/TXT格式订阅链接 | 支持多种播放器，用户友好 |
| 📊 **实时统计** | 观看统计、热度排行、连接监控 | 数据驱动决策，优化内容 |
| 🌐 **组播转换** | UDPxy支持，组播转HTTP流 | 解决组播源播放问题 |
| 🚀 **易于部署** | SQLite/MySQL，Docker支持 | 快速上线，运维简单 |

---

## 功能需求

### 1. 认证与授权模块

#### 1.1 用户登录

**功能描述**: 用户通过用户名和密码进行身份验证，获取系统访问权限。

**页面元素**:
- 网站Logo（可配置）
- 网站名称（可配置，默认"IPTV Proxy Admin"）
- 欢迎文字提示
- 用户名输入框（带图标提示）
- 密码输入框（带图标提示，密码掩码）
- "登录"按钮
- 主题切换按钮（右上角浮动）

**交互流程**:
```
用户输入用户名和密码
    ↓
前端验证（非空）
    ↓
提交到 POST /api/auth/login
    ↓
后端验证凭证 ← bcrypt验证密码哈希
    ↓
成功：设置Session Cookie → 跳转到仪表盘
失败：显示错误提示
```

**验证规则**:
- 用户名不能为空
- 密码不能为空
- 默认账户：`admin` / `admin123`（首次启动时创建）

**业务规则**:
- Session过期时间：24小时（可配置）
- 密码使用bcrypt加密存储（工作因子≥12）
- 登录失败不暴露是用户名还是密码错误

**API接口**:
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

Response (200):
{
  "success": true,
  "message": "登录成功",
  "data": {
    "id": 1,
    "username": "admin"
  }
}

Response (401):
{
  "error": "用户名或密码错误"
}
```

#### 1.2 用户登出

**功能描述**: 清除用户会话，返回登录页面。

**触发方式**:
- 点击右上角用户菜单 → "登出"

**交互流程**:
```
用户点击"登出"
    ↓
调用 POST /api/auth/logout
    ↓
后端清除Session
    ↓
前端清除状态存储
    ↓
跳转到登录页
```

#### 1.3 会话管理

**功能描述**: 管理用户登录状态和权限验证。

**实现方式**:
- 使用Flask-Login管理会话
- Session存储在Cookie中
- 所有需要认证的API都验证Session

**会话特性**:
- HttpOnly Cookie（防止XSS）
- SameSite=Strict（防止CSRF）
- Secure标志（HTTPS环境）
- 自动续期（活跃用户）

**失效处理**:
- Session过期：返回401
- 前端自动跳转到登录页
- 保存跳转前的URL，登录后恢复

---

### 2. 仪表盘模块

#### 2.1 系统概览

**功能描述**: 展示系统核心指标的实时统计数据。

**统计卡片**（4个）:

| 卡片 | 指标 | 说明 | 数据来源 |
|-----|------|------|---------|
| 📺 **频道统计** | 总频道数 / 活跃频道数 | 显示频道总量和已启用的频道数 | `Channel.count()` |
| 📁 **分组统计** | 总分组数 | 显示频道分组总数 | `ChannelGroup.count()` |
| 💊 **健康状态** | 健康频道数 / 健康率 | 显示检测正常的频道数及百分比 | `Channel.filter(is_healthy=True)` |
| 🔗 **代理连接** | 当前活跃连接 | 显示正在进行的流代理连接数 | `len(active_connections)` |

**计算公式**:
```python
# 健康率计算
health_rate = (healthy_channels / active_channels) * 100

# 显示格式
if active_channels == 0:
    health_rate = "100%"  # 没有频道时显示100%
else:
    health_rate = f"{health_rate:.1f}%"
```

**刷新机制**:
- 页面加载时自动获取
- 执行健康检测后自动刷新

#### 2.2 协议分布统计

**功能描述**: 以进度条形式展示各协议类型的频道分布。

**显示内容**:
- HTTP频道数量及占比
- HTTPS频道数量及占比
- RTP频道数量及占比
- UDP频道数量及占比

**视觉设计**:
- 横向进度条
- 不同协议使用不同颜色
- 显示数量和百分比

**数据计算**:
```python
# 协议统计
protocols = {
    'http': Channel.filter_by(protocol='http').count(),
    'https': Channel.filter_by(protocol='https').count(),
    'rtp': Channel.filter_by(protocol='rtp').count(),
    'udp': Channel.filter_by(protocol='udp').count()
}

# 百分比计算
total = sum(protocols.values())
for protocol, count in protocols.items():
    percentage = (count / total * 100) if total > 0 else 0
```

#### 2.3 不可用频道列表

**功能描述**: 展示健康检测失败的频道，便于快速定位问题。

**显示内容**:
- 频道名称
- 所属分组
- 最多显示10条

**空状态**:
- 无不可用频道时显示："✓ 所有频道运行正常"

**数据查询**:
```sql
SELECT name, group_name
FROM channels
WHERE is_healthy = FALSE AND is_active = TRUE
ORDER BY last_check DESC
LIMIT 10
```

#### 2.4 每日观看时长统计

**功能描述**: 以折线图展示用户观看时长的历史趋势。

**图表类型**: ECharts折线图

**时间范围选择**:
- 📅 7天（默认）
- 📅 14天
- 📅 30天

**数据维度**:
- X轴：日期（YYYY-MM-DD）
- Y轴：观看时长（自动单位：分钟/小时）

**数据转换**:
```python
# 查询观看历史
stats = db.session.query(
    WatchHistory.watch_date,
    func.sum(WatchHistory.duration).label('total_duration')
).filter(
    WatchHistory.watch_date >= (today - timedelta(days=days))
).group_by(
    WatchHistory.watch_date
).order_by(
    WatchHistory.watch_date
).all()

# 格式化输出
data = {
    'dates': [stat.watch_date.strftime('%Y-%m-%d') for stat in stats],
    'durations': [stat.total_duration / 60 for stat in stats]  # 转为分钟
}
```

**交互特性**:
- 鼠标悬停显示详细数值
- 显示总观看时长
- 支持切换时间范围

#### 2.5 热门频道排行

**功能描述**: 展示最受欢迎的频道排名，按观看时长排序。

**排名展示**:
- 显示前10名频道
- 前3名高亮显示（金、银、铜色背景）
- 显示频道名称和总观看时长

**时间范围选择**:
- 📅 7天（默认）
- 📅 14天
- 📅 30天

**排序规则**:
```sql
SELECT
    c.id as channel_id,
    c.name as channel_name,
    SUM(w.duration) as total_duration,
    COUNT(w.id) as watch_count
FROM watch_history w
JOIN channels c ON w.channel_id = c.id
WHERE w.watch_date >= DATE_SUB(CURDATE(), INTERVAL ? DAY)
GROUP BY w.channel_id
ORDER BY total_duration DESC
LIMIT 10
```

**时长格式化**:
- < 60秒：显示"< 1分钟"
- < 3600秒：显示"X分钟"
- ≥ 3600秒：显示"X小时Y分钟"

#### 2.6 快捷操作面板

**功能描述**: 提供常用功能的快速访问入口。

**操作项**（4个）:

| 图标 | 名称 | 操作 | 目标页面 |
|-----|------|------|---------|
| ➕ | 添加频道 | 跳转 | `/channels` |
| 🔗 | 获取订阅 | 跳转 | `/subscription` |
| 🔄 | 健康检测 | 执行 | 当前页 |
| ⚙️ | 系统设置 | 跳转 | `/settings` |

**健康检测交互**:
```
用户点击"健康检测"
    ↓
显示加载状态："检测中..."
    ↓
调用 POST /api/health/check-all
    ↓
后端并发检测所有频道
    ↓
返回结果：{healthy: 50, unhealthy: 5}
    ↓
显示提示："检测完成：正常50个，异常5个"
    ↓
刷新仪表盘数据
```

---

### 3. 频道管理模块

#### 3.1 频道列表展示

**功能描述**: 以表格形式分页展示所有IPTV频道。

**表格列定义**:

| 列名 | 宽度 | 数据类型 | 说明 |
|-----|------|---------|------|
| **Logo** | 80px | 图片 | 频道Logo缩略图，缺失时显示占位符 |
| **频道名称** | 自适应 | 文本 | 频道名称，支持搜索 |
| **分组** | 120px | 标签 | 所属分组，彩色标签显示 |
| **协议** | 100px | 标签 | http/https/rtp/udp，不同颜色 |
| **健康状态** | 100px | 标签 | 正常(绿)/离线(红) |
| **启用状态** | 80px | 开关 | is_active切换开关 |
| **操作** | 150px | 按钮组 | 检测/编辑/删除按钮 |

**分页配置**:
```javascript
{
  currentPage: 1,
  pageSize: 50,  // 默认每页50条
  pageSizes: [20, 50, 100],  // 可选项
  total: 0  // 总记录数
}
```

**行内操作**:

| 操作 | 图标 | 功能 | API |
|-----|------|------|-----|
| **启用开关** | 开关 | 切换频道启用状态 | `PUT /api/channels/{id}` |
| **检测** | 🔍 | 执行单个频道健康检测 | `POST /api/health/check/{id}` |
| **编辑** | ✏️ | 打开编辑对话框 | - |
| **删除** | 🗑️ | 删除频道（需确认） | `DELETE /api/channels/{id}` |

**批量操作**:
- 表格支持多选（复选框）
- 显示"已选择X项"
- "批量删除"按钮（选中时显示）
- 删除前二次确认

**空状态**:
- 无频道时显示友好提示
- "添加第一个频道"按钮

#### 3.2 频道搜索与筛选

**功能描述**: 提供多维度的频道筛选功能，快速定位目标频道。

**筛选项定义**:

| 筛选器 | 类型 | 选项 | 行为 |
|-------|------|------|------|
| **搜索框** | 输入 | 频道名称模糊搜索 | 300ms防抖 |
| **分组筛选** | 下拉 | 全部/各分组 | 立即筛选 |
| **协议筛选** | 下拉 | 全部/HTTP/HTTPS/RTP/UDP | 立即筛选 |
| **启用状态** | 下拉 | 全部/已启用/已禁用 | 立即筛选 |
| **健康状态** | 下拉 | 全部/正常/离线 | 立即筛选 |

**筛选逻辑**:
```javascript
// 筛选条件合并（AND关系）
const filters = {
  search: searchText,           // 模糊搜索
  group_id: selectedGroup,      // 精确匹配
  protocol: selectedProtocol,   // 精确匹配
  is_active: isActiveFilter,    // 布尔匹配
  is_healthy: isHealthyFilter   // 布尔匹配
}

// API请求
GET /api/channels?search=xxx&group_id=1&protocol=http&is_active=true
```

**交互特性**:
- 任何筛选变更立即触发列表刷新
- 搜索自动重置到第1页
- 显示加载动画
- 支持清空筛选（"重置"按钮）

**URL参数同步**:
```javascript
// 筛选条件同步到URL查询参数
/channels?search=cctv&group_id=1&protocol=http&page=2

// 刷新页面保持筛选状态
```

#### 3.3 频道详情编辑

**功能描述**: 创建新频道或修改现有频道的详细信息。

**对话框表单**:

| 字段名 | 类型 | 必填 | 验证规则 | 说明 |
|-------|------|------|---------|------|
| **频道名称** | 文本 | ✓ | 1-200字符 | 频道显示名称 |
| **频道地址** | 文本 | ✓ | URL格式 | 流地址，支持http/https/rtp/udp |
| **Logo URL** | 文本 | ✗ | URL格式 | 频道Logo图片地址 |
| **TVG-ID** | 文本 | ✗ | 100字符 | EPG节目单ID |
| **分组** | 下拉 | ✗ | - | 所属分组，支持"无分组" |
| **排序** | 数字 | ✗ | ≥0 | 显示顺序，数值越小越靠前 |

**URL格式验证**:
```javascript
// 协议检测正则
const protocolPatterns = {
  http: /^https?:\/\/.+/,
  rtp: /^rtp:\/\/.+/,
  udp: /^udp:\/\/@?.+/
}

// 验证示例
function validateChannelUrl(url) {
  // HTTP/HTTPS
  if (/^https?:\/\//.test(url)) {
    return validateHttpUrl(url)
  }
  // RTP
  if (/^rtp:\/\//.test(url)) {
    return validateMulticastUrl(url)
  }
  // UDP
  if (/^udp:\/\//.test(url)) {
    return validateMulticastUrl(url)
  }
  return { valid: false, message: '不支持的协议' }
}
```

**协议自动检测**:
```javascript
// 根据URL自动设置protocol字段
function detectProtocol(url) {
  if (url.startsWith('https://')) return 'https'
  if (url.startsWith('http://')) return 'http'
  if (url.startsWith('rtp://')) return 'rtp'
  if (url.startsWith('udp://')) return 'udp'
  return 'http'  // 默认
}
```

**快速创建分组**:
```
用户在分组下拉框输入新分组名
    ↓
点击"创建新分组"
    ↓
调用 POST /api/groups {name: "新分组"}
    ↓
返回新分组ID
    ↓
自动选中新分组
    ↓
刷新分组列表
```

**提交流程**:
```
用户填写表单
    ↓
前端验证（必填项、格式）
    ↓
提交到 POST /api/channels 或 PUT /api/channels/{id}
    ↓
后端验证
    ↓
保存到数据库
    ↓
返回成功/失败
    ↓
成功：关闭对话框，刷新列表
失败：显示错误提示
```

#### 3.4 频道导入

**功能描述**: 从外部源批量导入频道数据，支持多种导入方式。

**导入方式**（3种）:

##### 方式一：文件上传

**支持格式**:
- `.m3u` - M3U播放列表
- `.txt` - 文本格式频道列表

**交互流程**:
```
用户点击"上传文件"
    ↓
选择文件（.m3u或.txt）
    ↓
前端读取文件内容
    ↓
自动检测格式
    ↓
显示预览（可选）
    ↓
配置导入选项
    ↓
提交导入
```

##### 方式二：粘贴内容

**支持格式**:
- M3U格式文本
- TXT格式文本

**交互流程**:
```
用户选择"粘贴内容"
    ↓
在文本框粘贴播放列表
    ↓
手动选择格式（M3U/TXT）
    ↓
配置导入选项
    ↓
提交导入
```

##### 方式三：URL导入

**支持协议**:
- HTTP
- HTTPS

**交互流程**:
```
用户选择"URL导入"
    ↓
输入远程播放列表URL
    ↓
点击"获取"
    ↓
后端下载内容
    ↓
自动检测格式
    ↓
配置导入选项
    ↓
提交导入
```

**导入配置选项**:

| 选项 | 类型 | 默认值 | 说明 |
|-----|------|--------|------|
| **覆盖现有数据** | 开关 | OFF | 导入前是否清空现有频道 |
| **自动创建分组** | 开关 | ON | 自动创建播放列表中的新分组 |
| **包含关键词** | 文本 | 空 | 正则匹配，只导入匹配的频道 |
| **排除关键词** | 文本 | 空 | 正则匹配，跳过匹配的频道 |

**M3U格式解析**:
```
#EXTM3U x-tvg-url="http://epg.example.com/guide.xml"
#EXTINF:-1 tvg-id="cctv1" tvg-name="CCTV-1" tvg-logo="http://logo.url" group-title="央视频道",CCTV-1综合
http://stream.example.com/cctv1

解析规则：
- 识别 #EXTM3U 开头
- 提取 x-tvg-url 作为EPG地址
- 解析 #EXTINF 行：
  - tvg-id → channel.tvg_id
  - tvg-logo → channel.logo
  - group-title → channel_group.name
  - 逗号后为频道名 → channel.name
- 下一行为流地址 → channel.url
```

**TXT格式解析**:
```
央视频道,#genre#
CCTV-1综合,http://stream.example.com/cctv1
CCTV-2财经,http://stream.example.com/cctv2

地方台,#genre#
北京卫视,http://stream.example.com/btv1

解析规则：
- 识别 ",#genre#" 为分组标记
- 分组标记前为分组名
- 其他行格式：频道名,流地址
```

**导入结果反馈**:
```javascript
{
  "success": true,
  "message": "导入完成",
  "data": {
    "total": 100,        // 解析到的频道总数
    "imported": 95,      // 成功导入的频道数
    "skipped": 5,        // 跳过的频道数（重复或被过滤）
    "groups_created": 10 // 新创建的分组数
  }
}
```

#### 3.5 频道导出

**功能描述**: 将频道列表导出为标准格式文件，供其他播放器使用。

**导出格式**（2种）:

##### 格式一：M3U

**文件扩展名**: `.m3u`

**内容结构**:
```
#EXTM3U x-tvg-url="http://epg.example.com/guide.xml"

#EXTINF:-1 tvg-id="cctv1" tvg-name="CCTV-1" tvg-logo="http://logo.url" group-title="央视频道",CCTV-1综合
http://stream.example.com/cctv1

#EXTINF:-1 tvg-id="cctv2" tvg-name="CCTV-2" tvg-logo="http://logo.url" group-title="央视频道",CCTV-2财经
http://stream.example.com/cctv2
```

**生成规则**:
- 包含EPG URL（如已配置）
- 只导出启用的频道（`is_active=true`）
- 按分组和排序顺序组织
- 包含tvg-id、tvg-name、tvg-logo、group-title元数据

##### 格式二：TXT

**文件扩展名**: `.txt`

**内容结构**:
```
央视频道,#genre#
CCTV-1综合,http://stream.example.com/cctv1
CCTV-2财经,http://stream.example.com/cctv2

地方台,#genre#
北京卫视,http://stream.example.com/btv1
```

**生成规则**:
- 分组名称,#genre# 格式
- 频道名,流地址 格式
- 只导出启用的频道
- 按分组和排序顺序组织

**导出流程**:
```
用户点击"导出频道"
    ↓
选择格式（M3U/TXT）
    ↓
调用 GET /api/import-export/export?format=m3u
    ↓
后端生成文件内容
    ↓
设置响应头：
  Content-Type: application/octet-stream
  Content-Disposition: attachment; filename="channels.m3u"
    ↓
浏览器下载文件
```

---

### 4. 分组管理模块

#### 4.1 分组列表展示

**功能描述**: 以卡片网格形式展示所有频道分组。

**卡片内容**:
```
┌───────────────┐
│  📁 图标      │
│  分组名称     │
│  频道数: 25   │
│  ✏️ 编辑 🗑️ 删除│
└───────────────┘
```

**布局方式**:
- 栅格布局（Grid）
- 每行自适应列数
- 最小卡片宽度：280px
- 响应式调整

**特殊卡片**:
- "➕ 添加分组"卡片（固定第一个位置）
- 点击打开新建分组对话框

**排序显示**:
- 按 `sort_order` 字段升序排列
- `sort_order` 相同时按创建时间排序

**空状态**:
- 无分组时显示："暂无分组，点击添加第一个分组"

#### 4.2 分组创建/编辑

**功能描述**: 创建新分组或修改现有分组信息。

**对话框表单**:

| 字段名 | 类型 | 必填 | 验证规则 | 默认值 |
|-------|------|------|---------|--------|
| **分组名称** | 文本 | ✓ | 1-100字符 | - |
| **排序** | 数字 | ✗ | ≥0 | 0 |

**提交流程**:
```
用户填写表单
    ↓
前端验证
    ↓
提交到 POST /api/groups 或 PUT /api/groups/{id}
    ↓
后端保存
    ↓
成功：关闭对话框，刷新分组列表
失败：显示错误提示
```

#### 4.3 分组删除

**功能描述**: 删除频道分组，但需满足一定条件。

**删除规则**:
- ✓ 只能删除空分组（没有频道的分组）
- ✗ 如分组下有频道，禁止删除并提示

**删除流程**:
```
用户点击"删除"按钮
    ↓
检查分组下是否有频道
    ↓
有频道：
  显示警告："此分组下有X个频道，无法删除"
无频道：
  显示确认对话框："确定删除分组【分组名】吗？"
    ↓
用户确认
    ↓
调用 DELETE /api/groups/{id}
    ↓
成功：刷新分组列表
失败：显示错误提示
```

**批量删除空分组**:

**功能入口**: "删除空分组"按钮（工具栏）

**执行流程**:
```
用户点击"删除空分组"
    ↓
后端查询所有空分组
    ↓
显示确认："将删除X个空分组，确定吗？"
    ↓
用户确认
    ↓
调用 DELETE /api/groups/empty
    ↓
批量删除空分组
    ↓
显示结果："成功删除X个空分组"
    ↓
刷新分组列表
```

#### 4.4 分组排序

**功能描述**: 调整分组的显示顺序。

**实现方式**:
- 通过 `sort_order` 字段控制
- 数值越小越靠前
- 前端支持拖拽排序（可选）

**API支持**:
```http
POST /api/groups/sort
Content-Type: application/json

{
  "orders": [
    {"id": 1, "sort_order": 0},
    {"id": 2, "sort_order": 1},
    {"id": 3, "sort_order": 2}
  ]
}
```

---

### 5. 健康检测模块

#### 5.1 健康检测概述

**功能描述**: 定期或手动检测IPTV频道的可用性，及时发现故障频道。

**检测方式**:
1. **手动检测**（即时）
   - 单个频道检测
   - 全部频道检测

2. **定时检测**（后台）
   - 定时任务自动执行
   - 不阻塞主程序

**检测算法**:
```
对于HTTP/HTTPS频道：
  1. 发送HEAD请求到频道URL
  2. 设置超时时间（默认10秒）
  3. 检查响应状态码（200-299为成功）
  4. 失败后重试（默认1次）

对于RTP/UDP频道：
  1. 使用socket连接组播地址
  2. 尝试接收数据包
  3. 超时判定为失败
```

**检测结果**:
- 成功：`is_healthy = True`
- 失败：`is_healthy = False`
- 更新 `last_check` 为当前时间

#### 5.2 全局健康检测

**功能描述**: 对所有启用的频道执行健康检测。

**触发方式**:
1. 仪表盘 → 快捷操作 → "健康检测"
2. 频道列表 → 工具栏 → "检测全部"

**执行流程**:
```
用户点击"检测全部"
    ↓
禁用按钮，显示"检测中..."
    ↓
调用 POST /api/health/check-all
    ↓
后端：
  1. 查询所有启用的频道（is_active=true）
  2. 创建线程池（默认3个worker）
  3. 并发执行检测任务
  4. 收集检测结果
  5. 批量更新数据库
    ↓
返回结果：{healthy: 50, unhealthy: 5, total: 55}
    ↓
前端显示："检测完成：正常50个，异常5个"
    ↓
启用按钮，刷新列表
```

**并发控制**:
```python
from concurrent.futures import ThreadPoolExecutor

def check_all_channels():
    channels = Channel.query.filter_by(is_active=True).all()
    max_workers = get_health_check_threads()  # 默认3

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_channel_health, channel): channel
            for channel in channels
        }

        for future in as_completed(futures):
            channel = futures[future]
            try:
                is_healthy = future.result()
                channel.is_healthy = is_healthy
                channel.last_check = datetime.now()
            except Exception as e:
                logger.error(f"检测频道{channel.id}失败: {e}")
                channel.is_healthy = False

    db.session.commit()
```

#### 5.3 单个频道检测

**功能描述**: 检测单个频道的可用性。

**触发方式**: 频道列表 → 行操作 → "检测"按钮

**执行流程**:
```
用户点击单个频道的"检测"按钮
    ↓
按钮显示加载状态
    ↓
调用 POST /api/health/check/{channel_id}
    ↓
后端执行检测
    ↓
更新该频道的 is_healthy 和 last_check
    ↓
返回结果：{is_healthy: true, last_check: "2026-01-30T10:30:00"}
    ↓
前端更新该行的健康状态显示
    ↓
显示提示："检测完成"
```

#### 5.4 定时健康检测

**功能描述**: 后台定时任务，定期自动检测所有频道。

**配置项**:

| 配置项 | 环境变量 | 默认值 | 说明 |
|-------|---------|--------|------|
| **启用定时检测** | `HEALTH_CHECK_ENABLED` | `true` | 是否启用定时任务 |
| **检测间隔** | `HEALTH_CHECK_INTERVAL` | `1800` | 检测间隔（秒），默认30分钟 |

**实现方式**:
```python
from apscheduler.schedulers.background import BackgroundScheduler

def init_scheduler():
    if not config.HEALTH_CHECK_ENABLED:
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=check_all_channels,
        trigger='interval',
        seconds=config.HEALTH_CHECK_INTERVAL,
        id='health_check',
        name='频道健康检测',
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"定时健康检测已启动，间隔{config.HEALTH_CHECK_INTERVAL}秒")
```

**执行日志**:
```
[2026-01-30 10:00:00] INFO 定时健康检测开始，频道数: 100
[2026-01-30 10:00:15] INFO 检测完成，正常: 95，异常: 5，耗时: 15秒
```

#### 5.5 检测配置管理

**功能描述**: 在Web界面配置健康检测的相关参数。

**配置位置**: 系统设置 → 健康检测配置

**可配置项**:

| 配置项 | 类型 | 范围 | 默认值 | 说明 |
|-------|------|------|--------|------|
| **检测超时时间** | 数字 | 1-60秒 | 10秒 | 单个频道检测的超时限制 |
| **失败重试次数** | 数字 | 0-5次 | 1次 | 检测失败后的重试次数 |
| **检测线程数** | 数字 | 1-5线程 | 3线程 | 并发检测的线程池大小 |

**生效方式**:
- 立即生效，应用到新的检测任务
- 无需重启服务

**配置存储**:
- 保存到 `settings` 表
- 键名：`health_check_timeout`, `health_check_max_retries`, `health_check_threads`

---

### 6. 流代理模块

#### 6.1 流代理工作原理

**功能描述**: 作为中间代理，转发IPTV流到播放器，实现统一访问入口和观看统计。

**代理架构**:
```
播放器 → 代理服务器 → 上游流服务器

播放器请求：
GET /api/proxy/stream/123?token=abc123

代理服务器：
1. 验证Token有效性
2. 查询频道信息（ID=123）
3. 获取上游流URL
4. 转换协议（如需UDPxy）
5. 建立到上游的连接
6. 流式转发数据
7. 记录观看历史
```

**支持的协议**:

| 协议 | 示例 | 处理方式 | 说明 |
|-----|------|---------|------|
| **HTTP** | `http://example.com/stream` | 直接转发 | 标准HTTP流 |
| **HTTPS** | `https://example.com/stream` | 直接转发 | 加密HTTP流 |
| **RTP** | `rtp://239.0.0.1:5000` | UDPxy转换 | 组播流 |
| **UDP** | `udp://@239.0.0.1:5000` | UDPxy转换 | 组播流 |

**协议转换（UDPxy）**:
```python
def convert_multicast_url(channel_url, udpxy_url):
    """将组播地址转换为HTTP地址"""
    # RTP: rtp://239.0.0.1:5000
    # UDP: udp://@239.0.0.1:5000

    # 提取IP和端口
    match = re.search(r'(\d+\.\d+\.\d+\.\d+):(\d+)', channel_url)
    if not match:
        raise ValueError("无效的组播地址")

    ip, port = match.groups()

    # 转换为UDPxy格式
    # http://udpxy_host:port/udp/multicast_ip:multicast_port
    return f"{udpxy_url}/udp/{ip}:{port}"

# 示例
convert_multicast_url(
    "rtp://239.0.0.1:5000",
    "http://192.168.1.1:3680"
)
# 返回: "http://192.168.1.1:3680/udp/239.0.0.1:5000"
```

#### 6.2 流代理接口

**API端点**: `GET /api/proxy/stream/{channel_id}`

**请求参数**:
```http
GET /api/proxy/stream/123?token=abc123def456...
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|-----|------|------|------|------|
| `channel_id` | 路径 | 整数 | ✓ | 频道ID |
| `token` | 查询 | 字符串(64) | ✓ | 订阅Token |

**响应**:
- Content-Type: `video/mp2t`（或从上游获取）
- 流式数据（chunked transfer encoding）

**处理流程**:
```python
@bp.route('/stream/<int:channel_id>')
def stream(channel_id):
    # 1. 验证Token
    token = request.args.get('token')
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({'error': '无效的订阅令牌'}), 403

    # 2. 查询频道
    channel = Channel.query.get(channel_id)
    if not channel or not channel.is_active:
        return jsonify({'error': '频道不存在或已禁用'}), 404

    # 3. 获取流URL
    stream_url = channel.url

    # 4. 协议转换（如需）
    if channel.protocol in ['rtp', 'udp']:
        if not config.UDPXY_ENABLED:
            return jsonify({'error': 'UDPxy未启用'}), 400
        stream_url = convert_multicast_url(stream_url, config.UDPXY_URL)

    # 5. 记录观看历史
    watch_record = WatchHistory(
        user_id=user.id,
        channel_id=channel.id,
        start_time=datetime.now()
    )
    db.session.add(watch_record)
    db.session.commit()

    # 6. 流式转发
    def generate():
        buffer_size = config.PROXY_BUFFER_SIZE
        with requests.get(stream_url, stream=True, timeout=30) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=buffer_size):
                if chunk:
                    yield chunk

    # 7. 返回流
    return Response(
        generate(),
        mimetype='video/mp2t',
        headers={'X-Accel-Buffering': 'no'}
    )
```

#### 6.3 代理缓冲配置

**功能描述**: 配置流传输的缓冲区大小，影响吞吐量和延迟。

**配置位置**: 系统设置 → 代理配置 → 缓冲区大小

**配置项**:

| 参数 | 类型 | 范围 | 默认值 | 单位 |
|-----|------|------|--------|------|
| **缓冲区大小** | 整数 | 1024-65536 | 8192 | 字节 |

**调优建议**:

| 网络环境 | 建议值 | 说明 |
|---------|--------|------|
| **低延迟网络** | 4096-8192 | 适合局域网、光纤 |
| **普通网络** | 8192-16384 | 适合家庭宽带 |
| **高带宽网络** | 16384-32768 | 适合服务器、专线 |

**工作原理**:
```python
# 每次从上游读取buffer_size字节
chunk = upstream_stream.read(buffer_size)

# 缓冲区越大
# 优点：吞吐量越高，CPU占用越低
# 缺点：延迟越大，内存占用越高
```

#### 6.4 UDPxy配置管理

**功能描述**: 配置UDPxy服务器，实现组播到HTTP的转换。

**配置位置**: 系统设置 → UDPxy配置

**配置项**:

| 参数 | 类型 | 必填 | 说明 |
|-----|------|------|------|
| **启用UDPxy** | 开关 | ✓ | 是否启用UDPxy功能 |
| **服务器地址** | 文本 | ✗ | UDPxy服务器地址 |

**服务器地址格式**:
```
http://192.168.1.1:3680
或
http://udpxy.local:3680
```

**连接测试**:

**功能**: "检测连接"按钮

**测试流程**:
```
用户点击"检测连接"
    ↓
调用 POST /api/settings/test-udpxy
    Body: {url: "http://192.168.1.1:3680"}
    ↓
后端测试:
  1. 拼接测试URL: {url}/status
  2. 发送GET请求
  3. 检查响应状态码（200=成功）
    ↓
返回结果:
  成功: {success: true, message: "连接成功"}
  失败: {success: false, message: "连接超时"}
    ↓
前端显示测试结果
```

**使用场景**:
```
场景一：局域网组播源
- IPTV源为组播地址（rtp://或udp://）
- 局域网内有UDPxy服务器
- 需要将组播转为HTTP供外网访问

场景二：跨网段访问
- 组播源在某个VLAN
- 播放器在另一个VLAN
- 通过UDPxy实现跨网段访问
```

---

### 7. 订阅生成模块

#### 7.1 订阅链接生成

**功能描述**: 为用户生成个性化的IPTV订阅链接，供播放器使用。

**订阅类型**:

##### 类型一：M3U订阅

**文件格式**: `.m3u`

**链接格式**:
```
http://your-server.com/api/subscription/m3u?token={user_token}
```

**文件内容**:
```m3u
#EXTM3U x-tvg-url="http://epg.example.com/guide.xml"

#EXTINF:-1 tvg-id="cctv1" tvg-name="CCTV-1" tvg-logo="http://logo.url" group-title="央视频道",CCTV-1综合
http://your-server.com/api/proxy/stream/1?token=abc123

#EXTINF:-1 tvg-id="cctv2" tvg-name="CCTV-2" tvg-logo="http://logo.url" group-title="央视频道",CCTV-2财经
http://your-server.com/api/proxy/stream/2?token=abc123

#EXTINF:-1 tvg-id="btv1" tvg-name="北京卫视" tvg-logo="http://logo.url" group-title="地方台",北京卫视
http://your-server.com/api/proxy/stream/3?token=abc123
```

**元数据说明**:
- `x-tvg-url`: EPG节目单地址（如已配置）
- `tvg-id`: 频道EPG ID
- `tvg-name`: 频道名称
- `tvg-logo`: 频道Logo URL
- `group-title`: 分组名称

##### 类型二：TXT订阅

**文件格式**: `.txt`

**链接格式**:
```
http://your-server.com/api/subscription/txt?token={user_token}
```

**文件内容**:
```
央视频道,#genre#
CCTV-1综合,http://your-server.com/api/proxy/stream/1?token=abc123
CCTV-2财经,http://your-server.com/api/proxy/stream/2?token=abc123

地方台,#genre#
北京卫视,http://your-server.com/api/proxy/stream/3?token=abc123
```

**格式说明**:
- 分组行：`分组名,#genre#`
- 频道行：`频道名,流地址`

**生成规则**:
```python
def generate_subscription(user, format='m3u'):
    # 1. 查询启用的频道
    channels = Channel.query.filter_by(is_active=True)\
        .order_by(Channel.sort_order)\
        .all()

    # 2. 按分组组织
    groups = {}
    for channel in channels:
        group_name = channel.group.name if channel.group else "未分组"
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(channel)

    # 3. 生成订阅内容
    if format == 'm3u':
        return generate_m3u(groups, user.token)
    else:
        return generate_txt(groups, user.token)
```

#### 7.2 一键订阅

**功能描述**: 快速将订阅链接导入到支持的播放器。

**支持的播放器**:

| 播放器 | 格式 | 方式 | URI Scheme |
|-------|------|------|-----------|
| **VLC** | M3U | URI调用 | `vlc://` |
| **PotPlayer** | M3U | URI调用 | `potplayer://` |
| **IINA** | M3U | URI调用 | `iina://weblink?url=` |
| **nPlayer** | M3U | URI调用 | `nplayer-http://` 或 `nplayer-https://` |
| **Diyp** | TXT | 复制链接 | 手动粘贴 |
| **影视仓(mbox)** | TXT | 复制链接 | 手动粘贴 |

**实现方式**:

```javascript
// 一键订阅到VLC
function subscribeToVLC(m3uUrl) {
  const vlcUrl = `vlc://${encodeURIComponent(m3uUrl)}`
  window.location.href = vlcUrl
}

// 一键订阅到IINA
function subscribeToIINA(m3uUrl) {
  const iinaUrl = `iina://weblink?url=${encodeURIComponent(m3uUrl)}`
  window.location.href = iinaUrl
}

// 一键订阅到nPlayer
function subscribeToNPlayer(m3uUrl) {
  const protocol = m3uUrl.startsWith('https') ? 'nplayer-https' : 'nplayer-http'
  const nplayerUrl = m3uUrl.replace(/^https?/, protocol)
  window.location.href = nplayerUrl
}

// 复制链接
function copyToClipboard(url) {
  navigator.clipboard.writeText(url)
    .then(() => {
      ElMessage.success('链接已复制到剪贴板')
    })
}
```

**交互界面**:
```
订阅链接区域
┌─────────────────────────────────┐
│ M3U订阅                          │
│ ┌─────────────────────────────┐ │
│ │ http://server.com/m3u?...   │ │ 可选择文本复制
│ └─────────────────────────────┘ │
│ [VLC] [PotPlayer] [IINA] [复制] │
├─────────────────────────────────┤
│ TXT订阅                          │
│ ┌─────────────────────────────┐ │
│ │ http://server.com/txt?...   │ │
│ └─────────────────────────────┘ │
│ [Diyp] [影视仓] [复制]           │
└─────────────────────────────────┘
```

#### 7.3 Token管理

**功能描述**: 管理用户的订阅访问Token。

**Token特性**:
- 长度：64字节
- 格式：十六进制字符串（小写）
- 唯一性：每个用户一个唯一Token
- 用途：订阅认证 + 流代理认证

**Token显示**:
```
当前Token：abc123def456...（显示前后各4位，中间省略号）

[重置Token]
```

**Token重置**:

**触发**: 点击"重置Token"按钮

**流程**:
```
用户点击"重置Token"
    ↓
显示确认对话框：
  "重置Token将导致旧订阅链接失效，确定继续？"
    ↓
用户确认
    ↓
调用 POST /api/auth/reset-token
    ↓
后端：
  1. 生成新Token（64字节随机值）
  2. 更新用户记录
  3. 保存到数据库
    ↓
返回新Token
    ↓
前端更新显示
    ↓
显示提示："Token已重置，请更新播放器订阅"
```

**Token生成算法**:
```python
import secrets

def generate_token():
    """生成64字节随机Token"""
    return secrets.token_hex(32)  # 生成64个十六进制字符

# 示例输出
# "a1b2c3d4e5f6...（64个字符）"
```

---

### 8. 代理状态监控模块

#### 8.1 活跃连接监控

**功能描述**: 实时显示当前正在进行的流代理连接。

**列表字段**:

| 列名 | 宽度 | 数据类型 | 说明 |
|-----|------|---------|------|
| **用户名** | 120px | 文本 | 观看用户 |
| **频道名** | 自适应 | 文本 | 正在观看的频道 |
| **开始时间** | 180px | 日期时间 | 连接建立时间 |
| **持续时长** | 120px | 文本 | 实时计算的观看时长 |

**持续时长计算**:
```javascript
function formatDuration(startTime) {
  const now = Date.now()
  const start = new Date(startTime).getTime()
  const duration = Math.floor((now - start) / 1000)  // 秒

  const hours = Math.floor(duration / 3600)
  const minutes = Math.floor((duration % 3600) / 60)
  const seconds = duration % 60

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
}
```

**自动刷新**:
- 每10秒自动刷新一次
- 显示倒计时："下次刷新: 9秒"

**手动刷新**:
- "刷新"按钮（工具栏）
- 立即刷新并重置计时器

**空状态**:
- 无连接时显示："当前没有活跃连接"

**数据来源**:
```python
# 活跃连接字典（内存存储）
active_connections = {
    "connection_id_1": {
        "user_id": 1,
        "username": "admin",
        "channel_id": 123,
        "channel_name": "CCTV-1",
        "start_time": datetime.now()
    }
}

@bp.route('/status')
@login_required
def get_proxy_status():
    connections = list(active_connections.values())
    return jsonify({
        'active_count': len(connections),
        'connections': connections
    })
```

#### 8.2 历史连接记录

**功能描述**: 展示已完成的观看记录。

**列表字段**:

| 列名 | 宽度 | 数据类型 | 说明 |
|-----|------|---------|------|
| **用户名** | 100px | 文本 | 观看用户 |
| **频道名** | 自适应 | 文本 | 观看的频道 |
| **开始时间** | 170px | 日期时间 | 观看开始时间 |
| **结束时间** | 170px | 日期时间 | 观看结束时间 |
| **观看时长** | 130px | 文本 | 格式化的观看时长 |

**分页配置**:
```javascript
{
  currentPage: 1,
  pageSize: 20,  // 默认20条
  pageSizes: [10, 20, 50, 100],
  total: 0
}
```

**排序**:
- 按开始时间倒序（最新的在前）

**数据查询**:
```sql
SELECT
    u.username,
    c.name AS channel_name,
    w.start_time,
    w.end_time,
    w.duration
FROM watch_history w
JOIN users u ON w.user_id = u.id
JOIN channels c ON w.channel_id = c.id
WHERE w.duration > 0  -- 只显示有观看时长的记录
ORDER BY w.start_time DESC
LIMIT 20 OFFSET 0
```

**时长格式化**:
```javascript
function formatWatchDuration(seconds) {
  if (seconds < 60) {
    return '小于1分钟'
  }

  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else {
    return `${minutes}分钟`
  }
}
```

---

### 9. 系统设置模块

#### 9.1 网站基本设置

**功能描述**: 配置网站的基本信息和显示内容。

**配置项**:

| 设置项 | 类型 | 必填 | 说明 | 使用位置 |
|-------|------|------|------|---------|
| **网站名称** | 文本 | ✗ | 网站显示名称 | 浏览器标题、登录页、侧边栏 |
| **EPG URL** | 文本(URL) | ✗ | EPG节目单XML地址 | M3U订阅的x-tvg-url |

**默认值**:
- 网站名称：`IPTV Proxy Admin`
- EPG URL：空（不使用EPG）

**EPG说明**:
```
EPG（Electronic Program Guide）电子节目单

作用：
- 为播放器提供节目信息
- 显示当前播放内容
- 显示节目预告

格式：XML
示例：http://epg.example.com/guide.xml

使用：
- 配置后自动添加到M3U订阅
- 支持的播放器会自动加载节目单
```

#### 9.2 UDPxy配置

**功能描述**: 配置UDPxy代理服务，实现组播到HTTP转换。

**配置项**:

| 设置项 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| **启用UDPxy** | 开关 | ✓ | 是否启用UDPxy功能 |
| **服务器地址** | 文本 | ✗ | UDPxy服务地址（如 http://192.168.1.1:3680） |

**连接测试**:
- "检测连接"按钮
- 测试UDPxy服务器可达性
- 显示测试结果（成功/失败/超时）

**使用说明**:
```
UDPxy 是一个组播到HTTP的转换代理。

适用场景：
1. IPTV源为组播地址（RTP/UDP）
2. 需要将组播流转为HTTP供播放器使用
3. 跨网段访问组播源

部署方式：
- 独立服务器
- 与本系统部署在同一服务器
- 路由器内置（部分支持）

默认端口：3680
```

#### 9.3 代理配置

**功能描述**: 配置流代理转发的相关参数。

**配置项**:

| 设置项 | 类型 | 范围 | 默认值 | 说明 |
|-------|------|------|--------|------|
| **缓冲区大小** | 数字 | 1024-65536字节 | 8192 | 流传输缓冲区大小 |

**调优建议**:
```
低延迟网络（局域网）：4096-8192字节
普通网络（家庭宽带）：8192-16384字节
高带宽网络（服务器）：16384-32768字节

缓冲区越大：
优点：吞吐量越高，CPU占用越低
缺点：延迟越大，内存占用越高
```

#### 9.4 健康检测配置

**功能描述**: 配置频道健康检测的相关参数。

**配置项**:

| 设置项 | 类型 | 范围 | 默认值 | 说明 |
|-------|------|------|--------|------|
| **检测超时** | 数字 | 1-60秒 | 10秒 | 单个频道检测超时限制 |
| **失败重试** | 数字 | 0-5次 | 1次 | 检测失败后重试次数 |
| **检测线程数** | 数字 | 1-5线程 | 3线程 | 并发检测的线程数 |

**配置说明**:
```
检测超时：
- 值越大，对慢速频道越友好
- 值越小，检测速度越快
- 建议：5-15秒

失败重试：
- 增加检测准确性
- 但会延长检测时间
- 建议：1-2次

检测线程数：
- 值越大，检测速度越快
- 但会增加系统负载
- 建议：3-5线程
```

#### 9.5 账户管理

**功能描述**: 修改当前用户的账户信息。

**用户名修改**:

**表单**:
```
┌────────────────────────────┐
│ 当前用户名: admin          │
│                            │
│ 新用户名: [___________]    │
│                            │
│         [修改用户名]       │
└────────────────────────────┘
```

**验证规则**:
- 长度：3-80字符
- 唯一性：不能与其他用户重复
- 字符：建议字母、数字、下划线

**密码修改**:

**表单**:
```
┌────────────────────────────┐
│ 原密码: [___________]      │
│                            │
│ 新密码: [___________]      │
│                            │
│ 确认密码: [___________]    │
│                            │
│         [修改密码]         │
└────────────────────────────┘
```

**验证规则**:
- 原密码必须正确
- 新密码长度：6-128字符
- 新密码与确认密码必须一致
- 建议使用强密码（大小写+数字+特殊字符）

**修改流程**:
```
用户填写表单
    ↓
前端验证
    ↓
提交到 POST /api/auth/change-password
    ↓
后端验证原密码
    ↓
成功：
  1. 更新密码哈希
  2. 保存到数据库
  3. 返回成功
  4. 前端显示："密码修改成功"
失败：
  返回错误："原密码不正确"
```

#### 9.6 观看历史管理

**功能描述**: 管理观看历史数据。

**保留策略配置**:

**选项**:
- ⏱️ 7天
- ⏱️ 14天
- ⏱️ 30天（默认）

**说明**:
```
保留策略用于自动清理旧数据。
系统会定期删除超过保留天数的历史记录。

注意：
- 仅影响自动清理
- 不会立即删除现有数据
- 手动清空不受此限制
```

**历史统计**:

**显示内容**:
```
┌─────────────────────────────┐
│ 📊 观看历史统计             │
│                             │
│ 总记录数: 1,250条           │
│ 最早记录: 2026-01-15        │
│ 最新记录: 2026-01-30        │
│                             │
│        [刷新统计]           │
└─────────────────────────────┘
```

**数据清理**:

**功能**: "清空全部数据"按钮（红色，危险操作）

**流程**:
```
用户点击"清空全部数据"
    ↓
显示确认对话框：
  "⚠️ 警告
   此操作将删除所有观看历史记录（共1,250条）
   此操作不可恢复，确定继续？"
  选项：[取消] [确定删除]
    ↓
用户确认删除
    ↓
调用 POST /api/history/cleanup
    ↓
后端删除所有记录
    ↓
返回结果：{deleted_count: 1250}
    ↓
前端显示："成功清空1,250条观看历史记录"
    ↓
刷新统计
```

---

### 10. 主布局与导航

#### 10.1 侧边栏导航

**功能描述**: 应用主要功能的导航菜单。

**布局结构**:
```
┌──────────────────┐
│ 📺 网站Logo+名称  │ ← Logo区域
├──────────────────┤
│ 📊 仪表盘         │ ← 导航菜单
│ 📺 频道管理       │
│ 📁 分组管理       │
│ 📡 代理状态       │
│ 🔗 订阅链接       │
│ ⚙️ 系统设置       │
├──────────────────┤
│ 「  (折叠按钮)    │ ← 底部工具
└──────────────────┘
```

**菜单项**:

| 图标 | 名称 | 路径 | 说明 |
|-----|------|------|------|
| 📊 | 仪表盘 | `/` | 系统概览和统计 |
| 📺 | 频道管理 | `/channels` | 频道CRUD、导入导出 |
| 📁 | 分组管理 | `/groups` | 分组管理 |
| 📡 | 代理状态 | `/proxy-status` | 活跃连接和历史记录 |
| 🔗 | 订阅链接 | `/subscription` | 订阅生成和管理 |
| ⚙️ | 系统设置 | `/settings` | 系统配置 |

**交互特性**:
- 当前页面高亮显示
- 鼠标悬停效果
- 支持键盘导航

**折叠功能**:
- 桌面：手动折叠（点击「按钮）
- 手机：自动折叠为抽屉式
- 折叠后只显示图标

**响应式适配**:
```
桌面（≥768px）:
- 侧边栏固定显示
- 宽度：220px（展开）/ 64px（折叠）

手机（<768px）:
- 侧边栏自动折叠
- 点击汉堡菜单展开
- 覆盖式抽屉
```

#### 10.2 顶部工具栏

**功能描述**: 显示用户信息和全局操作。

**布局结构**:
```
┌──────────────────────────────────────────┐
│                   [🌙主题] [👤 admin ▾]    │
└──────────────────────────────────────────┘
```

**组件**（右侧）:

1. **主题切换按钮**
   - 图标：☀️（浅色）/ 🌙（深色）
   - 下拉菜单：
     - ☀️ 浅色
     - 🌙 深色
     - 💻 跟随系统

2. **用户信息下拉**
   - 显示：头像图标 + 用户名
   - 下拉菜单：
     - 👋 退出登录

**用户菜单交互**:
```
用户点击用户名
    ↓
显示下拉菜单
    ↓
选择"退出登录"
    ↓
调用 POST /api/auth/logout
    ↓
清除Session
    ↓
跳转到登录页
```

---

## 非功能需求

### 1. 性能要求

#### 1.1 响应时间

| 操作类型 | 目标 | 说明 |
|---------|------|------|
| **页面首次加载** | < 2秒 | 包含资源下载和渲染 |
| **页面切换** | < 500ms | SPA路由切换 |
| **API响应** | < 500ms | 常规查询操作（P95） |
| **搜索筛选** | < 300ms | 前端防抖后的响应 |
| **健康检测单个** | < 15秒 | 单个频道检测（含超时） |
| **健康检测全部** | < 60秒 | 100个频道并发检测 |

#### 1.2 并发能力

| 指标 | 目标 | 说明 |
|------|------|------|
| **并发用户** | 50+ | 同时在线用户数 |
| **并发流** | 50+ | 同时代理的流数量 |
| **数据库连接** | 20+ | 连接池大小 |
| **健康检测并发** | 3-5线程 | 可配置 |

#### 1.3 吞吐量

| 指标 | 目标 | 说明 |
|------|------|------|
| **流代理带宽** | 100Mbps+ | 单服务器总带宽 |
| **单流带宽** | 10Mbps | 典型IPTV流 |
| **API QPS** | 100+ | 每秒查询数 |

### 2. 可靠性要求

#### 2.1 可用性

- **目标**: 99.9%（生产环境）
- **允许停机**: 8.76小时/年
- **故障恢复**: < 5分钟

#### 2.2 数据持久化

| 数据类型 | 存储方式 | 备份策略 |
|---------|---------|---------|
| **用户数据** | 数据库 | 每日备份 |
| **频道配置** | 数据库 | 每日备份 |
| **观看历史** | 数据库 | 每周备份 |
| **系统设置** | 数据库 | 实时同步 |

#### 2.3 容错能力

| 场景 | 处理方式 |
|------|---------|
| **频道检测失败** | 自动重试，标记为不可用 |
| **上游流断开** | 记录日志，通知前端 |
| **数据库连接失败** | 重连机制，最多重试3次 |
| **网络超时** | 合理超时设置，友好错误提示 |

### 3. 安全要求

#### 3.1 认证与授权

- **认证方式**: Session-based（Cookie）
- **密码存储**: bcrypt加密（工作因子≥12）
- **Token安全**: 64字节随机Token
- **会话超时**: 24小时（可配置）

#### 3.2 数据安全

| 保护措施 | 说明 |
|---------|------|
| **SQL注入防护** | 使用ORM，参数化查询 |
| **XSS防护** | Vue自动转义，CSP策略 |
| **CSRF防护** | Flask内置Token验证 |
| **敏感信息** | 密码、Token不记录到日志 |

#### 3.3 通信安全

- **HTTPS**: 生产环境强制使用
- **TLS版本**: 1.2+
- **安全Headers**: HSTS、X-Frame-Options等

### 4. 可扩展性

#### 4.1 水平扩展

- **无状态设计**: API服务器可水平扩展
- **负载均衡**: 支持Nginx/HAProxy负载均衡
- **共享存储**: Session存储可迁移到Redis

#### 4.2 垂直扩展

| 资源类型 | 扩展方式 |
|---------|---------|
| **CPU** | 增加核心数提升并发能力 |
| **内存** | 增加内存支持更多连接 |
| **磁盘** | 扩容数据库存储空间 |
| **网络** | 升级带宽支持更多流 |

### 5. 兼容性

#### 5.1 浏览器兼容

| 浏览器 | 版本要求 | 备注 |
|-------|---------|------|
| **Chrome** | 90+ | 推荐使用 |
| **Firefox** | 88+ | 完全支持 |
| **Safari** | 14+ | macOS/iOS |
| **Edge** | 90+ | Chromium内核 |

#### 5.2 播放器兼容

| 播放器 | 格式 | 兼容性 |
|-------|------|--------|
| **VLC** | M3U | ✓ 完全兼容 |
| **PotPlayer** | M3U | ✓ 完全兼容 |
| **IINA** | M3U | ✓ 完全兼容 |
| **nPlayer** | M3U | ✓ 完全兼容 |
| **TiviMate** | M3U | ✓ 完全兼容 |
| **IPTV Pro** | M3U | ✓ 完全兼容 |
| **Diyp** | TXT | ✓ 完全兼容 |
| **影视仓** | TXT | ✓ 完全兼容 |

#### 5.3 操作系统兼容

| 系统 | 版本 | 部署方式 |
|-----|------|---------|
| **Ubuntu** | 18.04+ | 推荐 |
| **CentOS** | 7+ | 支持 |
| **Windows Server** | 2016+ | 支持 |
| **Docker** | 任何平台 | 推荐 |

### 6. 可维护性

#### 6.1 代码质量

- **代码规范**: PEP 8（Python）、ESLint（JavaScript）
- **注释**: 关键逻辑必须注释
- **命名**: 语义化命名，避免缩写
- **模块化**: 清晰的目录结构

#### 6.2 日志管理

| 日志类型 | 级别 | 内容 |
|---------|------|------|
| **访问日志** | INFO | 请求路径、响应时间 |
| **应用日志** | INFO | 业务操作记录 |
| **错误日志** | ERROR | 异常堆栈、错误详情 |
| **调试日志** | DEBUG | 开发调试信息 |

**日志轮转**:
- 文件大小：10MB
- 保留天数：30天（普通）/ 90天（错误）

#### 6.3 监控能力

| 监控指标 | 说明 |
|---------|------|
| **系统资源** | CPU、内存、磁盘、网络 |
| **应用性能** | 响应时间、错误率、QPS |
| **业务指标** | 活跃用户、流量、频道状态 |

---

## 用户角色与权限

### 1. 角色定义

#### 管理员（Admin）

**角色描述**: 系统的超级用户，拥有所有管理权限。

**使用场景**:
- 系统管理员
- IPTV服务运维人员
- 内容管理员

**权限列表**:

| 功能模块 | 权限 |
|---------|------|
| **认证** | 登录、登出 |
| **仪表盘** | 查看所有统计数据 |
| **频道管理** | 增删改查、导入导出、健康检测 |
| **分组管理** | 增删改查、排序 |
| **代理状态** | 查看活跃连接、查看历史记录 |
| **订阅管理** | 查看订阅链接、重置Token |
| **系统设置** | 修改所有系统配置 |
| **账户管理** | 修改用户名、修改密码 |
| **数据管理** | 清空观看历史 |

**账户信息**:
- 默认用户名：`admin`
- 默认密码：`admin123`（首次登录后建议修改）

### 2. 权限矩阵

| 功能 | 管理员 | 认证要求 | API端点 |
|-----|-------|---------|---------|
| **登录** | ✓ | 否 | POST /api/auth/login |
| **登出** | ✓ | 是 | POST /api/auth/logout |
| **查看仪表盘** | ✓ | 是 | GET /api/dashboard |
| **频道列表** | ✓ | 是 | GET /api/channels |
| **添加频道** | ✓ | 是 | POST /api/channels |
| **编辑频道** | ✓ | 是 | PUT /api/channels/{id} |
| **删除频道** | ✓ | 是 | DELETE /api/channels/{id} |
| **导入频道** | ✓ | 是 | POST /api/import-export/import |
| **导出频道** | ✓ | 是 | GET /api/import-export/export |
| **分组管理** | ✓ | 是 | /api/groups/* |
| **健康检测** | ✓ | 是 | POST /api/health/check-all |
| **流代理** | ✓ | 需Token | GET /api/proxy/stream/{id} |
| **订阅生成** | ✓ | 需Token | GET /api/subscription/* |
| **代理状态** | ✓ | 是 | GET /api/proxy/status |
| **系统设置** | ✓ | 是 | GET/POST /api/settings |

**权限说明**:
- ✓ = 拥有权限
- 认证要求 = 需要登录Session
- 需Token = 需要有效的订阅Token

---

## 数据模型

### 1. 实体关系图（ERD）

```
┌─────────────┐
│   users     │
│─────────────│
│ id (PK)     │───┐
│ username    │   │
│ password    │   │ 1
│ token       │   │
│ created_at  │   │
└─────────────┘   │
                  │
                  │ n
      ┌───────────▼────────────┐
      │   watch_history        │
      │────────────────────────│
      │ id (PK)                │
      │ user_id (FK)           │
      │ channel_id (FK)  ──────┼───┐
      │ start_time             │   │
      │ end_time               │   │ n
      │ duration               │   │
      │ watch_date (INDEX)     │   │
      └────────────────────────┘   │
                                   │
                                   │ 1
                       ┌───────────▼──────────┐
                       │  channels            │
                       │──────────────────────│
                       │ id (PK)              │
                       │ name                 │
                       │ url                  │
                       │ logo                 │
                       │ group_id (FK)  ──────┼───┐
                       │ sort_order           │   │
                       │ is_active            │   │ n
                       │ protocol             │   │
                       │ tvg_id               │   │
                       │ is_healthy           │   │
                       │ last_check           │   │
                       │ created_at           │   │
                       │ updated_at           │   │
                       └──────────────────────┘   │
                                                  │
                                                  │ 1
                                  ┌───────────────▼─────────┐
                                  │  channel_groups         │
                                  │─────────────────────────│
                                  │ id (PK)                 │
                                  │ name                    │
                                  │ sort_order              │
                                  │ created_at              │
                                  └─────────────────────────┘

                    ┌──────────────┐
                    │  settings    │
                    │──────────────│
                    │ id (PK)      │
                    │ key (UNIQUE) │
                    │ value (TEXT) │
                    └──────────────┘
```

### 2. 数据字典

#### 2.1 users（用户表）

**表名**: `users`

**说明**: 存储用户账户信息和订阅Token。

| 字段名 | 数据类型 | 长度 | 约束 | 默认值 | 说明 |
|-------|---------|------|------|--------|------|
| `id` | Integer | - | PK, AUTO_INCREMENT | - | 用户ID |
| `username` | String | 80 | NOT NULL, UNIQUE | - | 用户名，登录凭证 |
| `password_hash` | String | 256 | NOT NULL | - | 密码哈希（bcrypt） |
| `token` | String | 64 | UNIQUE | NULL | 订阅Token（64字节十六进制） |
| `created_at` | DateTime | - | NOT NULL | CURRENT_TIMESTAMP | 账户创建时间 |

**索引**:
- PRIMARY KEY: `id`
- UNIQUE INDEX: `username`
- UNIQUE INDEX: `token`

**业务规则**:
- 用户名唯一，建议3-80字符
- 密码使用bcrypt加密存储
- Token用于订阅和流代理认证
- 默认创建admin账户

#### 2.2 channel_groups（分组表）

**表名**: `channel_groups`

**说明**: 频道分组，用于组织和分类频道。

| 字段名 | 数据类型 | 长度 | 约束 | 默认值 | 说明 |
|-------|---------|------|------|--------|------|
| `id` | Integer | - | PK, AUTO_INCREMENT | - | 分组ID |
| `name` | String | 100 | NOT NULL | - | 分组名称 |
| `sort_order` | Integer | - | NOT NULL | 0 | 排序值（越小越靠前） |
| `created_at` | DateTime | - | NOT NULL | CURRENT_TIMESTAMP | 创建时间 |

**索引**:
- PRIMARY KEY: `id`

**业务规则**:
- 分组名称不限制唯一性（允许同名分组）
- 按sort_order升序排列
- 删除分组不影响频道（频道的group_id设为NULL）

#### 2.3 channels（频道表）

**表名**: `channels`

**说明**: IPTV频道信息，包含流地址、元数据和健康状态。

| 字段名 | 数据类型 | 长度 | 约束 | 默认值 | 说明 |
|-------|---------|------|------|--------|------|
| `id` | Integer | - | PK, AUTO_INCREMENT | - | 频道ID |
| `name` | String | 200 | NOT NULL | - | 频道名称 |
| `url` | String | 500 | NOT NULL | - | 直播流地址 |
| `logo` | String | 500 | | NULL | Logo图片URL |
| `group_id` | Integer | - | FK | NULL | 所属分组ID |
| `sort_order` | Integer | - | NOT NULL | 0 | 排序值 |
| `is_active` | Boolean | - | NOT NULL | TRUE | 是否启用 |
| `protocol` | String | 20 | NOT NULL | 'http' | 协议类型 |
| `tvg_id` | String | 100 | | NULL | EPG节目单ID |
| `last_check` | DateTime | - | | NULL | 最后检测时间 |
| `is_healthy` | Boolean | - | NOT NULL | TRUE | 健康状态 |
| `created_at` | DateTime | - | NOT NULL | CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | DateTime | - | NOT NULL | CURRENT_TIMESTAMP | 更新时间 |

**索引**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `group_id` → `channel_groups(id)`
- INDEX: `protocol`
- INDEX: `is_active`
- INDEX: `is_healthy`

**枚举值**:
- `protocol`: 'http', 'https', 'rtp', 'udp'

**业务规则**:
- URL必须以协议开头（http://, https://, rtp://, udp://）
- protocol字段自动从URL提取
- is_active控制频道是否启用（订阅和代理）
- is_healthy由健康检测更新

#### 2.4 watch_history（观看历史表）

**表名**: `watch_history`

**说明**: 记录用户的观看历史，用于统计分析。

| 字段名 | 数据类型 | 长度 | 约束 | 默认值 | 说明 |
|-------|---------|------|------|--------|------|
| `id` | Integer | - | PK, AUTO_INCREMENT | - | 记录ID |
| `user_id` | Integer | - | FK, NOT NULL | - | 用户ID |
| `channel_id` | Integer | - | FK, NOT NULL | - | 频道ID |
| `start_time` | DateTime | - | NOT NULL | - | 开始观看时间 |
| `end_time` | DateTime | - | | NULL | 结束观看时间 |
| `duration` | Integer | - | NOT NULL | 0 | 观看时长（秒） |
| `watch_date` | Date | - | NOT NULL | - | 观看日期（用于统计） |

**索引**:
- PRIMARY KEY: `id`
- FOREIGN KEY: `user_id` → `users(id)`
- FOREIGN KEY: `channel_id` → `channels(id)`
- INDEX: `watch_date`
- INDEX: `(user_id, watch_date)` （组合索引）
- INDEX: `(channel_id, watch_date)` （组合索引）

**业务规则**:
- 连接建立时创建记录
- 每60秒更新一次duration
- 连接断开时更新end_time
- 只显示duration > 0的记录
- watch_date从start_time提取

#### 2.5 settings（系统设置表）

**表名**: `settings`

**说明**: 键值对形式存储系统配置，支持Web界面配置。

| 字段名 | 数据类型 | 长度 | 约束 | 默认值 | 说明 |
|-------|---------|------|------|--------|------|
| `id` | Integer | - | PK, AUTO_INCREMENT | - | 设置ID |
| `key` | String | 100 | NOT NULL, UNIQUE | - | 配置键名 |
| `value` | Text | - | | NULL | 配置值（JSON或文本） |

**索引**:
- PRIMARY KEY: `id`
- UNIQUE INDEX: `key`

**预定义配置键**:

| 配置键 | 说明 | 数据类型 | 示例值 | Web配置 |
|-------|------|---------|--------|---------|
| `epg_url` | EPG节目单地址 | String | `http://epg.example.com` | ✗ |
| `site_name` | 网站名称 | String | `IPTV Proxy Admin` | ✓ |
| `proxy_buffer_size` | 代理缓冲区大小 | Integer | `8192` | ✓ |
| `health_check_timeout` | 检测超时时间 | Integer | `10` | ✓ |
| `health_check_max_retries` | 检测重试次数 | Integer | `1` | ✓ |
| `health_check_threads` | 检测线程数 | Integer | `3` | ✓ |
| `udpxy_enabled` | 启用UDPxy | Boolean | `false` | ✓ |
| `udpxy_url` | UDPxy服务地址 | String | `http://localhost:3680` | ✓ |

**业务规则**:
- Web界面配置的值优先于环境变量
- 配置立即生效，无需重启（部分配置）
- 布尔值存储为字符串（'true'/'false'）

---

## 界面设计要求

### 1. 设计语言

#### 1.1 UI框架

**前端UI库**: Element Plus

**设计规范**: Material Design

**特点**:
- 现代化、扁平化设计
- 丰富的组件库
- 完善的交互动画
- 响应式布局支持

#### 1.2 配色方案

**浅色主题**:
```css
--bg-primary: #F9FAFB
--bg-secondary: #FFFFFF
--text-primary: #1F2937
--text-secondary: #6B7280
--accent-primary: #3B82F6
--border-color: #E5E7EB
```

**深色主题**:
```css
--bg-primary: #111827
--bg-secondary: #1F2937
--text-primary: #F9FAFB
--text-secondary: #9CA3AF
--accent-primary: #60A5FA
--border-color: #374151
```

#### 1.3 图标系统

**来源**: Element Plus Icons

**使用**:
- 菜单图标：Emoji（📊、📺、📁等）
- 操作图标：Element Icons
- 状态图标：彩色圆点

### 2. 布局结构

#### 2.1 整体布局

```
┌─────────────────────────────────────────┐
│          顶部工具栏 (60px)               │
├──────────┬──────────────────────────────┤
│          │                              │
│ 侧边栏   │     主内容区域               │
│ (220px)  │     (max-width: 1400px)      │
│          │                              │
│          │                              │
└──────────┴──────────────────────────────┘
```

**桌面布局（≥768px）**:
- 侧边栏固定在左侧（220px）
- 可手动折叠为64px
- 主内容区自适应

**移动布局（<768px）**:
- 侧边栏自动折叠
- 汉堡菜单触发抽屉式侧边栏
- 主内容区全宽

#### 2.2 页面布局模式

**卡片布局**:
```
用于：仪表盘、设置页

┌──────────────────────────────────┐
│  卡片标题                         │
├──────────────────────────────────┤
│  卡片内容                         │
│                                  │
└──────────────────────────────────┘
```

**表格布局**:
```
用于：频道列表、历史记录

┌──────────────────────────────────┐
│  工具栏（筛选、搜索、操作按钮）    │
├──────────────────────────────────┤
│  数据表格                         │
│  │ 列1 │ 列2 │ 列3 │ 操作 │      │
│  ├─────┼─────┼─────┼──────┤      │
│  │     │     │     │ 编辑 │      │
├──────────────────────────────────┤
│  分页器                           │
└──────────────────────────────────┘
```

**网格布局**:
```
用于：分组管理

┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐
│卡片1│ │卡片2│ │卡片3│ │卡片4│
└─────┘ └─────┘ └─────┘ └─────┘
```

### 3. 组件设计

#### 3.1 按钮

**主要按钮**:
```
[主操作按钮]  (蓝色实心)
用于：保存、提交、确认
```

**次要按钮**:
```
[次要操作]  (白色边框)
用于：取消、返回
```

**危险按钮**:
```
[删除操作]  (红色实心)
用于：删除、清空
```

**文字按钮**:
```
[文字链接]  (无边框)
用于：次要链接
```

#### 3.2 表单

**输入框**:
- 高度：40px
- 圆角：4px
- 边框：1px solid
- 焦点：蓝色边框

**下拉选择**:
- 与输入框一致的样式
- 下拉面板支持搜索

**开关**:
- Element Plus Switch组件
- 蓝色激活状态

**数字输入**:
- 带加减按钮
- 支持键盘输入

#### 3.3 表格

**行高**: 48px

**斑马纹**: 奇偶行背景色不同

**行悬停**: 背景色高亮

**固定列**: 支持列固定

**排序**: 支持列排序

#### 3.4 对话框

**尺寸**:
- 小：400px
- 中：600px
- 大：800px

**位置**: 居中显示

**遮罩**: 半透明黑色

**动画**: 缩放淡入

### 4. 响应式设计

#### 4.1 断点定义

| 断点 | 最小宽度 | 设备 | 布局特征 |
|-----|---------|------|---------|
| **xs** | <768px | 手机 | 单列，侧边栏折叠 |
| **sm** | 768px | 平板 | 两列，侧边栏可折叠 |
| **md** | 1024px | 笔记本 | 多列，侧边栏固定 |
| **lg** | 1280px | 桌面 | 多列，宽松间距 |
| **xl** | 1536px | 大屏 | 最大宽度限制 |

#### 4.2 适配策略

**内容优先级**:
1. 核心功能按钮
2. 主要信息展示
3. 辅助信息和图表

**隐藏策略**:
- 手机：隐藏次要信息、折叠侧边栏
- 平板：显示部分辅助信息
- 桌面：显示全部信息

### 5. 动画与交互

#### 5.1 过渡动画

| 场景 | 动画类型 | 时长 |
|-----|---------|------|
| **页面切换** | 淡入淡出 | 300ms |
| **对话框** | 缩放淡入 | 200ms |
| **列表项** | 滑入 | 150ms |
| **加载状态** | 旋转 | 持续 |

#### 5.2 悬停效果

- **卡片**: 轻微阴影增强
- **按钮**: 背景色加深
- **表格行**: 背景色高亮
- **链接**: 颜色变化

### 6. 主题系统

**支持的主题**:
1. ☀️ 浅色主题
2. 🌙 深色主题
3. 💻 跟随系统

**切换方式**:
- 右上角下拉菜单
- 选择保存到localStorage
- 立即应用，无需刷新

**实现方式**:
```javascript
// 使用CSS Variables
document.documentElement.classList.add('dark')

// CSS定义
:root {
  --bg-primary: #F9FAFB;
}

.dark {
  --bg-primary: #111827;
}
```

---

## 技术架构

### 1. 技术选型

#### 1.1 前端技术栈

**核心框架**:
- **Vue 3.4+** - 渐进式JavaScript框架
  - 组合式API（Composition API）
  - 响应式系统
  - 虚拟DOM

**构建工具**:
- **Vite 5.0+** - 下一代前端构建工具
  - 快速冷启动
  - 即时模块热更新（HMR）
  - 优化的生产构建

**UI组件库**:
- **Element Plus 2.4+** - Vue 3组件库
  - 丰富的组件
  - TypeScript支持
  - 主题定制

**状态管理**:
- **Pinia 2.1+** - Vue官方状态管理库
  - 类型安全
  - DevTools支持
  - 轻量级

**路由**:
- **Vue Router 4.2+** - Vue官方路由
  - 声明式路由
  - 动态路由匹配
  - 导航守卫

**HTTP通信**:
- **Axios 1.6+** - Promise-based HTTP客户端
  - 请求/响应拦截器
  - 自动转换JSON
  - 请求取消

**工具库**:
- **dayjs** - 日期处理
- **echarts** - 数据可视化（可选）

#### 1.2 后端技术栈

**Web框架**:
- **Flask 3.0+** - 轻量级Python Web框架
  - 简单灵活
  - 丰富的扩展
  - WSGI标准

**扩展库**:
- **Flask-SQLAlchemy 3.1+** - ORM框架
- **Flask-Login** - 用户会话管理
- **Flask-CORS** - 跨域资源共享（开发环境）

**数据库**:
- **SQLite 3** - 嵌入式数据库（默认）
  - 无需部署
  - 文件存储
  - 适合中小规模

- **MySQL 5.7+** - 关系型数据库（可选）
  - 高性能
  - 成熟稳定
  - 适合大规模

**ORM**:
- **SQLAlchemy 2.0+** - Python SQL工具包
  - 对象关系映射
  - 查询构建器
  - 数据库抽象

**任务调度**:
- **APScheduler 3.10+** - 定时任务框架
  - 后台任务
  - Cron表达式
  - 多种触发器

**日志**:
- **Loguru 0.7+** - 现代化日志库
  - 简单易用
  - 自动轮转
  - 彩色输出

**HTTP库**:
- **Requests 2.31+** - HTTP请求库
  - 简洁API
  - 流式响应
  - Session支持

**其他**:
- **python-dotenv** - 环境变量管理
- **Werkzeug** - WSGI工具库（密码哈希）

### 2. 架构设计

#### 2.1 前端架构

**目录结构**:
```
frontend/
├── public/              # 静态资源
│   └── favicon.ico
├── src/
│   ├── api/            # API接口定义
│   │   └── index.js
│   ├── assets/         # 资源文件
│   ├── components/     # 通用组件
│   ├── layouts/        # 布局组件
│   │   └── MainLayout.vue
│   ├── router/         # 路由配置
│   │   └── index.js
│   ├── stores/         # Pinia状态管理
│   │   ├── auth.js
│   │   ├── theme.js
│   │   └── site.js
│   ├── styles/         # 全局样式
│   ├── utils/          # 工具函数
│   ├── views/          # 页面组件
│   │   ├── Dashboard.vue
│   │   ├── Channels.vue
│   │   ├── Groups.vue
│   │   ├── ProxyStatus.vue
│   │   ├── Subscription.vue
│   │   ├── Settings.vue
│   │   └── Login.vue
│   ├── App.vue         # 根组件
│   └── main.js         # 入口文件
├── index.html          # HTML模板
├── package.json        # 依赖配置
└── vite.config.js      # Vite配置
```

**组件化设计**:
- **页面组件**（views/）：路由级别组件
- **布局组件**（layouts/）：页面布局模板
- **通用组件**（components/）：可复用组件

**状态管理**:
- **authStore**: 用户认证状态
- **themeStore**: 主题配置
- **siteStore**: 站点信息

#### 2.2 后端架构

**目录结构**:
```
backend/
├── app/
│   ├── __init__.py          # 应用工厂
│   ├── config.py            # 配置管理
│   ├── api/                 # API蓝图
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── channels.py
│   │   ├── groups.py
│   │   ├── dashboard.py
│   │   ├── health.py
│   │   ├── proxy.py
│   │   ├── subscription.py
│   │   ├── settings.py
│   │   ├── history.py
│   │   └── import_export.py
│   ├── models/              # 数据模型
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── channel.py
│   │   ├── channel_group.py
│   │   ├── watch_history.py
│   │   └── settings.py
│   └── services/            # 业务逻辑
│       ├── __init__.py
│       ├── health_checker.py
│       ├── import_export.py
│       └── watch_history_saver.py
├── data/                    # 数据目录（SQLite）
├── logs/                    # 日志目录
├── .env.example             # 环境变量模板
├── requirements.txt         # Python依赖
├── run.py                   # 应用入口
└── gunicorn.conf.py         # Gunicorn配置
```

**分层设计**:
1. **API层**（api/）：处理HTTP请求
2. **业务逻辑层**（services/）：核心业务逻辑
3. **数据访问层**（models/）：ORM模型

**蓝图组织**:
- 每个功能模块一个蓝图
- 统一的URL前缀：`/api`
- 清晰的职责划分

### 3. 数据库设计

**支持的数据库**:

| 数据库 | 场景 | 优势 | 劣势 |
|-------|------|------|------|
| **SQLite** | 开发、小规模 | 无需部署、零配置 | 并发能力弱 |
| **MySQL** | 生产、大规模 | 高性能、高并发 | 需要部署维护 |

**切换方式**:
```python
# 配置环境变量
DATABASE_TYPE=mysql
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=iptv_user
MYSQL_PASSWORD=password
MYSQL_DB=iptv

# SQLAlchemy自动适配
```

### 4. API设计

#### 4.1 RESTful规范

**HTTP方法**:
- `GET` - 查询资源
- `POST` - 创建资源
- `PUT` - 更新资源
- `DELETE` - 删除资源

**URL设计**:
```
/api/channels          GET: 列表, POST: 创建
/api/channels/{id}     GET: 详情, PUT: 更新, DELETE: 删除
/api/channels/batch-delete  POST: 批量删除
```

**状态码**:
- `200` - 成功
- `201` - 创建成功
- `400` - 请求错误
- `401` - 未认证
- `403` - 禁止访问
- `404` - 资源不存在
- `500` - 服务器错误

#### 4.2 响应格式

**成功响应**:
```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "name": "频道名"
  }
}
```

**分页响应**:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "per_page": 50,
  "pages": 2
}
```

**错误响应**:
```json
{
  "code": 400,
  "error": "错误描述",
  "message": "详细错误信息"
}
```

### 5. 部署架构

#### 5.1 开发环境

```
┌─────────────────┐
│  开发机          │
│                 │
│  ┌───────────┐  │
│  │ Frontend  │  │  Vite Dev Server
│  │ :5173     │  │  Hot Reload
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ Backend   │  │  Flask Dev Server
│  │ :5000     │  │  Hot Reload
│  └───────────┘  │
│                 │
│  ┌───────────┐  │
│  │ SQLite    │  │  data/iptv.db
│  └───────────┘  │
└─────────────────┘
```

#### 5.2 生产环境

```
┌──────────────────────────────────────┐
│         Nginx (反向代理)              │
│    :80 (HTTP) / :443 (HTTPS)         │
└────────────┬─────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
    ▼                 ▼
┌─────────┐      ┌─────────┐
│Frontend │      │Backend  │
│(静态)   │      │(Gunicorn)│
│dist/    │      │:5000    │
└─────────┘      └────┬────┘
                      │
              ┌───────┴──────┐
              │              │
              ▼              ▼
          ┌────────┐    ┌────────┐
          │ MySQL  │    │ Redis  │
          │ :3306  │    │ :6379  │
          └────────┘    └────────┘
                        (可选缓存)
```

#### 5.3 Docker部署

**架构**:
```
┌──────────────────────────┐
│   Docker Compose         │
│                          │
│  ┌────────────────────┐  │
│  │ frontend container │  │
│  │ (Nginx)            │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │ backend container  │  │
│  │ (Gunicorn + Flask) │  │
│  └────────────────────┘  │
│                          │
│  ┌────────────────────┐  │
│  │ mysql container    │  │
│  │ (可选)             │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

**优势**:
- 一键部署
- 环境隔离
- 易于迁移
- 版本管理

---

## 总结

IPTV Proxy Admin 是一个功能完整、架构清晰、易于部署的 IPTV 管理系统。

### 核心功能

1. ✅ **完整的频道管理** - 增删改查、导入导出、批量操作
2. ✅ **智能健康检测** - 自动检测、手动触发、定时任务、并发优化
3. ✅ **灵活的流代理** - 多协议支持、UDPxy转换、缓冲配置
4. ✅ **实时订阅生成** - M3U/TXT格式、EPG支持、一键订阅
5. ✅ **可视化监控** - 仪表盘统计、图表展示、实时连接
6. ✅ **灵活配置** - Web界面配置、实时生效、环境变量支持
7. ✅ **观看统计** - 历史记录、热度排行、时长统计

### 技术特点

- 🎨 **现代化UI** - Vue 3 + Element Plus，响应式设计
- 🚀 **高性能** - 并发检测、流式传输、数据库优化
- 🔒 **安全可靠** - Session认证、密码加密、Token验证
- 📦 **易于部署** - SQLite/MySQL，Docker支持，零依赖启动
- 🔧 **灵活扩展** - 模块化设计，清晰的架构，易于维护

### 适用场景

- ✓ 个人IPTV频道管理
- ✓ 家庭影音服务器
- ✓ 小型IPTV服务提供商
- ✓ 局域网流媒体代理
- ✓ IPTV源集中管理平台

---

**文档版本**: v1.0
**最后更新**: 2026-01-30
**维护者**: 开发团队
