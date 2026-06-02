<template>
  <div class="space-y-8">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          角色管理
        </h2>
        <p class="text-gray-400 mt-1">创建和管理小说中的角色</p>
      </div>
      <PButton label="添加角色" icon="pi pi-plus" @click="openAddDialog" />
    </div>

    <!-- 角色列表 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="(character, index) in characters"
        :key="character.character_id || character.id || index"
        class="glass-card p-6 hover-lift cursor-pointer group"
        @click="openCharacter(index)"
      >
        <!-- 角色头部 -->
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-4">
            <div
              class="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl font-bold"
              :class="getTypeColor(character.agent_type)"
            >
              {{ (character.name || '?').charAt(0) }}
            </div>
            <div>
              <h3 class="text-lg font-semibold">{{ character.name || '未命名' }}</h3>
              <span class="text-sm text-gray-400">{{ character.role || '-' }}</span>
            </div>
          </div>
          <PBadge
            :value="getTypeLabel(character.agent_type)"
            :class="getBadgeClass(character.agent_type)"
          />
        </div>

        <!-- 性格标签 -->
        <div class="flex flex-wrap gap-2 mb-4">
          <span
            v-for="trait in (character.traits || []).slice(0, 3)"
            :key="trait"
            class="px-2 py-1 rounded-lg text-xs bg-noir-700 text-gray-300"
          >
            {{ trait }}
          </span>
        </div>

        <!-- 技能雷达图 -->
        <div class="flex items-center justify-center mb-4">
          <div class="grid grid-cols-4 gap-2 text-center">
            <div
              v-for="(value, skill) in (character.skills || {})"
              :key="skill"
              class="flex flex-col items-center"
            >
              <div
                class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                :class="getSkillColor(value)"
              >
                {{ value }}
              </div>
              <span class="text-xs text-gray-500 mt-1">{{ getSkillLabel(skill) }}</span>
            </div>
          </div>
        </div>

        <!-- 短期目标 -->
        <div class="p-3 rounded-xl bg-noir-800/50">
          <p class="text-xs text-gray-500 mb-1">短期目标</p>
          <p class="text-sm text-gray-300 line-clamp-2">{{ character.goals?.short_term || '-' }}</p>
        </div>

        <!-- 悬停操作按钮 -->
        <div class="mt-4 flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <PButton
            icon="pi pi-pencil"
            text
            size="small"
            class="p-button-text"
            @click.stop="openCharacter(index)"
          />
          <PButton
            icon="pi pi-trash"
            text
            size="small"
            class="p-button-text p-button-danger"
            @click.stop="deleteCharacter(index)"
          />
        </div>
      </div>

      <!-- 添加角色卡片 -->
      <div
        class="glass-card p-6 hover-lift flex flex-col items-center justify-center cursor-pointer border-dashed border-2 border-noir-600 hover:border-neon-purple transition-colors"
        @click="openAddDialog"
      >
        <div class="w-14 h-14 rounded-2xl bg-noir-700 flex items-center justify-center mb-4 group-hover:bg-neon-purple/20 transition-colors">
          <Plus class="w-7 h-7 text-gray-400 group-hover:text-neon-purple transition-colors" />
        </div>
        <p class="text-gray-400 font-medium">添加新角色</p>
      </div>
    </div>

    <!-- 角色编辑弹窗 -->
    <PDialog
      v-model:visible="showAddDialog"
      :header="editingIndex >= 0 ? '编辑角色' : '添加新角色'"
      :modal="true"
      class="w-full max-w-3xl"
      contentStyle="background: #2a2d35; border: 1px solid #374151"
    >
      <div class="space-y-6">
        <!-- 基本信息 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">角色 ID</label>
            <PInputText
              v-model="newCharacter.character_id"
              class="w-full input-dark"
              placeholder="例如：char_linzho"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">角色姓名</label>
            <PInputText
              v-model="newCharacter.name"
              class="w-full input-dark"
              placeholder="例如：林舟"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">角色类型</label>
            <PDropdown
              v-model="newCharacter.agent_type"
              :options="agentTypeOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="选择类型"
              class="w-full"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">角色定位</label>
            <PInputText
              v-model="newCharacter.role"
              class="w-full input-dark"
              placeholder="例如：protagonist"
            />
          </div>
        </div>

        <!-- 性格标签 -->
        <div>
          <label class="text-sm text-gray-400 block mb-2">性格特征</label>
          <div class="flex flex-wrap gap-2 mb-3">
            <span
              v-for="(trait, i) in newCharacter.traits"
              :key="i"
              class="px-3 py-1 rounded-full text-sm bg-noir-700 text-gray-300 flex items-center gap-2"
            >
              {{ trait }}
              <button class="hover:text-neon-pink" @click="newCharacter.traits.splice(i, 1)">
                ×
              </button>
            </span>
          </div>
          <div class="flex gap-2">
            <PInputText
              v-model="newTrait"
              class="input-dark flex-1"
              placeholder="添加性格标签..."
              @keyup.enter="addTrait"
            />
            <PButton label="添加" text @click="addTrait" />
          </div>
        </div>

        <!-- 技能值 -->
        <div>
          <label class="text-sm text-gray-400 block mb-3">技能值</label>
          <div class="grid grid-cols-4 gap-4">
            <div v-for="(value, skill) in newCharacter.skills" :key="skill">
              <label class="text-xs text-gray-500 block mb-2">{{ getSkillLabel(skill) }}</label>
              <input
                type="range"
                v-model.number="newCharacter.skills[skill]"
                min="0"
                max="100"
                class="w-full accent-neon-purple"
              />
              <div class="text-center text-sm text-neon-purple font-bold">{{ value }}</div>
            </div>
          </div>
        </div>

        <!-- 目标 -->
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">短期目标</label>
            <PTextarea
              v-model="newCharacter.goals.short_term"
              class="w-full input-dark"
              rows="3"
              placeholder="角色的短期目标..."
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">长期目标</label>
            <PTextarea
              v-model="newCharacter.goals.long_term"
              class="w-full input-dark"
              rows="3"
              placeholder="角色的长期目标..."
            />
          </div>
        </div>
      </div>

      <template #footer>
        <PButton label="取消" severity="secondary" text @click="closeDialog" />
        <PButton label="保存" @click="saveCharacter" />
      </template>
    </PDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useWorldStore } from '@/stores/world'
import { Plus } from 'lucide-vue-next'

const worldStore = useWorldStore()

const characters = computed(() => worldStore.characters)

const showAddDialog = ref(false)
const newTrait = ref('')

const createEmptyCharacter = () => ({
  character_id: '',
  name: '',
  role: '',
  agent_type: 'core_agent',
  traits: [],
  goals: {
    short_term: '',
    long_term: '',
  },
  skills: {
    observation: 50,
    social: 50,
    courage: 50,
    logic: 50,
  },
})

const normalizeCharacterForEdit = (character = {}) => ({
  ...createEmptyCharacter(),
  ...character,
  character_id: character.character_id || character.id || '',
  traits: character.traits || character.personality?.traits || [],
  goals: {
    ...createEmptyCharacter().goals,
    ...(character.goals || {}),
  },
  skills: {
    ...createEmptyCharacter().skills,
    ...(character.skills || {}),
  },
})

const newCharacter = ref(createEmptyCharacter())

const agentTypeOptions = [
  { label: '核心主角', value: 'core_agent' },
  { label: '完整 NPC', value: 'full_npc_agent' },
  { label: '半响应 NPC', value: 'semi_agent_npc' },
  { label: '被动响应 NPC', value: 'reactive_npc' },
  { label: '背景 NPC', value: 'background_npc' },
]

function getTypeColor(type) {
  const colors = {
    core_agent: 'bg-gradient-to-br from-neon-purple/30 to-neon-pink/30',
    full_npc_agent: 'bg-gradient-to-br from-neon-blue/30 to-neon-cyan/30',
    semi_agent_npc: 'bg-gradient-to-br from-amber-500/30 to-orange-500/30',
    reactive_npc: 'bg-gradient-to-br from-gray-500/30 to-gray-600/30',
    background_npc: 'bg-gradient-to-br from-gray-600/30 to-gray-700/30',
  }
  return colors[type] || colors.background_npc
}

function getTypeLabel(type) {
  const labels = {
    core_agent: '核心主角',
    full_npc_agent: '完整 NPC',
    semi_agent_npc: '半响应 NPC',
    reactive_npc: '被动响应',
    background_npc: '背景',
  }
  return labels[type] || type
}

function getBadgeClass(type) {
  if (type === 'core_agent') return 'bg-purple-500/20 text-purple-400'
  if (type === 'full_npc_agent') return 'bg-blue-500/20 text-blue-400'
  if (type === 'semi_agent_npc') return 'bg-amber-500/20 text-amber-400'
  return 'bg-gray-500/20 text-gray-400'
}

function getSkillLabel(skill) {
  const labels = {
    observation: '观察',
    social: '社交',
    courage: '勇气',
    logic: '逻辑',
  }
  return labels[skill] || skill
}

function getSkillColor(value) {
  if (value >= 70) return 'bg-green-500/30 text-green-400'
  if (value >= 50) return 'bg-blue-500/30 text-blue-400'
  if (value >= 30) return 'bg-amber-500/30 text-amber-400'
  return 'bg-red-500/30 text-red-400'
}

function addTrait() {
  if (newTrait.value.trim() && !newCharacter.value.traits.includes(newTrait.value.trim())) {
    newCharacter.value.traits.push(newTrait.value.trim())
    newTrait.value = ''
  }
}

const editingIndex = ref(-1)

function resetForm() {
  editingIndex.value = -1
  newTrait.value = ''
  newCharacter.value = createEmptyCharacter()
}

function openAddDialog() {
  resetForm()
  showAddDialog.value = true
}

function closeDialog() {
  showAddDialog.value = false
  resetForm()
}

function openCharacter(index) {
  editingIndex.value = index
  const char = characters.value[index]
  newCharacter.value = normalizeCharacterForEdit(JSON.parse(JSON.stringify(char)))
  showAddDialog.value = true
}

function getCurrentWorldId() {
  return worldStore.worldBible?.world_id || worldStore.worldId || ''
}

async function persistCharacters() {
  const worldId = getCurrentWorldId()
  if (!worldId) return

  const response = await fetch(`http://localhost:8421/api/worlds/${worldId}/characters`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      characters: worldStore.characters,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.detail?.message || error?.detail || '角色保存到后端失败')
  }
}

async function deleteCharacter(index) {
  if (confirm('确定删除这个角色吗？')) {
    worldStore.removeCharacter(index)
    try {
      await persistCharacters()
    } catch (error) {
      alert(`角色已从前端删除，但同步到模拟配置失败：${error.message}`)
    }
  }
}

async function saveCharacter() {
  const character = normalizeCharacterForEdit(newCharacter.value)
  character.character_id = character.character_id.trim()
  character.name = character.name.trim()
  character.id = character.character_id

  if (!character.character_id || !character.name) {
    alert('请填写角色 ID 和角色姓名')
    return
  }

  if (editingIndex.value >= 0) {
    worldStore.updateCharacter(editingIndex.value, character)
  } else {
    worldStore.addCharacter(character)
  }

  try {
    await persistCharacters()
    closeDialog()
  } catch (error) {
    alert(`角色已保存到前端，但同步到模拟配置失败：${error.message}`)
  }
}
</script>
