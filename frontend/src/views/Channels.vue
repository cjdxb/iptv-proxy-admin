<template>
  <div class="channels-page">
    <div class="page-header">
      <div class="header-left">
        <h1>📺 频道管理</h1>
        <p>管理 IPTV 频道源</p>
      </div>
      <div class="header-actions">
        <el-button @click="showImportDialog = true">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
        <el-button @click="handleExport">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button type="primary" @click="openChannelDialog()">
          <el-icon><Plus /></el-icon>
          添加频道
        </el-button>
      </div>
    </div>
    
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="filter-row">
        <el-input
          v-model="filters.search"
          placeholder="搜索频道..."
          :prefix-icon="Search"
          clearable
          class="search-input"
          @input="debouncedSearch"
        />
        <el-button @click="runHealthCheck" :loading="healthCheckLoading">
          <el-icon><Refresh /></el-icon>
          检测全部频道
        </el-button>
      </div>
      <div class="filter-row">
        <el-select v-model="filters.groupId" placeholder="分组" clearable @change="fetchChannels" class="filter-select">
          <el-option label="全部分组" :value="''" />
          <el-option
            v-for="group in groups"
            :key="group.id"
            :label="group.name"
            :value="group.id"
          />
        </el-select>
        <el-select v-model="filters.protocol" placeholder="协议" clearable @change="fetchChannels" class="filter-select">
          <el-option label="全部协议" :value="''" />
          <el-option label="HTTP" value="http" />
          <el-option label="HTTPS" value="https" />
          <el-option label="RTP" value="rtp" />
          <el-option label="UDP" value="udp" />
        </el-select>
        <el-select v-model="filters.isActive" placeholder="启用状态" clearable @change="fetchChannels" class="filter-select">
          <el-option label="全部" :value="''" />
          <el-option label="已启用" :value="true" />
          <el-option label="已禁用" :value="false" />
        </el-select>
        <el-select v-model="filters.healthStatus" placeholder="健康状态" clearable @change="fetchChannels" class="filter-select">
          <el-option label="全部" :value="''" />
          <el-option label="正常" :value="true" />
          <el-option label="离线" :value="false" />
        </el-select>
      </div>
    </div>
    
    <!-- 频道表格 -->
    <el-table
      v-loading="loading"
      :data="channels"
      class="channels-table"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="50" />
      <el-table-column label="Logo" width="80">
        <template #default="{ row }">
          <img v-if="row.logo" :src="row.logo" class="channel-logo" alt="logo" />
          <div v-else class="logo-placeholder">
            <el-icon><VideoPlay /></el-icon>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="频道名称" min-width="150" />
      <el-table-column label="分组" min-width="120">
        <template #default="{ row }">
          <el-tag v-if="row.group_name" size="small">{{ row.group_name }}</el-tag>
          <span v-else class="text-muted">未分组</span>
        </template>
      </el-table-column>
      <el-table-column label="协议" width="100">
        <template #default="{ row }">
          <el-tag :type="getProtocolType(row.protocol)" size="small">
            {{ row.protocol.toUpperCase() }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_healthy ? 'success' : 'danger'" size="small">
            {{ row.is_healthy ? '正常' : '离线' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="启用" width="80">
        <template #default="{ row }">
          <el-switch
            v-model="row.is_active"
            @change="toggleActive(row)"
          />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" @click="checkSingleChannel(row)" :loading="row._checking">
            检测
          </el-button>
          <el-button link type="primary" @click="openChannelDialog(row)">
            编辑
          </el-button>
          <el-button link type="danger" @click="deleteChannel(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 批量操作 & 分页 -->
    <div class="table-footer">
      <div class="batch-actions" v-if="selectedChannels.length">
        <span>已选择 {{ selectedChannels.length }} 项</span>
        <el-button type="danger" size="small" @click="batchDelete">
          批量删除
        </el-button>
      </div>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.perPage"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchChannels"
        @current-change="fetchChannels"
      />
    </div>
    
    <!-- 添加/编辑频道对话框 -->
    <el-dialog
      v-model="channelDialogVisible"
      :title="editingChannel ? '编辑频道' : '添加频道'"
      width="500px"
    >
      <el-form
        ref="channelFormRef"
        :model="channelForm"
        :rules="channelRules"
        label-width="80px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="channelForm.name" placeholder="频道名称" />
        </el-form-item>
        <el-form-item label="地址" prop="url">
          <el-input v-model="channelForm.url" placeholder="频道源地址" />
        </el-form-item>
        <el-form-item label="Logo">
          <el-input v-model="channelForm.logo" placeholder="Logo URL（可选）" />
        </el-form-item>
        <el-form-item label="TVG-ID">
          <el-input v-model="channelForm.tvg_id" placeholder="EPG tvg-id（可选）" />
        </el-form-item>
        <el-form-item label="分组">
          <div style="display: flex; gap: 8px; width: 100%">
            <el-select v-model="channelForm.group_id" placeholder="选择分组" clearable style="flex: 1">
              <el-option label="无分组" :value="''" />
              <el-option
                v-for="group in groups"
                :key="group.id"
                :label="group.name"
                :value="group.id"
              />
            </el-select>
            <el-button @click="showNewGroupInput = true" v-if="!showNewGroupInput">
              <el-icon><Plus /></el-icon>
            </el-button>
          </div>
          <div v-if="showNewGroupInput" style="margin-top: 8px; display: flex; gap: 8px; width: 100%">
            <el-input v-model="newGroupName" placeholder="新分组名称" style="flex: 1" />
            <el-button type="primary" @click="createGroupAndSelect" :loading="creatingGroup">创建</el-button>
            <el-button @click="showNewGroupInput = false; newGroupName = ''">取消</el-button>
          </div>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="channelForm.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChannel" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 导入对话框 -->
    <el-dialog v-model="showImportDialog" title="导入频道" width="500px">
      <el-form label-width="100px">
        <el-form-item label="导入方式">
          <el-radio-group v-model="importType">
            <el-radio value="file">文件上传</el-radio>
            <el-radio value="text">粘贴内容</el-radio>
            <el-radio value="url">URL导入</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item v-if="importType === 'file'" label="选择文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".m3u,.txt"
            :on-change="handleFileChange"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 .m3u 和 .txt 格式</div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item v-else-if="importType === 'text'" label="内容">
          <el-input
            v-model="importContent"
            type="textarea"
            :rows="8"
            placeholder="粘贴 M3U 或 TXT 格式的频道列表"
          />
        </el-form-item>
        
        <el-form-item v-else-if="importType === 'url'" label="URL地址">
          <el-input
            v-model="importUrl"
            placeholder="输入 M3U/TXT 文件的 URL 地址"
            clearable
          />
          <div class="form-tip" style="margin-top: 4px; margin-left: 0;">支持 http:// 或 https:// 开头的 M3U/TXT 链接，自动检测格式</div>
        </el-form-item>
        
        <el-form-item v-if="importType === 'text'" label="格式">
          <el-radio-group v-model="importFormat">
            <el-radio value="m3u">M3U</el-radio>
            <el-radio value="txt">TXT</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="覆盖">
          <el-switch v-model="importOverwrite" />
          <span class="form-tip">开启后将清空现有频道</span>
        </el-form-item>
        
        <el-form-item label="自动分组">
          <el-switch v-model="importAutoCreateGroup" />
          <span class="form-tip">自动创建导入数据中的新分组</span>
        </el-form-item>
        
        <el-divider content-position="left">过滤选项</el-divider>
        
        <el-form-item label="包含关键词">
          <el-input v-model="importIncludeRegex" placeholder="正则匹配，留空导入所有" />
          <div class="form-tip" style="margin-left: 0; margin-top: 4px">只导入匹配此正则的频道</div>
        </el-form-item>
        
        <el-form-item label="排除关键词">
          <el-input v-model="importExcludeRegex" placeholder="正则匹配，留空不排除" />
          <div class="form-tip" style="margin-left: 0; margin-top: 4px">跳过匹配此正则的频道</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing">导入</el-button>
      </template>
    </el-dialog>
    <!-- 导出对话框 -->
    <el-dialog v-model="showExportDialog" title="导出频道" width="400px">
      <el-form label-width="100px">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportFormat">
            <el-radio value="m3u">M3U 文件 (.m3u)</el-radio>
            <el-radio value="txt">TXT 文件 (.txt)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExportDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Upload, Download, Plus, Refresh, VideoPlay } from '@element-plus/icons-vue'
import api from '@/api'

// 数据
const channels = ref([])
const groups = ref([])
const loading = ref(false)
const saving = ref(false)
const healthCheckLoading = ref(false)
const selectedChannels = ref([])

// 筛选
const filters = reactive({
  search: '',
  groupId: null,
  protocol: '',
  isActive: null,
  healthStatus: null
})

// 分页
const pagination = reactive({
  page: 1,
  perPage: 50,
  total: 0
})

// 频道对话框
const channelDialogVisible = ref(false)
const editingChannel = ref(null)
const channelFormRef = ref()
const channelForm = reactive({
  name: '',
  url: '',
  logo: '',
  tvg_id: '',
  group_id: null,
  sort_order: 0
})

const channelRules = {
  name: [{ required: true, message: '请输入频道名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入频道地址', trigger: 'blur' }]
}

// 导入相关
const showImportDialog = ref(false)
const importType = ref('file')
const importContent = ref('')
const importFormat = ref('m3u')
const importOverwrite = ref(false)
const importAutoCreateGroup = ref(true)
const importIncludeRegex = ref('')
const importExcludeRegex = ref('')
const importFile = ref(null)
const importUrl = ref('')
const importing = ref(false)

// 新建分组相关
const showNewGroupInput = ref(false)
const newGroupName = ref('')
const creatingGroup = ref(false)

// 防抖搜索
let searchTimer = null
function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    pagination.page = 1
    fetchChannels()
  }, 300)
}

// 获取频道列表
async function fetchChannels() {
  loading.value = true
  try {
    const response = await api.channels.list({
      page: pagination.page,
      per_page: pagination.perPage,
      search: filters.search || undefined,
      group_id: filters.groupId === '' ? undefined : filters.groupId,
      protocol: filters.protocol || undefined,
      is_active: filters.isActive === '' ? undefined : filters.isActive,
      is_healthy: filters.healthStatus === '' ? undefined : filters.healthStatus
    })
    channels.value = response.data.items
    pagination.total = response.data.total
  } catch (error) {
    ElMessage.error('获取频道列表失败')
  } finally {
    loading.value = false
  }
}

// 获取分组列表
async function fetchGroups() {
  try {
    const response = await api.groups.list()
    groups.value = response.data
  } catch (error) {
    console.error('获取分组失败', error)
  }
}

// 打开频道对话框
function openChannelDialog(channel = null) {
  editingChannel.value = channel
  if (channel) {
    Object.assign(channelForm, {
      name: channel.name,
      url: channel.url,
      logo: channel.logo || '',
      tvg_id: channel.tvg_id || '',
      group_id: channel.group_id,
      sort_order: channel.sort_order
    })
  } else {
    Object.assign(channelForm, {
      name: '',
      url: '',
      logo: '',
      tvg_id: '',
      group_id: null,
      sort_order: 0
    })
  }
  channelDialogVisible.value = true
}

// 保存频道
async function saveChannel() {
  if (!channelFormRef.value) return
  
  await channelFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      const data = { ...channelForm }
      if (data.group_id === '') data.group_id = null
      
      if (editingChannel.value) {
        await api.channels.update(editingChannel.value.id, data)
        ElMessage.success('频道更新成功')
      } else {
        await api.channels.create(data)
        ElMessage.success('频道创建成功')
      }
      channelDialogVisible.value = false
      fetchChannels()
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

// 删除频道
async function deleteChannel(channel) {
  try {
    await ElMessageBox.confirm(`确定要删除频道 "${channel.name}" 吗？`, '确认删除', {
      type: 'warning'
    })
    await api.channels.delete(channel.id)
    ElMessage.success('删除成功')
    fetchChannels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 批量删除
async function batchDelete() {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedChannels.value.length} 个频道吗？`, '确认删除', {
      type: 'warning'
    })
    const ids = selectedChannels.value.map(c => c.id)
    await api.channels.batchDelete(ids)
    ElMessage.success('批量删除成功')
    fetchChannels()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

// 切换启用状态
async function toggleActive(channel) {
  try {
    await api.channels.update(channel.id, { is_active: channel.is_active })
  } catch (error) {
    channel.is_active = !channel.is_active
    ElMessage.error('更新失败')
  }
}

// 选择变更
function handleSelectionChange(selection) {
  selectedChannels.value = selection
}

// 协议类型样式
function getProtocolType(protocol) {
  const types = {
    http: 'info',
    https: 'success',
    rtp: 'warning',
    udp: 'warning'
  }
  return types[protocol] || 'info'
}

// 检测全部频道
async function runHealthCheck() {
  healthCheckLoading.value = true
  try {
    const result = await api.health.checkAll()
    const data = result.data
    ElMessage.success(`检测完成：正常 ${data.healthy} 个，异常 ${data.unhealthy} 个`)
    fetchChannels()
  } catch (error) {
    ElMessage.error('健康检测失败')
  } finally {
    healthCheckLoading.value = false
  }
}

// 检测单个频道
async function checkSingleChannel(channel) {
  channel._checking = true
  try {
    const result = await api.health.checkOne(channel.id)
    channel.is_healthy = result.data.is_healthy
    channel.last_check = result.data.last_check
    ElMessage.success(`频道 "${channel.name}" 检测完成：${result.data.is_healthy ? '正常' : '异常'}`)
  } catch (error) {
    ElMessage.error('检测失败')
  } finally {
    channel._checking = false
  }
}

// 文件选择
function handleFileChange(file) {
  importFile.value = file.raw
}

// 导入
async function handleImport() {
  importing.value = true
  try {
    if (importType.value === 'file' && importFile.value) {
      const formData = new FormData()
      formData.append('file', importFile.value)
      formData.append('overwrite', importOverwrite.value)
      formData.append('auto_create_group', importAutoCreateGroup.value)
      formData.append('include_regex', importIncludeRegex.value)
      formData.append('exclude_regex', importExcludeRegex.value)
      await api.importExport.import(formData)
    } else if (importType.value === 'text' && importContent.value) {
      await api.importExport.importContent(
        importContent.value, 
        importFormat.value, 
        importOverwrite.value, 
        importAutoCreateGroup.value,
        importIncludeRegex.value,
        importExcludeRegex.value
      )
    } else if (importType.value === 'url' && importUrl.value) {
      await api.importExport.importFromUrl(
        importUrl.value, 
        importOverwrite.value, 
        importAutoCreateGroup.value, 
        'auto',
        importIncludeRegex.value,
        importExcludeRegex.value
      )
    } else {
      ElMessage.warning('请选择文件、输入内容或填写 URL')
      return
    }
    ElMessage.success('导入成功')
    showImportDialog.value = false
    importContent.value = ''
    importFile.value = null
    importUrl.value = ''
    importIncludeRegex.value = ''
    importExcludeRegex.value = ''
    fetchChannels()
    fetchGroups()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '导入失败')
  } finally {
    importing.value = false
  }
}

// 创建分组并选择
async function createGroupAndSelect() {
  if (!newGroupName.value.trim()) {
    ElMessage.warning('请输入分组名称')
    return
  }
  
  creatingGroup.value = true
  try {
    const response = await api.groups.create({ name: newGroupName.value.trim(), sort_order: 0 })
    ElMessage.success('分组创建成功')
    await fetchGroups()
    channelForm.group_id = response.data.id
    showNewGroupInput.value = false
    newGroupName.value = ''
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '创建分组失败')
  } finally {
    creatingGroup.value = false
  }
}

// 导出
const showExportDialog = ref(false)
const exportFormat = ref('m3u')

// 导出 - 打开对话框
function handleExport() {
  exportFormat.value = 'm3u'
  showExportDialog.value = true
}

// 导出 - 确认
async function confirmExport() {
  try {
    const format = exportFormat.value
    const response = await api.importExport.export(format)
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `channels.${format}`
    link.click()
    window.URL.revokeObjectURL(url)
    showExportDialog.value = false
    ElMessage.success('导出已开始下载')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  fetchChannels()
  fetchGroups()
})
</script>

<style scoped>
.channels-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 24px;
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 280px;
}

.filter-select {
  width: 160px;
}

.channels-table {
  margin-bottom: 24px;
}

.channel-logo {
  width: 40px;
  height: 40px;
  object-fit: contain;
  border-radius: 8px;
  background: var(--bg-secondary);
}

.logo-placeholder {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-secondary);
  border-radius: 8px;
  color: var(--text-muted);
}

.text-muted {
  color: var(--text-muted);
}

.table-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
}

.form-tip {
  margin-left: 12px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
