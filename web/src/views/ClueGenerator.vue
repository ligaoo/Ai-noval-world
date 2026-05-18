<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          线索生成器
        </h2>
        <p class="text-gray-400 mt-1">自动生成小说线索和发现路径配置，构建悬疑感</p>
      </div>
      <PBadge :value="`候选池: ${clueCandidates.length}`" class="bg-neon-purple/20 text-neon-purple" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 左侧：生成参数 -->
      <div class="lg:col-span-1">
        <div class="glass-card p-6 space-y-6">
          <h3 class="text-xl font-semibold flex items-center gap-2">
            <Settings class="w-5 h-5 text-neon-purple" />
            生成参数
          </h3>

          <!-- 所属剧情线 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">所属剧情线</label>
            <select 
              v-model="params.arc_id"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="">选择剧情线</option>
              <option value="arc_hospital_truth">旧医院真相篇</option>
              <option value="arc_identity_mystery">身份谜团</option>
              <option value="arc_sinister_past">黑暗过往</option>
            </select>
          </div>

          <!-- 线索等级 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">线索等级</label>
            <select 
              v-model="params.clue_level"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="surface">表层</option>
              <option value="minor">轻度</option>
              <option value="medium">中等</option>
              <option value="major">重要</option>
              <option value="truth">核心真相</option>
            </select>
          </div>

          <!-- 剧情阶段 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">剧情阶段</label>
            <select 
              v-model="params.stage"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple">
              <option value="setup">建立异常</option>
              <option value="investigation">调查线索</option>
              <option value="confrontation">冲突阶段</option>
              <option value="revelation">真相揭露</option>
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

          <!-- 发现路径数量 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">每条线索发现路径数</label>
            <input 
              type="number" 
              v-model.number="params.must_have_routes"
              min="1" 
              max="5"
              class="w-full bg-noir-800 border border-noir-600 rounded-lg p-3 text-white focus:outline-none focus:border-neon-purple"
            />
          </div>

          <!-- 允许的发现方式 -->
          <div>
            <label class="block text-sm text-gray-400 mb-2">允许的发现方式</label>
            <div class="flex flex-wrap gap-2">
              <label 
                v-for="type in routeTypes"
                :key="type.value"
                class="flex items-center gap-2 px-3 py-2 rounded-lg bg-noir-800 cursor-pointer hover:bg-noir-700 transition-colors"
              >
                <input 
                  type="checkbox" 
                  :value="type.value"
                  v-model="params.allowed_route_types"
                  class="w-4 h-4 accent-neon-purple"
                />
                <span class="text-sm text-gray-300">{{ type.label }}</span>
              </label>
            </div>
          </div>

          <!-- 生成按钮 -->
          <div class="flex gap-3">
            <button
              @click="generateClue"
              :disabled="isGenerating"
              class="flex-1 bg-gradient-to-r from-neon-purple to-neon-pink text-white py-3 px-6 rounded-lg font-semibold hover:shadow-lg hover:shadow-neon-purple/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles class="w-5 h-5 mr-2" />
              {{ isGenerating ? '生成中...' : '生成线索候选' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 右侧：候选展示 -->
      <div class="lg:col-span-2 space-y-4">
        <div v-if="clueCandidates.length === 0" class="glass-card p-12 text-center">
          <Search class="w-16 h-16 mx-auto text-gray-500 mb-4" />
          <h3 class="text-xl font-semibold text-gray-400 mb-2">暂无候选线索</h3>
          <p class="text-gray-500 mb-6">点击左侧生成按钮开始生成你的第一个线索吧！</p>
        </div>

        <div v-else class="space-y-4">
          <div
            v-for="candidate in clueCandidates"
            :key="candidate.candidate_id"
            class="glass-card p-6 hover:border-neon-purple/50 transition-all"
          >
            <div class="flex justify-between items-start mb-4">
              <div>
                <h4 class="text-lg font-semibold text-white">{{ candidate.name }}</h4>
                <p class="text-sm text-gray-400">{{ candidate.clue_id }}</p>
              </div>
              <div class="flex items-center gap-3">
                <span 
                  :class="[
                    'px-2 py-1 rounded-full text-xs',
                    getLevelColor(candidate.level)
                  ]"
                >
                  {{ getLevelLabel(candidate.level) }}
                </span>
                <button
                  @click="validateClue(candidate)"
                  class="p-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 transition-colors"
                  title="校验"
                >
                  <CheckCircle class="w-4 h-4" />
                </button>
                <button
                  @click="approveClue(candidate.candidate_id)"
                  class="p-2 rounded-lg bg-green-500/20 hover:bg-green-500/30 text-green-400 transition-colors"
                  title="批准"
                >
                  <ThumbsUp class="w-4 h-4" />
                </button>
                <button
                  @click="rejectClue(candidate.candidate_id)"
                  class="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors"
                  title="拒绝"
                >
                  <X class="w-4 h-4" />
                </button>
              </div>
            </div>

            <!-- 线索内容 -->
            <div class="mb-4 p-4 rounded-xl bg-noir-800/50">
              <div class="text-sm text-gray-500 mb-1">线索内容</div>
              <p class="text-gray-300">{{ candidate.content }}</p>
            </div>

            <!-- 发现路径 -->
            <div v-if="candidate.discover_routes && candidate.discover_routes.length > 0" class="mb-4">
              <div class="text-sm text-gray-500 mb-2">发现路径 ({{ candidate.discover_routes.length }}条)</div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div
                  v-for="route in candidate.discover_routes"
                  :key="route.route_id"
                  class="p-3 rounded-lg bg-noir-800/50"
                >
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm font-medium text-neon-cyan">{{ route.action_type }}</span>
                    <span class="text-xs text-gray-500">难度: {{ route.difficulty }}</span>
                  </div>
                  <div class="text-sm text-gray-400">
                    目标: {{ route.target }}
                  </div>
                  <div class="text-xs text-gray-500 mt-1">
                    地点: {{ route.location_id }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 允许阶段 -->
            <div v-if="candidate.allowed_stages && candidate.allowed_stages.length > 0">
              <div class="text-sm text-gray-500 mb-2">可发现阶段</div>
              <div class="flex flex-wrap gap-2">
                <span
                  v-for="stage in candidate.allowed_stages"
                  :key="stage"
                  class="px-3 py-1 rounded-full text-xs bg-neon-purple/20 text-neon-purple border border-neon-purple/30"
                >
                  {{ stage }}
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
import { Settings, Search, Sparkles, CheckCircle, ThumbsUp, X } from 'lucide-vue-next'

const worldStore = useWorldStore()
const generatorStore = useGeneratorStore()

const routeTypes = [
  { value: 'search', label: '搜索' },
  { value: 'observe', label: '观察' },
  { value: 'ask', label: '询问' },
  { value: 'investigate', label: '调查' }
]

const params = ref({
  arc_id: 'arc_hospital_truth',
  stage: 'investigation',
  clue_level: 'medium',
  count: 3,
  must_have_routes: 3,
  allowed_route_types: ['search', 'observe', 'ask']
})

const clueCandidates = computed(() => generatorStore.clueCandidates)
const isGenerating = computed(() => generatorStore.isGenerating)

const getLevelColor = (level) => {
  const colors = {
    surface: 'bg-gray-500/20 text-gray-300',
    minor: 'bg-blue-500/20 text-blue-300',
    medium: 'bg-yellow-500/20 text-yellow-300',
    major: 'bg-orange-500/20 text-orange-300',
    truth: 'bg-red-500/20 text-red-300'
  }
  return colors[level] || colors.surface
}

const getLevelLabel = (level) => {
  const labels = {
    surface: '表层',
    minor: '轻度',
    medium: '中等',
    major: '重要',
    truth: '核心真相'
  }
  return labels[level] || '未知'
}

const generateClue = async () => {
  generatorStore.setGenerating(true)
  
  setTimeout(() => {
    const mockCandidates = generateMockClues()
    generatorStore.addCandidates(mockCandidates)
    generatorStore.setGenerating(false)
  }, 1500)
}

const generateMockClues = () => {
  const clueTemplates = [
    {
      name: '生锈的钥匙',
      content: '一把布满锈迹的旧钥匙，看起来有些年头了，可能是某个重要房间的钥匙。',
      routes: [
        { action_type: '搜索', target: '医院大门锁', difficulty: 30 },
        { action_type: '询问', target: '老门卫', difficulty: 50 }
      ]
    },
    {
      name: '泛黄的病历',
      content: '一份已经泛黄的旧病历，上面的名字和记录都模糊不清，但能看出和某个关键人物有关。',
      routes: [
        { action_type: '搜索', target: '档案室', difficulty: 40 },
        { action_type: '观察', target: '办公桌抽屉', difficulty: 35 }
      ]
    },
    {
      name: '奇怪的脚步声',
      content: '半夜在走廊尽头会传来奇怪的脚步声，但走过去查看时却什么都没有。',
      routes: [
        { action_type: '观察', target: '走廊尽头', difficulty: 45 },
        { action_type: '询问', target: '夜班护士', difficulty: 55 }
      ]
    },
    {
      name: '上锁的档案室',
      content: '医院深处有一间被牢牢锁住的档案室，里面似乎藏着什么不可告人的秘密。',
      routes: [
        { action_type: '调查', target: '档案室', difficulty: 60 },
        { action_type: '询问', target: '院长', difficulty: 70 }
      ]
    },
    {
      name: '消失的夜班记录',
      content: '某天的夜班记录簿不翼而飞，取而代之的是一本全新的空白簿子。',
      routes: [
        { action_type: '搜索', target: '护士站', difficulty: 50 },
        { action_type: '询问', target: '护士长', difficulty: 65 }
      ]
    }
  ]

  const candidates = []
  const usedNames = new Set()

  for (let i = 0; i < params.value.count; i++) {
    const template = clueTemplates[Math.floor(Math.random() * clueTemplates.length)]
    if (usedNames.has(template.name)) continue
    usedNames.add(template.name)

    const routes = []
    const routeCount = Math.min(params.value.must_have_routes, template.routes.length)
    
    for (let j = 0; j < routeCount; j++) {
      const route = template.routes[j]
      routes.push({
        route_id: `route_${params.value.arc_id}_${template.name}_${j}`,
        action_type: route.action_type,
        target: route.target,
        difficulty: route.difficulty + Math.floor(Math.random() * 10) - 5,
        location_id: 'old_hospital_gate'
      })
    }

    candidates.push({
      candidate_type: 'clue',
      clue_id: `clue_${template.name}_${Date.now()}`,
      name: template.name,
      content: template.content,
      level: params.value.clue_level,
      arc_id: params.value.arc_id,
      allowed_stages: [params.value.stage],
      discover_routes: routes,
      generator: 'ClueGenerator'
    })
  }

  return candidates
}

const validateClue = (candidate) => {
  generatorStore.validateCandidate(candidate.candidate_id)
}

const approveClue = (candidateId) => {
  generatorStore.approveCandidate(candidateId)
}

const rejectClue = (candidateId) => {
  generatorStore.rejectCandidate(candidateId)
}
</script>
