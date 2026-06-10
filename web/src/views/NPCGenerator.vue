<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          NPC生成器
        </h2>
        <p class="text-gray-400 mt-1">生成不同类型的NPC，包括地点NPC、线索NPC、阻碍NPC等</p>
      </div>
      <PBadge :value="`候选池: ${npcCandidates.length}`" class="bg-neon-purple/20 text-neon-purple" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 左侧：生成参数 -->
      <div class="lg:col-span-1">
        <div class="glass-card p-6 space-y-6">
          <h3 class="text-xl font-semibold flex items-center gap-2">
            <Settings class="w-5 h-5 text-neon-purple" />
            生成参数
          </h3>

          <!-- NPC类型 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">NPC类型</label>
            <select 
              v-model="params.npc_type"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="location_npc">地点NPC</option>
              <option value="clue_npc">线索NPC</option>
              <option value="obstructing_npc">阻碍NPC</option>
              <option value="witness_npc">目击者NPC</option>
              <option value="atmosphere_npc">氛围NPC</option>
            </select>
          </div>

          <!-- 叙事功能 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">叙事功能</label>
            <select 
              v-model="params.narrative_function"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="witness">目击者</option>
              <option value="gatekeeper">守门人</option>
              <option value="obstructor">阻碍者</option>
              <option value="clue_holder">线索持有者</option>
              <option value="atmosphere">氛围营造</option>
              <option value="plot_driver">剧情推动者</option>
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

          <!-- 所属地点 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">所属地点</label>
            <select 
              v-model="params.location_id"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="">选择地点</option>
              <option v-for="location in locationOptions" :key="location.value" :value="location.value">
                {{ location.label }}
              </option>
            </select>
          </div>

          <!-- 最大线索等级 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">最大线索等级</label>
            <select 
              v-model="params.max_clue_level"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="surface">表层</option>
              <option value="minor">轻度</option>
              <option value="medium">中等</option>
              <option value="major">重要</option>
              <option value="truth">核心真相</option>
            </select>
          </div>

          <!-- 生成按钮 -->
          <div class="flex gap-3">
            <button
              @click="generateNPC"
              :disabled="isGenerating"
              class="flex-1 bg-gradient-to-r from-neon-purple to-neon-pink text-white py-3 px-6 rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-purple/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles class="w-5 h-5 mr-2" />
              {{ isGenerating ? '生成中...' : '生成NPC候选' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧：候选展示 -->
      <div class="lg:col-span-2 space-y-4">
        <div v-if="npcCandidates.length === 0" class="glass-card p-12 text-center">
          <Users class="w-16 h-16 mx-auto text-gray-500 mb-4" />
          <h3 class="text-xl font-semibold text-gray-400 mb-2">暂无候选NPC</h3>
          <p class="text-gray-500 mb-6">点击左侧生成NPC按钮开始生成你的第一个NPC吧！</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="candidate in npcCandidates"
            :key="candidate.candidate_id"
            class="glass-card p-6 hover:border-neon-purple/50 transition-all"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <h4 class="text-lg font-semibold text-white">{{ candidate.name }}</h4>
                <p class="text-sm text-gray-400">{{ candidate.role }}</p>
              </div>
              <div class="flex items-center gap-3">
                <span class="px-2 py-1 rounded-full text-xs bg-noir-700 text-gray-300">
                  {{ candidate.type }}
                </span>
                <span class="px-2 py-1 rounded-full text-xs bg-blue-500/20 text-blue-400">
                  {{ candidate.narrative_function }}
                </span>
                <div class="flex gap-2">
                  <button
                    @click="validateNPC(candidate)"
                    class="p-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 transition-colors"
                    title="校验"
                  >
                    <CheckCircle class="w-4 h-4" />
                  </button>
                  <button
                    @click="approveNPC(candidate.candidate_id)"
                    class="p-2 rounded-lg bg-green-500/20 hover:bg-green-500/30 text-green-400 transition-colors"
                    title="批准"
                  >
                    <ThumbsUp class="w-4 h-4" />
                  </button>
                  <button
                    @click="rejectNPC(candidate.candidate_id)"
                    class="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors"
                    title="拒绝"
                  >
                    <X class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>

            <div class="mb-4">
              <div class="text-sm text-gray-500 mb-1">所属地点</div>
              <div class="text-white">{{ candidate.location_id }}</div>
            </div>

            <!-- 个性标签 -->
            <div class="mb-4">
              <div class="text-sm text-gray-500 mb-2">个性特点</div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="(trait, idx) in candidate.personality?.split('、')"
                  :key="idx"
                  class="px-3 py-1 rounded-full text-xs bg-noir-700 text-gray-300"
                >
                  {{ trait }}
                </span>
              </div>
            </div>

            <!-- 已知信息 -->
            <div v-if="candidate.knows && candidate.knows.length > 0" class="mb-4">
              <div class="text-sm text-gray-500 mb-2">已知信息</div>
              <div class="space-y-2">
                <div
                  v-for="(fact, idx) in candidate.knows"
                  :key="idx"
                  class="p-3 rounded-lg bg-noir-800/50"
                >
                  <div class="text-sm text-gray-300 mb-1">{{ fact.content }}</div>
                  <div class="text-xs text-gray-500">线索等级: {{ fact.clue_level || 'unknown' }}</div>
                </div>
              </div>
            </div>

            <!-- 可获得话题 -->
            <div v-if="candidate.first_available_topics && candidate.first_available_topics.length > 0">
              <div class="text-sm text-gray-500 mb-2">可获得话题</div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="topic in candidate.first_available_topics"
                  :key="topic"
                  class="px-3 py-1 rounded-full text-xs bg-neon-purple/20 text-neon-purple"
                >
                  {{ topic }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWorldStore } from '@/stores/world'
import { useGeneratorStore } from '@/stores/generator'
import { generatorsApi } from '@/lib/api'
import { Settings, Users, Sparkles, CheckCircle, ThumbsUp, X } from 'lucide-vue-next'

const worldStore = useWorldStore()
const generatorStore = useGeneratorStore()

const params = ref({
  npc_type: 'witness_npc',
  narrative_function: 'witness',
  count: 3,
  location_id: '',
  max_clue_level: 'medium'
})

const npcCandidates = computed(() => generatorStore.npcCandidates)
const isGenerating = computed(() => generatorStore.isGenerating)
const locationOptions = computed(() => (worldStore.locations || []).map(location => ({
  value: location.location_id || location.id,
  label: location.name || location.location_id || location.id,
})).filter(location => location.value))

const generateNPC = async () => {
  generatorStore.setGenerating(true)
  try {
    const currentWorldId = worldStore.worldBible?.world_id || worldStore.worldId
    if (!currentWorldId) {
      throw new Error('请先在世界总览中选择一个世界')
    }
    const data = await generatorsApi.npcs({
      world_id: currentWorldId,
      count: params.value.count,
      npc_type: params.value.npc_type,
      location_id: params.value.location_id,
      narrative_function: params.value.narrative_function,
    })
    if (!data?.success || !Array.isArray(data.candidates)) {
      throw new Error(data?.detail || data?.message || 'NPC生成失败')
    }
    generatorStore.addCandidates(data.candidates)
    generatorStore.addLog(`返回 ${data.candidates.length} 个 NPC 候选`)
  } catch (error) {
    generatorStore.addLog(`NPC生成失败: ${error?.message || 'unknown error'}`)
    alert(`NPC生成失败：${error?.message || '请检查后端服务'}`)
  } finally {
    generatorStore.setGenerating(false)
  }
}

const validateNPC = (candidate) => {
  generatorStore.validateCandidate(candidate.candidate_id)
}

const approveNPC = (candidateId) => {
  generatorStore.approveCandidate(candidateId)
}

const rejectNPC = (candidateId) => {
  generatorStore.rejectCandidate(candidateId)
}
</script>
