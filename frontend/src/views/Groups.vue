<template>
  <div class="groups-page">
    <div class="page-header">
      <div class="header-left">
        <h1>📁 分组管理</h1>
        <p>管理频道分组</p>
      </div>
      <div class="header-actions">
        <el-button @click="deleteEmptyGroups" :loading="deletingEmpty">
          <el-icon><Delete /></el-icon>
          删除空分组
        </el-button>
        <el-button type="primary" @click="openGroupDialog()">
          <el-icon><Plus /></el-icon>
          添加分组
        </el-button>
      </div>
    </div>
    
    <!-- 分组列表 -->
    <div class="groups-grid" v-loading="loading">
      <div
        v-for="group in groups"
        :key="group.id"
        class="group-card"
      >
        <div class="group-header">
          <div class="group-icon">
            📂
          </div>
          <div class="group-info">
            <h3>{{ group.name }}</h3>
            <span class="channel-count">{{ group.channel_count }} 个频道</span>
          </div>
        </div>
        <div class="group-actions">
          <el-button link type="primary" @click="openGroupDialog(group)">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button link type="danger" @click="deleteGroup(group)">
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </div>
      </div>
      
      <!-- 添加分组卡片 -->
      <div class="group-card add-card" @click="openGroupDialog()">
        <span class="add-emoji">➕</span>
        <span>添加分组</span>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-if="!loading && groups.length === 0" class="empty-state">
      <span class="empty-emoji">📂</span>
      <h3>暂无分组</h3>
      <p>点击上方按钮添加第一个分组</p>
    </div>
    
    <!-- 添加/编辑分组对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingGroup ? '编辑分组' : '添加分组'"
      width="400px"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="分组名称" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveGroup" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/api'

const groups = ref([])
const loading = ref(false)
const saving = ref(false)
const deletingEmpty = ref(false)

const dialogVisible = ref(false)
const editingGroup = ref(null)
const formRef = ref()
const form = reactive({
  name: '',
  sort_order: 0
})

const rules = {
  name: [{ required: true, message: '请输入分组名称', trigger: 'blur' }]
}

async function fetchGroups() {
  loading.value = true
  try {
    const response = await api.groups.list()
    groups.value = response.data
  } catch (error) {
    ElMessage.error('获取分组列表失败')
  } finally {
    loading.value = false
  }
}

function openGroupDialog(group = null) {
  editingGroup.value = group
  if (group) {
    Object.assign(form, {
      name: group.name,
      sort_order: group.sort_order
    })
  } else {
    Object.assign(form, {
      name: '',
      sort_order: 0
    })
  }
  dialogVisible.value = true
}

async function saveGroup() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      if (editingGroup.value) {
        await api.groups.update(editingGroup.value.id, form)
        ElMessage.success('分组更新成功')
      } else {
        await api.groups.create(form)
        ElMessage.success('分组创建成功')
      }
      dialogVisible.value = false
      fetchGroups()
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '保存失败')
    } finally {
      saving.value = false
    }
  })
}

async function deleteGroup(group) {
  // 如果分组下有频道，直接提示不允许删除
  if (group.channel_count > 0) {
    ElMessage.warning(`无法删除：分组 "${group.name}" 下有 ${group.channel_count} 个频道，请先移除或修改这些频道的分组`)
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除分组 "${group.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    await api.groups.delete(group.id)
    ElMessage.success('分组删除成功')
    fetchGroups()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  }
}

async function deleteEmptyGroups() {
  // 检查是否有空分组
  const emptyCount = groups.value.filter(g => g.channel_count === 0).length
  if (emptyCount === 0) {
    ElMessage.info('没有空分组需要删除')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除 ${emptyCount} 个空分组吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    deletingEmpty.value = true
    const response = await api.groups.deleteEmpty()
    ElMessage.success(response.data.message)
    fetchGroups()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  } finally {
    deletingEmpty.value = false
  }
}

onMounted(fetchGroups)
</script>

<style scoped>
.groups-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 26px;
  font-weight: 700;
  margin-bottom: 6px;
}

.page-header p {
  color: var(--text-muted);
}

.groups-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.group-card {
  background: var(--bg-card);
  border-radius: var(--border-radius);
  padding: 24px;
  border: 1px solid var(--border-color);
  transition: background-color 0.3s ease, border-color 0.3s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.group-card:hover {
  border-color: var(--accent-primary);
  box-shadow: var(--shadow-md);
}

.group-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.group-icon {
  width: 48px;
  height: 48px;
  background: var(--accent-gradient);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.group-info h3 {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.channel-count {
  color: var(--text-muted);
  font-size: 14px;
}

.group-actions {
  display: flex;
  gap: 16px;
}

.add-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  cursor: pointer;
  border-style: dashed;
  color: var(--text-muted);
  min-height: 160px;
}

.add-card:hover {
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.empty-state {
  text-align: center;
  padding: 64px;
  color: var(--text-muted);
}

.empty-state h3 {
  margin: 24px 0 8px;
  font-size: 20px;
  color: var(--text-primary);
}
</style>
