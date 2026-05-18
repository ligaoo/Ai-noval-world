<template>
  <div class="space-y-8">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          剧情弧管理
        </h2>
        <p class="text-gray-400 mt-1">设计和管理小说的整体剧情结构与阶段</p>
      </div>
      <PButton label="添加剧情弧" icon="pi pi-plus" @click="showAddDialog = true" />
    </div>

    <!-- 剧情弧时间线 -->
    <div class="space-y-6">
      <div
        v-for="(arc, arcIndex) in plotArcs"
        :key="arc.arc_id"
        class="glass-card p-6"
      >
        <!-- 剧情弧头部 -->
        <div class="flex items-start justify-between mb-6">
          <div class="flex items-center gap-4">
            <div
              class="w-12 h-12 rounded-xl flex items-center justify-center"
              :class="getStatusColor(arc.status)"
            >
              <GitBranch class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="text-xl font-semibold">{{ arc.name }}</h3>
              <p class="text-sm text-gray-500">{{ arc.arc_id }}</p>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <PBadge
              :value="getStatusLabel(arc.status)"
              :class="getStatusBadgeClass(arc.status)"
            />
            <PButton
              icon="pi pi-pencil"
              text
              size="small"
              class="p-button-text"
              @click="openArc(arcIndex)"
            />
            <PButton
              icon="pi pi-trash"
              text
              size="small"
              class="p-button-text p-button-danger"
              @click="deleteArc(arcIndex)"
            />
          </div>
        </div>

        <!-- 进度条 -->
        <div class="mb-6">
          <div class="flex items-center justify-between text-sm mb-2">
            <span class="text-gray-500">整体进度</span>
            <span class="text-neon-purple font-medium">{{ arc.progress }}%</span>
          </div>
          <PProgressBar
            :value="arc.progress"
            class="h-2"
            styleClass="bg-noir-700"
            :showValue="false"
          />
        </div>

        <!-- 阶段时间线 -->
        <div class="relative">
          <div class="absolute left-6 top-0 bottom-0 w-0.5 bg-noir-700"></div>
          <div class="space-y-4">
            <div
              v-for="(stage, stageIndex) in arc.stages"
              :key="stage.stage_id"
              class="relative pl-16"
            >
              <!-- 阶段节点 -->
              <div
                class="absolute left-4 top-0 w-5 h-5 rounded-full border-2 border-noir-600 bg-noir-900 flex items-center justify-center"
                :class="getStageClass(stage, arc.current_stage)"
              >
                <div v-if="stage.stage_id === arc.current_stage" class="w-2 h-2 rounded-full bg-current"></div>
              </div>

              <!-- 阶段内容 -->
              <div
                class="p-4 rounded-xl transition-all"
                :class="stage.stage_id === arc.current_stage
                  ? 'bg-neon-purple/10 border border-neon-purple/30'
                  : 'bg-noir-800/50 hover:bg-noir-800'"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-3">
                    <h4 class="font-semibold">{{ stage.name }}</h4>
                    <span v-if="stage.stage_id === arc.current_stage" class="px-2 py-0.5 rounded-full text-xs bg-neon-purple/20 text-neon-purple">
                      当前阶段
                    </span>
                  </div>
                  <div class="flex items-center gap-2">
                    <PButton
                      icon="pi pi-arrow-right"
                      text
                      size="small"
                      class="p-button-text p-button-sm"
                      @click="setCurrentStage(arcIndex, stage.stage_id)"
                      v-if="stage.stage_id !== arc.current_stage"
                    />
                  </div>
                </div>

                <p class="text-sm text-gray-400 mb-3">{{ stage.purpose }}</p>

                <!-- 允许的线索级别 -->
                <div class="flex flex-wrap gap-2 mb-2">
                  <span class="text-xs text-gray-500">允许线索级别：</span>
                  <span
                    v-for="level in stage.allowed_clue_levels"
                    :key="level"
                    class="px-2 py-0.5 rounded-full text-xs bg-noir-700 text-gray-300"
                  >
                    {{ level }}
                  </span>
                </div>

                <!-- 禁止揭示 -->
                <div v-if="stage.forbidden_revelations.length > 0" class="flex flex-wrap gap-2">
                  <span class="text-xs text-gray-500">禁止揭示：</span>
                  <span
                    v-for="item in stage.forbidden_revelations"
                    :key="item"
                    class="px-2 py-0.5 rounded-full text-xs bg-red-900/30 text-red-400"
                  >
                    {{ item }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 添加剧情弧卡片 -->
      <div
        class="glass-card p-6 hover-lift flex flex-col items-center justify-center cursor-pointer border-dashed border-2 border-noir-600 hover:border-neon-purple transition-colors"
        @click="showAddDialog = true"
      >
        <div class="w-14 h-14 rounded-2xl bg-noir-700 flex items-center justify-center mb-4 group-hover:bg-neon-purple/20 transition-colors">
          <Plus class="w-7 h-7 text-gray-400 group-hover:text-neon-purple transition-colors" />
        </div>
        <p class="text-gray-400 font-medium">添加新剧情弧</p>
      </div>
    </div>

    <!-- 添加/编辑剧情弧弹窗 -->
    <PDialog
      v-model:visible="showAddDialog"
      header="添加剧情弧"
      :modal="true"
      class="w-full max-w-3xl"
      contentStyle="background: #2a2d35; border: 1px solid #374151"
    >
      <div class="space-y-6">
        <!-- 基本信息 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">剧情弧 ID</label>
            <PInputText
              v-model="newArc.arc_id"
              class="w-full input-dark"
              placeholder="例如：arc_hospital_truth"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">剧情弧名称</label>
            <PInputText
              v-model="newArc.name"
              class="w-full input-dark"
              placeholder="例如：旧医院真相篇"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">状态</label>
            <PDropdown
              v-model="newArc.status"
              :options="statusOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="选择状态"
              class="w-full"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">进度</label>
            <input
              type="range"
              v-model.number="newArc.progress"
              min="0"
              max="100"
              class="w-full accent-neon-purple"
            />
            <div class="text-center text-neon-purple font-bold mt-1">
              {{ newArc.progress }}%
            </div>
          </div>
        </div>

        <!-- 阶段管理 -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="text-sm text-gray-400">阶段设置</label>
            <PButton
              label="+ 添加阶段"
              text
              size="small"
              class="p-button-text text-neon-purple"
              @click="addStage"
            />
          </div>

          <div class="space-y-4">
            <div
              v-for="(stage, sIndex) in newArc.stages"
              :key="sIndex"
              class="p-4 rounded-xl bg-noir-800/50 space-y-4"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium text-neon-cyan">阶段 {{ sIndex + 1 }}</span>
                <PButton
                  icon="pi pi-trash"
                  text
                  size="small"
                  class="p-button-text p-button-danger"
                  @click="newArc.stages.splice(sIndex, 1)"
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="text-xs text-gray-500 block mb-1">阶段 ID</label>
                  <PInputText
                    v-model="stage.stage_id"
                    class="w-full input-dark"
                    placeholder="setup"
                  />
                </div>
                <div>
                  <label class="text-xs text-gray-500 block mb-1">阶段名称</label>
                  <PInputText
                    v-model="stage.name"
                    class="w-full input-dark"
                    placeholder="建立异常"
                  />
                </div>
              </div>

              <div>
                <label class="text-xs text-gray-500 block mb-1">阶段目标</label>
                <PInputText
                  v-model="stage.purpose"
                  class="w-full input-dark"
                  placeholder="建立医院并非完全废弃的认知"
                />
              </div>

              <div>
                <label class="text-xs text-gray-500 block mb-2">允许线索级别</label>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="level in clueLevelOptions"
                    :key="level.value"
                    class="px-3 py-1 rounded-full text-xs cursor-pointer transition-all"
                    :class="stage.allowed_clue_levels.includes(level.value)
                      ? 'bg-neon-purple/30 text-neon-purple border border-neon-purple/50'
                      : 'bg-noir-700 text-gray-400 border border-transparent hover:border-gray-500'"
                    @click="toggleClueLevel(stage, level.value)"
                  >
                    {{ level.label }}
                  </span>
                </div>
              </div>

              <div>
                <label class="text-xs text-gray-500 block mb-1">禁止揭示（逗号分隔）</label>
                <PInputText
                  v-model="stage.forbidden_revelations_str"
                  class="w-full input-dark"
                  placeholder="truth_1, truth_2"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <PButton label="取消" severity="secondary" text @click="showAddDialog = false" />
        <PButton label="保存" @click="saveArc" />
      </template>
    </PDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useWorldStore } from '@/stores/world'
import { GitBranch, Plus } from 'lucide-vue-next'

const worldStore = useWorldStore()
const toast = useToast()

const plotArcs = computed(() => worldStore.plotArcs)

const showAddDialog = ref(false)
const editingIndex = ref(-1)

const statusOptions = [
  { label: '活跃 (Active)', value: 'active' },
  { label: '进行中 (In Progress)', value: 'in_progress' },
  { label: '已完成 (Completed)', value: 'completed' },
  { label: '搁置 (On Hold)', value: 'on_hold' },
]

const clueLevelOptions = [
  { label: '表层 (surface)', value: 'surface' },
  { label: '次要 (minor)', value: 'minor' },
  { label: '中等 (medium)', value: 'medium' },
  { label: '重要 (major)', value: 'major' },
  { label: '真相 (truth)', value: 'truth' },
]

const newArc = ref({
  arc_id: '',
  name: '',
  status: 'active',
  progress: 0,
  current_stage: '',
  stages: [],
})

const getStatusColor = (status) => {
  const colors = {
    active: 'bg-green-600',
    in_progress: 'bg-blue-600',
    completed: 'bg-gray-600',
    on_hold: 'bg-yellow-600',
  }
  return colors[status] || colors.active
}

const getStatusLabel = (status) => {
  const labels = {
    active: '活跃',
    in_progress: '进行中',
    completed: '已完成',
    on_hold: '搁置',
  }
  return labels[status] || '未知'
}

const getStatusBadgeClass = (status) => {
  const classes = {
    active: 'p-badge-success',
    in_progress: 'p-badge-info',
    completed: 'p-badge-secondary',
    on_hold: 'p-badge-warning',
  }
  return classes[status] || classes.active
}

const getStageClass = (stage, currentStage) => {
  if (stage.stage_id === currentStage) {
    return 'text-neon-purple border-neon-purple bg-neon-purple/20'
  }
  return 'text-gray-400'
}

const addStage = () => {
  newArc.value.stages.push({
    stage_id: '',
    name: '',
    purpose: '',
    allowed_clue_levels: [],
    forbidden_revelations_str: '',
    forbidden_revelations: [],
  })
}

const toggleClueLevel = (stage, level) => {
  const index = stage.allowed_clue_levels.indexOf(level)
  if (index > -1) {
    stage.allowed_clue_levels.splice(index, 1)
  } else {
    stage.allowed_clue_levels.push(level)
  }
}

const openArc = (index) => {
  editingIndex.value = index
  const arc = plotArcs.value[index]
  newArc.value = JSON.parse(JSON.stringify(arc))
  newArc.value.stages = newArc.value.stages.map(stage => ({
    ...stage,
    forbidden_revelations_str: stage.forbidden_revelations.join(', '),
  }))
  showAddDialog.value = true
}

const saveArc = () => {
  if (!newArc.value.arc_id || !newArc.value.name) {
    toast.add({
      severity: 'error',
      summary: '保存失败',
      detail: '剧情弧 ID 和名称不能为空',
      life: 3000,
    })
    return
  }

  // 转换 forbidden_revelations
  newArc.value.stages = newArc.value.stages.map(stage => ({
    ...stage,
    forbidden_revelations: stage.forbidden_revelations_str
      ? stage.forbidden_revelations_str.split(',').map(s => s.trim()).filter(Boolean)
      : [],
  }))

  // 设置默认当前阶段
  if (!newArc.value.current_stage && newArc.value.stages.length > 0) {
    newArc.value.current_stage = newArc.value.stages[0].stage_id
  }

  if (editingIndex.value >= 0) {
    worldStore.plotArcs[editingIndex.value] = newArc.value
    toast.add({
      severity: 'success',
      summary: '更新成功',
      detail: `剧情弧 ${newArc.value.name} 已更新`,
      life: 3000,
    })
  } else {
    worldStore.plotArcs.push(newArc.value)
    toast.add({
      severity: 'success',
      summary: '添加成功',
      detail: `剧情弧 ${newArc.value.name} 已添加`,
      life: 3000,
    })
  }

  showAddDialog.value = false
  resetForm()
}

const deleteArc = (index) => {
  const arc = plotArcs.value[index]
  worldStore.plotArcs.splice(index, 1)
  toast.add({
    severity: 'success',
    summary: '删除成功',
    detail: `剧情弧 ${arc.name} 已删除`,
    life: 3000,
  })
}

const setCurrentStage = (arcIndex, stageId) => {
  worldStore.plotArcs[arcIndex].current_stage = stageId
  toast.add({
    severity: 'success',
    summary: '阶段更新',
    detail: `已切换到 ${stageId}`,
    life: 3000,
  })
}

const resetForm = () => {
  editingIndex.value = -1
  newArc.value = {
    arc_id: '',
    name: '',
    status: 'active',
    progress: 0,
    current_stage: '',
    stages: [],
  }
}

onMounted(() => {
  showAddDialog.value = false
})
</script>
