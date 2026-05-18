<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          角色生成器
        </h2>
        <p class="text-gray-400 mt-1">生成符合剧情设定的角色候选，支持多种角色类型和参数配置</p>
      </div>
      <div class="flex gap-3">
        <PBadge :value="`角色候选: ${characterCandidates.length}`" severity="info" />
        <PBadge :value="`已批准: ${approvedCount}`" severity="success" />
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 左侧：生成参数 -->
      <div class="lg:col-span-1">
        <div class="glass-card p-6 space-y-6">
          <h3 class="text-xl font-semibold flex items-center gap-2">
            <Settings class="w-5 h-5 text-neon-purple" />
            生成参数
          </h3>

          <!-- 角色类型 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">角色类型</label>
            <select 
              v-model="params.character_type"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple"
            >
              <option value="protagonist">主角</option>
              <option value="supporting">配角</option>
              <option value="antagonist">反派</option>
              <option value="npc">普通NPC</option>
            </select>
          </div>

          <!-- 生成数量 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">生成数量</label>
            <input 
              type="number" 
              v-model.number="params.count"
              min="1" 
              max="10"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple"
            />
          </div>

          <!-- 剧情线 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">剧情线</label>
            <select 
              v-model="params.arc_id"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple"
            >
              <option value="arc_hospital_truth">医院真相篇</option>
              <option value="arc_identity_mystery">身份谜团篇</option>
              <option value="arc_ancestor_secret">老宅秘闻篇</option>
              <option value="unspecified">不指定</option>
            </select>
          </div>

          <!-- 创意参数 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">创意参数</label>
            <input 
              type="range" 
              v-model.number="params.creativity"
              min="0" 
              max="100"
              class="w-full accent-neon-purple"
            />
            <div class="flex justify-between text-xs text-gray-500 mt-1">
              <span>保守</span>
              <span>{{ params.creativity }}</span>
              <span>创意</span>
            </div>
          </div>

          <!-- 生成按钮 -->
          <div class="flex gap-3">
            <button
              @click="generateCharacter"
              :disabled="isGenerating"
              class="flex-1 bg-gradient-to-r from-neon-purple to-neon-pink text-white py-3 px-6 rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-purple/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles class="w-5 h-5 mr-2" />
              {{ isGenerating ? '生成中...' : '生成角色候选' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧：候选展示 -->
      <div class="lg:col-span-2 space-y-4">
        <div v-if="characterCandidates.length === 0" class="glass-card p-12 text-center">
          <Users class="w-16 h-16 mx-auto text-gray-500 mb-4" />
          <h3 class="text-xl font-semibold text-gray-400 mb-2">暂无候选角色</h3>
          <p class="text-gray-500 mb-6">点击左侧生成按钮开始生成你的第一个角色吧！</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="candidate in characterCandidates"
            :key="candidate.candidate_id"
            class="glass-card p-6 hover:border-neon-purple/50 transition-all"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <h4 class="text-lg font-semibold text-white">{{ candidate.name }}</h4>
                <p class="text-sm text-gray-400">{{ candidate.role }}</p>
              </div>
              <div class="flex gap-2">
                <button
                  @click="editCharacter(candidate)"
                  class="p-2 rounded-lg bg-noir-700 hover:bg-noir-600 text-gray-300 transition-colors"
                  title="编辑"
                >
                  <Pencil class="w-4 h-4" />
                </button>
                <button
                  @click="validateCharacter(candidate)"
                  class="p-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 transition-colors"
                  title="校验"
                >
                  <CheckCircle class="w-4 h-4" />
                </button>
                <button
                  @click="approveCharacter(candidate.candidate_id)"
                  class="p-2 rounded-lg bg-green-500/20 hover:bg-green-500/30 text-green-400 transition-colors"
                  title="批准"
                >
                  <ThumbsUp class="w-4 h-4" />
                </button>
                <button
                  @click="rejectCharacter(candidate.candidate_id)"
                  class="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors"
                  title="拒绝"
                >
                  <X class="w-4 h-4" />
                </button>
              </div>
            </div>

            <p class="text-gray-300 mb-4">{{ candidate.summary }}</p>

            <!-- 技能属性 -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <div class="bg-noir-800/50 p-3 rounded-lg">
                <div class="text-xs text-gray-500 mb-1">观察力</div>
                <div class="text-lg font-bold text-neon-purple">{{ candidate.skills?.observation || 0 }}</div>
              </div>
              <div class="bg-noir-800/50 p-3 rounded-lg">
                <div class="text-xs text-gray-500 mb-1">社交能力</div>
                <div class="text-lg font-bold text-neon-pink">{{ candidate.skills?.social || 0 }}</div>
              </div>
              <div class="bg-noir-800/50 p-3 rounded-lg">
                <div class="text-xs text-gray-500 mb-1">逻辑</div>
                <div class="text-lg font-bold text-neon-cyan">{{ candidate.skills?.logic || 0 }}</div>
              </div>
              <div class="bg-noir-800/50 p-3 rounded-lg">
                <div class="text-xs text-gray-500 mb-1">勇气</div>
                <div class="text-lg font-bold text-amber-400">{{ candidate.skills?.courage || 0 }}</div>
              </div>
            </div>

            <!-- 状态标签 -->
            <div class="flex flex-wrap gap-2 mb-2">
              <span
                v-for="trait in candidate.traits"
                :key="trait"
                class="px-3 py-1 rounded-full text-xs bg-noir-700 text-gray-300"
              >
                {{ trait }}
              </span>
            </div>
            
            <!-- 校验状态 -->
            <div v-if="candidate.validation_report" class="mt-2 text-xs text-gray-400">
              校验得分: {{ candidate.validation_report.score }}/100
              <span :class="candidate.validation_report.errors?.length ? 'text-red-400' : 'text-green-400'">
                ({{ candidate.validation_report.errors?.length ? '未通过' : '已通过' }})
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <PDialog
      v-model:visible="showEditDialog"
      header="编辑角色"
      :modal="true"
      class="w-full max-w-2xl"
    >
      <div v-if="editForm" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-400 mb-1">姓名</label>
          <input v-model="editForm.name" class="w-full bg-noir-800 border border-noir-600 rounded-lg p-2 text-white" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">角色定位</label>
          <input v-model="editForm.role" class="w-full bg-noir-800 border border-noir-600 rounded-lg p-2 text-white" />
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">简介</label>
          <textarea v-model="editForm.summary" rows="3" class="w-full bg-noir-800 border border-noir-600 rounded-lg p-2 text-white"></textarea>
        </div>
        <div>
          <label class="block text-sm text-gray-400 mb-1">技能 - 观察力</label>
          <input type="number" v-model.number="editForm.skills.observation" min="0" max="100" class="w-full bg-noir-800 border border-noir-600 rounded-lg p-2 text-white" />
        </div>
      </div>
      <template #footer>
        <PButton label="取消" severity="secondary" @click="showEditDialog = false" />
        <PButton label="保存" @click="saveEdit" />
      </template>
    </PDialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useWorldStore } from '@/stores/world'
import { useGeneratorStore } from '@/stores/generator'
import { Users, Sparkles, Pencil, CheckCircle, ThumbsUp, X, Settings } from 'lucide-vue-next'

const worldStore = useWorldStore()
const generatorStore = useGeneratorStore()
const toast = useToast()

const params = ref({
  character_type: 'supporting',
  count: 3,
  arc_id: 'arc_hospital_truth',
  creativity: 50
})

const editingCandidate = ref(null)
const showEditDialog = ref(false)
const editForm = ref({})

const characterCandidates = computed(() => generatorStore.characterCandidates)
const isGenerating = computed(() => generatorStore.isGenerating)
const approvedCount = computed(() => characterCandidates.value.filter(c => c.status === 'approved').length)

const generateCharacter = async () => {
  generatorStore.setGenerating(true)
  
  setTimeout(() => {
    const mockCandidates = generateMockCandidates()
    generatorStore.addCandidates(mockCandidates)
    generatorStore.setGenerating(false)
    toast.add({ severity: 'success', summary: '生成完成', detail: `已生成 ${params.value.count} 个角色候选`, life: 3000 })
  }, 1500)
}

const generateMockCandidates = () => {
  const traits = ['敏锐', '强势', '有职业执念', '冷静', '谨慎', '好奇心强', '记忆力超群', '神秘', '阴暗', '阳光']
  
  const names = ['陈默', '林薇', '张磊', '王芳', '李明']
  const roles = ['私家侦探', '警察', '记者', '医生', '教师']
  const summaries = [
    '一个追查旧案的侦探，在调查过程中逐渐发现自己与事件的关联',
    '警局的老刑警，看似粗犷但心思缜密，掌握着很多不为人知的秘密',
    '地方新闻记者，职业敏感，总是能挖到第一手消息但容易卷入麻烦',
    '心理医生，善于观察人心，自己却藏着一个深埋心底的秘密',
    '退休警察，看起来普通但经历丰富，能提供重要线索'
  ]

  const candidates = []
  for (let i = 0; i < params.value.count; i++) {
    const roleTraits = []
    for (let j = 0; j < 3; j++) {
      const randomIndex = Math.floor(Math.random() * traits.length)
      roleTraits.push(traits[randomIndex])
    }

    candidates.push({
      candidate_type: 'character',
      name: names[Math.floor(Math.random() * names.length)],
      role: roles[Math.floor(Math.random() * roles.length)],
      agent_type: 'full_npc_agent',
      narrative_function: 'connector',
      summary: summaries[Math.floor(Math.random() * summaries.length)],
      traits: [...new Set(roleTraits)],
      goals: {
        short_term: '找到案件的关键线索',
        long_term: '查明当年事件的真相'
      },
      skills: {
        observation: Math.floor(Math.random() * 40) + 60,
        social: Math.floor(Math.random() * 40) + 60,
        logic: Math.floor(Math.random() * 40) + 60,
        courage: Math.floor(Math.random() * 40) + 60
      },
      generator: 'CharacterGenerator'
    })
  }

  return candidates
}

const editCharacter = (candidate) => {
  editingCandidate.value = candidate
  editForm.value = JSON.parse(JSON.stringify(candidate))
  showEditDialog.value = true
}

const saveEdit = () => {
  if (editingCandidate.value && editForm.value.name) {
    generatorStore.updateCandidate(editingCandidate.value.candidate_id, editForm.value)
    showEditDialog.value = false
    toast.add({ severity: 'success', summary: '编辑成功', detail: '角色信息已更新', life: 3000 })
  }
}

const validateCharacter = (candidate) => {
  const report = generatorStore.validateCandidate(candidate.candidate_id)
  if (report) {
    toast.add({
      severity: report.errors?.length ? 'error' : 'success',
      summary: report.errors?.length ? '校验失败' : '校验通过',
      detail: `得分: ${report.score}/100`,
      life: 3000
    })
  }
}

const approveCharacter = (candidateId) => {
  generatorStore.approveCandidate(candidateId)
  toast.add({ severity: 'success', summary: '已批准', detail: '角色已加入候选列表', life: 3000 })
}

const rejectCharacter = (candidateId) => {
  generatorStore.rejectCandidate(candidateId)
  toast.add({ severity: 'info', summary: '已拒绝', detail: '角色已从列表中移除', life: 3000 })
}
</script>

<style scoped>
.glass-card {
  background: rgba(30, 30, 40, 0.8);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.glass-card:hover {
  border-color: rgba(139, 92, 246, 0.5);
}

.bg-noir-800 {
  background-color: rgba(45, 45, 60, 0.8);
}

.bg-noir-700 {
  background-color: rgba(55, 55, 70, 0.8);
}

.bg-noir-600 {
  background-color: rgba(65, 65, 80, 0.8);
}

.border-noir-600 {
  border-color: rgba(100, 100, 120, 0.6);
}

.text-neon-purple {
  color: #a855f7;
}

.text-neon-pink {
  color: #ec4899;
}

.text-neon-cyan {
  color: #06b6d4;
}

.bg-gradient-to-r {
  background: linear-gradient(to right, var(--tw-gradient-stops));
}

.from-neon-purple {
  --tw-gradient-from: #a855f7;
}

.to-neon-pink {
  --tw-gradient-to: #ec4899;
}

.accent-neon-purple {
  accent-color: #a855f7;
}

.hover\:shadow-neon-purple\/30:hover {
  box-shadow: 0 10px 40px rgba(168, 85, 247, 0.3);
}
</style>
