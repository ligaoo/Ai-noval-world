<template>
  <div class="space-y-8">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          人物弧管理
        </h2>
        <p class="text-gray-400 mt-1">设计和管理角色的成长、转变与心理历程</p>
      </div>
      <PButton label="添加人物弧" icon="pi pi-plus" @click="showAddDialog = true" />
    </div>

    <!-- 人物弧列表 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div
        v-for="(arc, arcIndex) in characterArcs"
        :key="arc.arc_id"
        class="glass-card p-6"
      >
        <!-- 人物弧头部 -->
        <div class="flex items-start justify-between mb-6">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center">
              <UserCircle class="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 class="text-xl font-semibold">{{ arc.character_name }}</h3>
              <p class="text-sm text-gray-500">{{ arc.arc_id }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
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

        <!-- 人物画像 -->
        <div class="mb-6 p-4 rounded-xl bg-noir-800/50">
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <span class="text-xs text-gray-500">身份</span>
              <p class="text-sm">{{ arc.identity }}</p>
            </div>
            <div>
              <span class="text-xs text-gray-500">核心欲望</span>
              <p class="text-sm">{{ arc.core_desire }}</p>
            </div>
            <div>
              <span class="text-xs text-gray-500">心理创伤</span>
              <p class="text-sm">{{ arc.psychological_wound }}</p>
            </div>
            <div>
              <span class="text-xs text-gray-500">恐惧</span>
              <p class="text-sm">{{ arc.fear }}</p>
            </div>
          </div>
          <div>
            <span class="text-xs text-gray-500">谎言</span>
            <p class="text-sm">{{ arc.lie }}</p>
          </div>
        </div>

        <!-- 心理阶段 -->
        <div class="space-y-3">
          <h4 class="text-sm font-medium text-gray-400 mb-3">心理阶段</h4>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="(stage, sIndex) in arc.psychological_stages"
              :key="sIndex"
              class="px-3 py-1.5 rounded-xl text-sm transition-all cursor-default"
              :class="sIndex === arc.current_stage_index
                ? 'bg-neon-purple/30 text-neon-purple border border-neon-purple/50'
                : 'bg-noir-700 text-gray-400'"
            >
              {{ stage.stage_name }}
            </span>
          </div>
        </div>

        <!-- 当前阶段详情 -->
        <div v-if="currentStageDetail(arc)" class="mt-4 p-4 rounded-xl bg-neon-purple/10 border border-neon-purple/30">
          <div class="flex items-center justify-between mb-2">
            <span class="text-neon-purple font-medium text-sm">当前阶段：{{ currentStageDetail(arc).stage_name }}</span>
            <PButton
              icon="pi pi-arrow-right"
              text
              size="small"
              class="p-button-text p-button-sm text-neon-purple"
              @click="nextStage(arcIndex)"
              v-if="arc.current_stage_index < arc.psychological_stages.length - 1"
            />
          </div>
          <p class="text-sm text-gray-300 mb-2">{{ currentStageDetail(arc).description }}</p>
          <div class="flex flex-wrap gap-2">
            <span class="text-xs text-gray-500">必要经历：</span>
            <span
              v-for="exp in currentStageDetail(arc).required_experiences"
              :key="exp"
              class="px-2 py-0.5 rounded-full text-xs bg-noir-700 text-gray-300"
            >
              {{ exp }}
            </span>
          </div>
        </div>

        <!-- 反思点 -->
        <div v-if="arc.reflection_points && arc.reflection_points.length > 0" class="mt-4">
          <h4 class="text-sm font-medium text-gray-400 mb-3">反思与转变</h4>
          <div class="space-y-2">
            <div
              v-for="(point, pIndex) in arc.reflection_points"
              :key="pIndex"
              class="p-3 rounded-xl bg-noir-800/50"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-sm font-medium">{{ point.trigger_event }}</span>
                <PBadge
                  :value="point.emotional_impact"
                  :severity="point.emotional_impact === 'positive' ? 'success' : 'warning'"
                  size="small"
                />
              </div>
              <p class="text-xs text-gray-400">{{ point.reflection }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 添加人物弧卡片 -->
      <div
        class="glass-card p-6 hover-lift flex flex-col items-center justify-center cursor-pointer border-dashed border-2 border-noir-600 hover:border-neon-purple transition-colors"
        @click="showAddDialog = true"
      >
        <div class="w-14 h-14 rounded-2xl bg-noir-700 flex items-center justify-center mb-4 group-hover:bg-neon-purple/20 transition-colors">
          <Plus class="w-7 h-7 text-gray-400 group-hover:text-neon-purple transition-colors" />
        </div>
        <p class="text-gray-400 font-medium">添加新人物弧</p>
      </div>
    </div>

    <!-- 添加/编辑人物弧弹窗 -->
    <PDialog
      v-model:visible="showAddDialog"
      header="添加人物弧"
      :modal="true"
      class="w-full max-w-4xl"
      contentStyle="background: #2a2d35; border: 1px solid #374151"
    >
      <div class="space-y-6">
        <!-- 基本信息 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">人物弧 ID</label>
            <PInputText
              v-model="newArc.arc_id"
              class="w-full input-dark"
              placeholder="例如：arc_char_linzhou"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">角色名称</label>
            <PInputText
              v-model="newArc.character_name"
              class="w-full input-dark"
              placeholder="例如：林舟"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">关联角色 ID</label>
            <PDropdown
              v-model="newArc.character_id"
              :options="characterOptions"
              placeholder="选择角色"
              class="w-full"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">身份</label>
            <PInputText
              v-model="newArc.identity"
              class="w-full input-dark"
              placeholder="例如：调查记者"
            />
          </div>
        </div>

        <!-- 核心心理 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">核心欲望</label>
            <PInputText
              v-model="newArc.core_desire"
              class="w-full input-dark"
              placeholder="例如：找回童年记忆"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">心理创伤</label>
            <PInputText
              v-model="newArc.psychological_wound"
              class="w-full input-dark"
              placeholder="例如：童年目睹死亡却失忆"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">恐惧</label>
            <PInputText
              v-model="newArc.fear"
              class="w-full input-dark"
              placeholder="例如：真相可能无法接受"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">谎言</label>
            <PInputText
              v-model="newArc.lie"
              class="w-full input-dark"
              placeholder="例如：我只是想了解医院历史"
            />
          </div>
        </div>

        <!-- 心理阶段 -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="text-sm text-gray-400">心理阶段</label>
            <PButton
              label="+ 添加阶段"
              text
              size="small"
              class="p-button-text text-neon-purple"
              @click="addPsychologicalStage"
            />
          </div>

          <div class="space-y-4">
            <div
              v-for="(stage, sIndex) in newArc.psychological_stages"
              :key="sIndex"
              class="p-4 rounded-xl bg-noir-800/50 space-y-3"
            >
              <div class="flex items-center justify-between">
                <span class="font-medium text-neon-cyan">阶段 {{ sIndex + 1 }}</span>
                <PButton
                  icon="pi pi-trash"
                  text
                  size="small"
                  class="p-button-text p-button-danger"
                  @click="newArc.psychological_stages.splice(sIndex, 1)"
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="text-xs text-gray-500 block mb-1">阶段名称</label>
                  <PInputText
                    v-model="stage.stage_name"
                    class="w-full input-dark"
                    placeholder="例如：否认"
                  />
                </div>
                <div>
                  <label class="text-xs text-gray-500 block mb-1">心理转变方向</label>
                  <PDropdown
                    v-model="stage.direction"
                    :options="directionOptions"
                    placeholder="选择方向"
                    class="w-full"
                  />
                </div>
              </div>

              <div>
                <label class="text-xs text-gray-500 block mb-1">阶段描述</label>
                <PTextarea
                  v-model="stage.description"
                  class="w-full input-dark"
                  rows="2"
                  placeholder="描述这个阶段的心理状态..."
                />
              </div>

              <div>
                <label class="text-xs text-gray-500 block mb-1">必要经历（逗号分隔）</label>
                <PInputText
                  v-model="stage.required_experiences_str"
                  class="w-full input-dark"
                  placeholder="经历1, 经历2..."
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
import { UserCircle, Plus } from 'lucide-vue-next'

const worldStore = useWorldStore()
const toast = useToast()

const characterArcs = computed(() => worldStore.characterArcs)
const characters = computed(() => worldStore.characters)

const showAddDialog = ref(false)
const editingIndex = ref(-1)

const directionOptions = [
  { label: '成长 (Growth)', value: 'growth' },
  { label: '堕落 (Decay)', value: 'decay' },
  { label: '转变 (Transformation)', value: 'transformation' },
  { label: '觉醒 (Awakening)', value: 'awakening' },
  { label: '崩溃 (Breakdown)', value: 'breakdown' },
]

const characterOptions = computed(() =>
  characters.value.map(char => ({ label: char.name, value: char.character_id }))
)

const newArc = ref({
  arc_id: '',
  character_id: '',
  character_name: '',
  identity: '',
  core_desire: '',
  psychological_wound: '',
  fear: '',
  lie: '',
  current_stage_index: 0,
  psychological_stages: [],
  reflection_points: [],
})

const currentStageDetail = (arc) => {
  if (arc.psychological_stages && arc.psychological_stages.length > arc.current_stage_index) {
    return arc.psychological_stages[arc.current_stage_index]
  }
  return null
}

const addPsychologicalStage = () => {
  newArc.value.psychological_stages.push({
    stage_name: '',
    direction: 'growth',
    description: '',
    required_experiences_str: '',
    required_experiences: [],
  })
}

const openArc = (index) => {
  editingIndex.value = index
  const arc = characterArcs.value[index]
  newArc.value = JSON.parse(JSON.stringify(arc))
  newArc.value.psychological_stages = newArc.value.psychological_stages.map(stage => ({
    ...stage,
    required_experiences_str: stage.required_experiences.join(', '),
  }))
  showAddDialog.value = true
}

const saveArc = () => {
  if (!newArc.value.arc_id || !newArc.value.character_name) {
    toast.add({
      severity: 'error',
      summary: '保存失败',
      detail: '人物弧 ID 和角色名称不能为空',
      life: 3000,
    })
    return
  }

  // 转换 required_experiences
  newArc.value.psychological_stages = newArc.value.psychological_stages.map(stage => ({
    ...stage,
    required_experiences: stage.required_experiences_str
      ? stage.required_experiences_str.split(',').map(s => s.trim()).filter(Boolean)
      : [],
  }))

  if (editingIndex.value >= 0) {
    worldStore.characterArcs[editingIndex.value] = newArc.value
    toast.add({
      severity: 'success',
      summary: '更新成功',
      detail: `${newArc.value.character_name} 的人物弧已更新`,
      life: 3000,
    })
  } else {
    worldStore.characterArcs.push(newArc.value)
    toast.add({
      severity: 'success',
      summary: '添加成功',
      detail: `${newArc.value.character_name} 的人物弧已添加`,
      life: 3000,
    })
  }

  showAddDialog.value = false
  resetForm()
}

const deleteArc = (index) => {
  const arc = characterArcs.value[index]
  worldStore.characterArcs.splice(index, 1)
  toast.add({
    severity: 'success',
    summary: '删除成功',
    detail: `${arc.character_name} 的人物弧已删除`,
    life: 3000,
  })
}

const nextStage = (arcIndex) => {
  if (worldStore.characterArcs[arcIndex].current_stage_index < worldStore.characterArcs[arcIndex].psychological_stages.length - 1) {
    worldStore.characterArcs[arcIndex].current_stage_index++
    toast.add({
      severity: 'success',
      summary: '阶段推进',
      detail: '人物已进入下一心理阶段',
      life: 3000,
    })
  }
}

const resetForm = () => {
  editingIndex.value = -1
  newArc.value = {
    arc_id: '',
    character_id: '',
    character_name: '',
    identity: '',
    core_desire: '',
    psychological_wound: '',
    fear: '',
    lie: '',
    current_stage_index: 0,
    psychological_stages: [],
    reflection_points: [],
  }
}

onMounted(() => {
  showAddDialog.value = false
})
</script>
