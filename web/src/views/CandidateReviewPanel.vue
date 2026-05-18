<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          候选审核面板
        </h2>
        <p class="text-gray-400 mt-1">审核、编辑、确认所有生成的候选内容，统一管理</p>
      </div>
      <div class="flex gap-3">
        <PBadge :value="`待处理: ${pendingCandidates.length}`" severity="warning" />
        <PBadge :value="`已验证: ${validatedCandidates.length}`" severity="info" />
        <PBadge :value="`已批准: ${approvedCandidates.length}`" severity="success" />
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <div class="text-3xl font-bold text-neon-purple mb-1">{{ candidates.length }}</div>
        <div class="text-sm text-gray-400">总候选数</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-3xl font-bold text-yellow-400 mb-1">{{ pendingCandidates.length }}</div>
        <div class="text-sm text-gray-400">待处理</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-3xl font-bold text-blue-400 mb-1">{{ validatedCandidates.length }}</div>
        <div class="text-sm text-gray-400">已验证</div>
      </div>
      <div class="glass-card p-4">
        <div class="text-3xl font-bold text-green-400 mb-1">{{ approvedCandidates.length }}</div>
        <div class="text-sm text-gray-400">已批准</div>
      </div>
    </div>

    <!-- 筛选和操作栏 -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <PDropdown v-model="filterType" :options="typeOptions" optionLabel="label" optionValue="value" placeholder="筛选类型" class="w-48" />
        <PDropdown v-model="filterStatus" :options="statusOptions" optionLabel="label" optionValue="value" placeholder="筛选状态" class="w-48" />
      </div>
      <div class="flex items-center gap-2">
        <PButton
          v-if="selectedCandidates.length > 0"
          label="批量验证"
          icon="pi pi-check"
          severity="info"
          @click="batchValidate"
        />
        <PButton
          label="批量批准"
          icon="pi pi-check-circle"
          severity="success"
          @click="batchApprove"
        />
        <PButton
          label="批量入库"
          icon="pi pi-save"
          severity="success"
          @click="batchCommit"
        />
        <PButton
          label="清空候选"
          icon="pi pi-trash"
          severity="danger"
          @click="clearAll"
        />
      </div>
    </div>

    <!-- 候选列表 -->
    <div class="space-y-4">
      <div v-if="filteredCandidates.length === 0" class="glass-card p-12 text-center">
        <i class="pi pi-inbox text-6xl text-gray-500 mb-4"></i>
        <h3 class="text-xl font-semibold text-gray-400 mb-2">暂无待审核候选</h3>
        <p class="text-gray-500 mb-6">前往各生成器页面创建你的第一个候选吧！</p>
      </div>

      <TransitionGroup name="list">
        <div
          v-for="candidate in filteredCandidates"
          :key="candidate.candidate_id"
          class="glass-card p-6 hover:border-neon-purple/50 transition-all"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-start gap-4">
              <input
                type="checkbox"
                v-model="selectedCandidates"
                :value="candidate.candidate_id"
                class="mt-1 w-5 h-5 accent-neon-purple rounded"
              />
              <div>
                <h4 class="text-lg font-semibold text-white">
                  {{ candidate.name || candidate.clue_id || candidate.candidate_id }}
                </h4>
                <p class="text-sm text-gray-400">{{ getCandidateTypeLabel(candidate.candidate_type) }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <PBadge
                :value="getStatusLabel(candidate.status)"
                :severity="getStatusSeverity(candidate.status)"
              />
              <PButton
                icon="pi pi-pencil"
                severity="secondary"
                text
                size="small"
                @click="editCandidate(candidate)"
                tooltip="编辑"
              />
              <PButton
                icon="pi pi-check"
                severity="info"
                text
                size="small"
                @click="validateCandidate(candidate)"
                :disabled="candidate.status === 'validated' || candidate.status === 'approved'"
                tooltip="验证"
              />
              <PButton
                icon="pi pi-check-circle"
                severity="success"
                text
                size="small"
                @click="approveCandidate(candidate.candidate_id)"
                :disabled="candidate.status === 'approved'"
                tooltip="批准"
              />
              <PButton
                icon="pi pi-times"
                severity="danger"
                text
                size="small"
                @click="rejectCandidate(candidate.candidate_id)"
                tooltip="拒绝"
              />
            </div>
          </div>

          <!-- 候选详细信息 -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <!-- 左侧：基础信息 -->
            <div class="space-y-3">
              <div v-if="candidate.summary">
                <div class="text-sm text-gray-500 mb-1">简介</div>
                <div class="text-gray-300">{{ candidate.summary }}</div>
              </div>
              <div v-else-if="candidate.content">
                <div class="text-sm text-gray-500 mb-1">内容</div>
                <div class="text-gray-300">{{ candidate.content }}</div>
              </div>
              <div v-if="candidate.role">
                <div class="text-sm text-gray-500 mb-1">角色</div>
                <div class="text-gray-300">{{ candidate.role }}</div>
              </div>
              <div v-if="candidate.location_id">
                <div class="text-sm text-gray-500 mb-1">所属地点</div>
                <div class="text-gray-300">{{ candidate.location_id }}</div>
              </div>
              <div v-if="candidate.arc_id">
                <div class="text-sm text-gray-500 mb-1">所属剧情线</div>
                <div class="text-gray-300">{{ candidate.arc_id }}</div>
              </div>
            </div>

            <!-- 右侧：特性和技能 -->
            <div class="space-y-3">
              <div v-if="candidate.traits && candidate.traits.length > 0">
                <div class="text-sm text-gray-500 mb-2">性格特点</div>
                <div class="flex flex-wrap gap-2">
                  <span
                    v-for="trait in candidate.traits"
                    :key="trait"
                    class="px-3 py-1 rounded-full text-xs bg-noir-700 text-gray-300"
                  >
                    {{ trait }}
                  </span>
                </div>
              </div>
              <div v-if="candidate.skills">
                <div class="text-sm text-gray-500 mb-2">技能</div>
                <div class="grid grid-cols-2 gap-2">
                  <div v-for="(value, skill) in candidate.skills" :key="skill" class="bg-noir-800 p-2 rounded-lg">
                    <div class="text-xs text-gray-500 capitalize">{{ skill }}</div>
                    <div class="font-bold text-neon-purple">{{ value }}</div>
                  </div>
                </div>
              </div>
              <div v-if="candidate.discover_routes && candidate.discover_routes.length > 0">
                <div class="text-sm text-gray-500 mb-2">发现路径 ({{ candidate.discover_routes.length }}条)</div>
                <div class="space-y-2">
                  <div
                    v-for="route in candidate.discover_routes"
                    :key="route.route_id"
                    class="p-2 rounded-lg bg-noir-800 text-sm"
                  >
                    <span class="text-neon-cyan">{{ route.action_type }}</span>
                    <span class="text-gray-400"> - {{ route.target }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 验证报告 -->
          <div v-if="candidate.validation_report" class="mt-4 p-4 rounded-xl bg-noir-800/50">
            <div class="text-sm font-medium text-gray-400 mb-2">验证报告</div>
            <div class="flex items-center gap-6 text-sm flex-wrap">
              <div class="flex items-center gap-2">
                <div class="text-gray-500">完整性:</div>
                <div :class="candidate.validation_report.schema_valid ? 'text-green-400' : 'text-red-400'">
                  {{ candidate.validation_report.schema_valid ? '通过' : '失败' }}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <div class="text-gray-500">引用检查:</div>
                <div :class="candidate.validation_report.references_valid ? 'text-green-400' : 'text-red-400'">
                  {{ candidate.validation_report.references_valid ? '通过' : '失败' }}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <div class="text-gray-500">知识边界:</div>
                <div :class="candidate.validation_report.knowledge_boundary_valid ? 'text-green-400' : 'text-red-400'">
                  {{ candidate.validation_report.knowledge_boundary_valid ? '通过' : '失败' }}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <div class="text-gray-500">综合评分:</div>
                <div class="text-neon-purple font-bold">{{ candidate.validation_report.score }}/100</div>
              </div>
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useGeneratorStore } from '@/stores/generator'

const generatorStore = useGeneratorStore()

const filterType = ref('all')
const filterStatus = ref('all')
const selectedCandidates = ref([])

const typeOptions = [
  { label: '全部类型', value: 'all' },
  { label: '角色', value: 'character' },
  { label: 'NPC', value: 'npc' },
  { label: '地点', value: 'location' },
  { label: '线索', value: 'clue' },
  { label: '关系', value: 'relationship' },
  { label: '秘密', value: 'secret' }
]

const statusOptions = [
  { label: '全部状态', value: 'all' },
  { label: '刚生成', value: 'generated' },
  { label: '已编辑', value: 'edited' },
  { label: '已验证', value: 'validated' },
  { label: '已批准', value: 'approved' }
]

const candidates = computed(() => generatorStore.candidates)
const pendingCandidates = computed(() => generatorStore.pendingCandidates)
const validatedCandidates = computed(() => generatorStore.validatedCandidates)
const approvedCandidates = computed(() => generatorStore.approvedCandidates)

const filteredCandidates = computed(() => {
  let result = candidates.value
  
  if (filterType.value !== 'all') {
    result = result.filter(c => c.candidate_type === filterType.value)
  }
  
  if (filterStatus.value !== 'all') {
    result = result.filter(c => c.status === filterStatus.value)
  }
  
  return result
})

const getCandidateTypeLabel = (type) => {
  const labels = {
    character: '角色',
    npc: 'NPC',
    location: '地点',
    clue: '线索',
    relationship: '关系',
    secret: '秘密'
  }
  return labels[type] || '未知'
}

const getStatusLabel = (status) => {
  const labels = {
    generated: '刚生成',
    edited: '已编辑',
    validated: '已验证',
    approved: '已批准',
    committed: '已入库',
    rejected: '已拒绝',
    archived: '已归档'
  }
  return labels[status] || '未知'
}

const getStatusSeverity = (status) => {
  const severities = {
    generated: 'secondary',
    edited: 'warning',
    validated: 'info',
    approved: 'success',
    committed: 'success',
    rejected: 'danger',
    archived: 'info'
  }
  return severities[status] || 'secondary'
}

const editCandidate = (candidate) => {
  // 编辑候选逻辑
  console.log('编辑候选:', candidate)
}

const validateCandidate = (candidate) => {
  generatorStore.validateCandidate(candidate.candidate_id)
}

const approveCandidate = (candidateId) => {
  generatorStore.approveCandidate(candidateId)
}

const rejectCandidate = (candidateId) => {
  generatorStore.rejectCandidate(candidateId)
}

const batchValidate = () => {
  selectedCandidates.value.forEach(id => {
    generatorStore.validateCandidate(id)
  })
  selectedCandidates.value = []
}

const batchApprove = () => {
  validatedCandidates.value.forEach(candidate => {
    generatorStore.approveCandidate(candidate.candidate_id)
  })
}

const batchCommit = () => {
  approvedCandidates.value.forEach(candidate => {
    generatorStore.commitCandidate(candidate.candidate_id)
  })
}

const clearAll = () => {
  if (confirm('确定要清空所有候选吗？')) {
    generatorStore.candidates = []
  }
}
</script>

<style scoped>
.list-enter-active,
.list-leave-active {
  transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
