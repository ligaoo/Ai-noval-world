<template>
  <div class="space-y-8">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          线索管理
        </h2>
        <p class="text-gray-400 mt-1">设计和管理小说中的线索与发现路径</p>
      </div>
      <PButton label="添加线索" icon="pi pi-plus" @click="showAddDialog = true" />
    </div>

    <!-- 线索卡片列表 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="(clue, index) in clues"
        :key="clue.clue_id"
        class="glass-card p-6 hover-lift cursor-pointer group"
        @click="openClue(index)"
      >
        <!-- 头部：级别和名称 -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-3">
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center"
              :class="getLevelColor(clue.level)"
            >
              <Search class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="font-semibold">{{ clue.name }}</h3>
              <span class="text-xs text-gray-500">{{ clue.clue_id }}</span>
            </div>
          </div>
          <PBadge
            :value="getLevelLabel(clue.level)"
            :class="getLevelBadgeClass(clue.level)"
          />
        </div>

        <!-- 线索内容 -->
        <div class="mb-4 p-3 rounded-xl bg-noir-800/50">
          <p class="text-sm text-gray-300">{{ clue.content }}</p>
        </div>

        <!-- 发现路径数量 -->
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-500">发现路径</span>
          <span class="text-neon-cyan font-medium">
            {{ clue.discover_routes?.length || 0 }} 条
          </span>
        </div>

        <!-- 允许发现阶段 -->
        <div class="mt-3">
          <span class="text-xs text-gray-500 block mb-2">可发现阶段</span>
          <div class="flex flex-wrap gap-1">
            <span
              v-for="stage in clue.allowed_stages"
              :key="stage"
              class="px-2 py-0.5 rounded-full text-xs bg-neon-purple/20 text-neon-purple"
            >
              {{ stage }}
            </span>
          </div>
        </div>

        <!-- 悬停操作按钮 -->
        <div class="mt-4 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <PButton
            icon="pi pi-pencil"
            text
            size="small"
            class="p-button-text"
            @click.stop="openClue(index)"
          />
          <PButton
            icon="pi pi-trash"
            text
            size="small"
            class="p-button-text p-button-danger"
            @click.stop="deleteClue(index)"
          />
        </div>
      </div>

      <!-- 添加线索卡片 -->
      <div
        class="glass-card p-6 hover-lift flex flex-col items-center justify-center cursor-pointer border-dashed border-2 border-noir-600 hover:border-neon-purple transition-colors"
        @click="showAddDialog = true"
      >
        <div class="w-14 h-14 rounded-2xl bg-noir-700 flex items-center justify-center mb-4 group-hover:bg-neon-purple/20 transition-colors">
          <Plus class="w-7 h-7 text-gray-400 group-hover:text-neon-purple transition-colors" />
        </div>
        <p class="text-gray-400 font-medium">添加新线索</p>
      </div>
    </div>

    <!-- 添加/编辑线索弹窗 -->
    <PDialog
      v-model:visible="showAddDialog"
      header="添加线索"
      :modal="true"
      class="w-full max-w-4xl"
      contentStyle="background: #2a2d35; border: 1px solid #374151"
    >
      <div class="space-y-6">
        <!-- 基本信息 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">线索 ID</label>
            <PInputText
              v-model="newClue.clue_id"
              class="w-full input-dark"
              placeholder="例如：hf_001"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">线索名称</label>
            <PInputText
              v-model="newClue.name"
              class="w-full input-dark"
              placeholder="例如：最近更换的铁锁"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">线索级别</label>
            <PDropdown
              v-model="newClue.level"
              :options="levelOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="选择级别"
              class="w-full"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">重要度</label>
            <input
              type="range"
              v-model.number="newClue.importance"
              min="1"
              max="100"
              class="w-full accent-neon-purple"
            />
            <div class="text-center text-neon-purple font-bold mt-1">
              {{ newClue.importance }} / 100
            </div>
          </div>
        </div>

        <!-- 线索内容 -->
        <div>
          <label class="text-sm text-gray-400 block mb-2">线索内容</label>
          <PTextarea
            v-model="newClue.content"
            class="w-full input-dark"
            rows="2"
            placeholder="描述发现线索时的具体内容..."
          />
        </div>

        <!-- 允许阶段 -->
        <div>
          <label class="text-sm text-gray-400 block mb-3">允许发现阶段</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="stage in stageOptions"
              :key="stage.value"
              class="px-4 py-2 rounded-xl text-sm font-medium transition-all"
              :class="newClue.allowed_stages.includes(stage.value)
                ? 'bg-neon-purple/30 text-neon-purple border border-neon-purple/50'
                : 'bg-noir-700 text-gray-400 border border-transparent hover:border-gray-500'"
              @click="toggleStage(stage.value)"
            >
              {{ stage.label }}
            </button>
          </div>
        </div>

        <!-- 发现路径 -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="text-sm text-gray-400">发现路径</label>
            <PButton
              label="+ 添加路径"
              text
              size="small"
              class="p-button-text text-neon-purple"
              @click="addDiscoverRoute"
            />
          </div>

          <div class="space-y-4">
            <div
              v-for="(route, rIndex) in newClue.discover_routes"
              :key="rIndex"
              class="p-4 rounded-xl bg-noir-800/50 space-y-4"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium text-neon-cyan">路径 {{ rIndex + 1 }}</span>
                <PButton
                  icon="pi pi-trash"
                  text
                  size="small"
                  class="p-button-text p-button-danger"
                  @click="newClue.discover_routes.splice(rIndex, 1)"
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="text-xs text-gray-500 block mb-1">动作类型</label>
                  <PDropdown
                    v-model="route.action_type"
                    :options="actionTypeOptions"
                    placeholder="选择动作"
                    class="w-full"
                  />
                </div>
                <div>
                  <label class="text-xs text-gray-500 block mb-1">目标</label>
                  <PInputText
                    v-model="route.target"
                    class="w-full input-dark"
                    placeholder="目标对象 ID"
                  />
                </div>
                <div>
                  <label class="text-xs text-gray-500 block mb-1">地点</label>
                  <PDropdown
                    v-model="route.location_id"
                    :options="locationOptions"
                    placeholder="选择地点"
                    class="w-full"
                  />
                </div>
                <div>
                  <label class="text-xs text-gray-500 block mb-1">难度</label>
                  <input
                    type="range"
                    v-model.number="route.difficulty"
                    min="1"
                    max="100"
                    class="w-full accent-neon-purple"
                  />
                  <div class="text-center text-neon-purple text-xs mt-1">
                    {{ route.difficulty }} / 100
                  </div>
                </div>
              </div>

              <div>
                <label class="text-xs text-gray-500 block mb-1">发现结果</label>
                <PTextarea
                  v-model="route.result"
                  class="w-full input-dark"
                  rows="2"
                  placeholder="描述发现后的具体结果..."
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <PButton label="取消" severity="secondary" text @click="showAddDialog = false" />
        <PButton label="保存" @click="saveClue" />
      </template>
    </PDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useWorldStore } from '@/stores/world'
import { Search, Plus } from 'lucide-vue-next'

const worldStore = useWorldStore()
const toast = useToast()

const clues = computed(() => worldStore.clues)
const locations = computed(() => worldStore.locations)

const showAddDialog = ref(false)
const editingIndex = ref(-1)

const levelOptions = [
  { label: '表层 (Surface)', value: 'surface' },
  { label: '浅层 (Shallow)', value: 'shallow' },
  { label: '深层 (Deep)', value: 'deep' },
  { label: '核心 (Core)', value: 'core' },
]

const stageOptions = [
  { label: '序幕', value: 'prologue' },
  { label: '第一章', value: 'chapter_1' },
  { label: '第二章', value: 'chapter_2' },
  { label: '第三章', value: 'chapter_3' },
  { label: '高潮', value: 'climax' },
  { label: '结局', value: 'epilogue' },
]

const actionTypeOptions = [
  '调查',
  '搜索',
  '询问',
  '观察',
  '触碰',
  '阅读',
  '聆听',
  '检查',
]

const locationOptions = computed(() =>
  locations.value.map(loc => ({ label: loc.name, value: loc.id }))
)

const newClue = ref({
  clue_id: '',
  name: '',
  level: 'surface',
  importance: 50,
  content: '',
  allowed_stages: [],
  discover_routes: [],
})

const getLevelColor = (level) => {
  const colors = {
    surface: 'bg-gray-600',
    shallow: 'bg-blue-600',
    deep: 'bg-purple-600',
    core: 'bg-red-600',
  }
  return colors[level] || colors.surface
}

const getLevelLabel = (level) => {
  const labels = {
    surface: '表层',
    shallow: '浅层',
    deep: '深层',
    core: '核心',
  }
  return labels[level] || '未知'
}

const getLevelBadgeClass = (level) => {
  const classes = {
    surface: 'p-badge-gray',
    shallow: 'p-badge-info',
    deep: 'p-badge-secondary',
    core: 'p-badge-danger',
  }
  return classes[level] || classes.surface
}

const toggleStage = (stage) => {
  const index = newClue.value.allowed_stages.indexOf(stage)
  if (index > -1) {
    newClue.value.allowed_stages.splice(index, 1)
  } else {
    newClue.value.allowed_stages.push(stage)
  }
}

const addDiscoverRoute = () => {
  newClue.value.discover_routes.push({
    action_type: '',
    target: '',
    location_id: '',
    difficulty: 50,
    result: '',
  })
}

const openClue = (index) => {
  editingIndex.value = index
  const clue = clues.value[index]
  newClue.value = JSON.parse(JSON.stringify(clue))
  showAddDialog.value = true
}

const saveClue = () => {
  if (!newClue.value.clue_id || !newClue.value.name) {
    toast.add({
      severity: 'error',
      summary: '保存失败',
      detail: '线索 ID 和名称不能为空',
      life: 3000,
    })
    return
  }

  if (editingIndex.value >= 0) {
    worldStore.updateClue(editingIndex.value, newClue.value)
    toast.add({
      severity: 'success',
      summary: '更新成功',
      detail: `线索 ${newClue.value.name} 已更新`,
      life: 3000,
    })
  } else {
    worldStore.addClue(newClue.value)
    toast.add({
      severity: 'success',
      summary: '添加成功',
      detail: `线索 ${newClue.value.name} 已添加`,
      life: 3000,
    })
  }

  showAddDialog.value = false
  resetForm()
}

const deleteClue = (index) => {
  const clue = clues.value[index]
  worldStore.removeClue(index)
  toast.add({
    severity: 'success',
    summary: '删除成功',
    detail: `线索 ${clue.name} 已删除`,
    life: 3000,
  })
}

const resetForm = () => {
  editingIndex.value = -1
  newClue.value = {
    clue_id: '',
    name: '',
    level: 'surface',
    importance: 50,
    content: '',
    allowed_stages: [],
    discover_routes: [],
  }
}

onMounted(() => {
  showAddDialog.value = false
})
</script>
