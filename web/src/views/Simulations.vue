<template>
  <div style="max-width: 1320px; margin: 0 auto;">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px;">
      <div>
        <h2 style="font-size: 32px; font-weight: 700; margin: 0; background: linear-gradient(135deg, #60a5fa, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">模拟运行</h2>
        <p style="color: #9ca3af; margin-top: 8px;">启动单章模拟，查看状态、正文、质量、连续性、揭示预算，并执行手动改写。</p>
      </div>
      <button @click="refreshSimulations" :disabled="loading" :style="buttonStyle('#374151')">刷新列表</button>
    </div>

    <section :style="panelStyle">
      <h3 style="margin: 0 0 14px; font-size: 20px;">启动模拟</h3>
      <div style="display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px;">
        <div>
          <label :style="labelStyle">世界</label>
          <select v-model="runForm.world_id" :style="inputStyle">
            <option value="" disabled>请选择世界</option>
            <option v-for="world in worlds" :key="world.id" :value="world.id">{{ world.title || world.id }} ({{ world.id }})</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">Genre</label>
          <select v-model="runForm.genre_id" :style="inputStyle" @change="loadGenreProfile">
            <option v-for="genre in genres" :key="genreValue(genre)" :value="genreValue(genre)">{{ genreLabel(genre) }}</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">章节号</label>
          <input v-model.number="runForm.chapter_no" type="number" min="1" :style="inputStyle" />
        </div>
        <div>
          <label :style="labelStyle">目标章节</label>
          <input v-model.number="runForm.target_chapters" type="number" min="1" :style="inputStyle" />
        </div>
        <div>
          <label :style="labelStyle">Ticks</label>
          <input v-model.number="runForm.ticks" type="number" min="1" placeholder="默认" :style="inputStyle" />
        </div>
        <div>
          <label :style="labelStyle">Seed</label>
          <input v-model.number="runForm.seed" type="number" :style="inputStyle" />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px;">
        <div>
          <label :style="labelStyle">章节风格</label>
          <select v-model="runForm.quality_controls.style_focus" multiple :style="{ ...inputStyle, minHeight: '86px' }">
            <option value="悬疑推进">悬疑推进</option>
            <option value="恐怖氛围">恐怖氛围</option>
            <option value="角色冲突">角色冲突</option>
            <option value="线索密集">线索密集</option>
            <option value="慢热铺垫">慢热铺垫</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">生成强度</label>
          <select v-model="runForm.quality_controls.generation_strength" :style="inputStyle">
            <option value="保守">保守</option>
            <option value="平衡">平衡</option>
            <option value="强化">强化</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">结尾类型</label>
          <select v-model="runForm.quality_controls.ending_hook_type" :style="inputStyle">
            <option value="感官钩子">感官钩子</option>
            <option value="线索钩子">线索钩子</option>
            <option value="关系钩子">关系钩子</option>
            <option value="危险钩子">危险钩子</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">改写策略</label>
          <select v-model="runForm.quality_controls.rewrite_policy" :style="inputStyle">
            <option value="auto_once">auto_once</option>
            <option value="manual">manual</option>
            <option value="disabled">disabled</option>
          </select>
        </div>
      </div>

      <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <button @click="runSimulation" :disabled="loading || !runForm.world_id" :style="buttonStyle('#7c3aed')">{{ loading ? '运行中...' : '启动模拟' }}</button>
        <button v-if="selectedSimId" @click="refreshStatus" :disabled="loading" :style="buttonStyle('#2563eb')">刷新状态</button>
        <span v-if="status" style="color: #d1d5db; font-size: 13px;">状态：{{ status.status || '-' }} <code>{{ selectedSimId }}</code></span>
      </div>
      <div v-if="genreProfile" style="margin-top: 12px;">
        <button @click="showGenreProfile = !showGenreProfile" :style="buttonStyle('#111827')">{{ showGenreProfile ? '隐藏' : '查看' }} Genre Profile</button>
        <pre v-if="showGenreProfile" :style="preStyle">{{ formatJson(genreProfile) }}</pre>
      </div>
      <div v-if="error" style="margin-top: 12px; color: #f87171; white-space: pre-wrap;">{{ error }}</div>
    </section>

    <section style="display: grid; grid-template-columns: 320px 1fr; gap: 16px; align-items: start;">
      <div :style="panelStyle">
        <h3 style="margin: 0 0 12px; font-size: 18px; color: #93c5fd;">模拟列表</h3>
        <div v-if="!simulations.length" style="color: #9ca3af; font-size: 13px;">暂无模拟输出。</div>
        <button v-for="sim in simulations" :key="sim.id" @click="selectSimulation(sim.id)" :style="listButtonStyle(selectedSimId === sim.id)">
          <strong>{{ sim.id }}</strong><br />
          <span style="font-size: 12px; color: #9ca3af;">{{ formatTime(sim.created_at) }}</span><br />
          <span style="font-size: 12px; color: #d1d5db;">质量：{{ sim.quality_score ?? '-' }} / {{ sim.grade || '-' }}</span>
        </button>
      </div>

      <div :style="panelStyle">
        <div v-if="!selectedSimId" style="color: #9ca3af;">选择一个模拟查看详情，或启动一个新模拟。</div>
        <template v-else>
          <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; font-size: 18px; color: #c084fc;">{{ selectedSimId }}</h3>
            <button @click="loadSimulationArtifacts(selectedSimId)" :disabled="loading" :style="buttonStyle('#374151')">刷新详情</button>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
            <button v-for="tab in detailTabs" :key="tab.id" @click="activeTab = tab.id" :style="tabButtonStyle(activeTab === tab.id)">{{ tab.label }}</button>
          </div>

          <pre v-if="activeTab === 'draft'" :style="{ ...preStyle, maxHeight: '620px', color: '#e5e7eb', lineHeight: '1.7' }">{{ detail?.chapter_draft || '暂无正文' }}</pre>

          <div v-else-if="activeTab === 'rewrite'" style="display: grid; gap: 12px;">
            <label :style="labelStyle">改写意图</label>
            <textarea v-model="rewriteForm.rewrite_intent" rows="4" :style="inputStyle" placeholder="例如：加强悬疑压迫感，减少解释，保持已发生事实不变。"></textarea>
            <label style="color: #d1d5db;"><input v-model="rewriteForm.preserve_facts" type="checkbox" /> 保留事实</label>
            <label style="color: #d1d5db;"><input v-model="rewriteForm.preserve_scene_plan" type="checkbox" /> 保留场景计划</label>
            <button @click="rewriteSelectedSimulation" :disabled="loading || !rewriteForm.rewrite_intent.trim()" :style="buttonStyle('#7c3aed')">执行手动改写</button>
            <pre :style="preStyle">{{ formatJson(rewriteReport || {}) }}</pre>
          </div>

          <pre v-else :style="preStyle">{{ currentTabJson }}</pre>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { genresApi, simulationsApi, worldsApi } from '@/lib/api'

const worlds = ref([])
const genres = ref([])
const genreProfile = ref(null)
const showGenreProfile = ref(false)
const simulations = ref([])
const selectedSimId = ref('')
const detail = ref(null)
const quality = ref(null)
const qualityControls = ref(null)
const revealBudget = ref(null)
const continuity = ref(null)
const status = ref(null)
const rewriteReport = ref(null)
const activeTab = ref('draft')
const loading = ref(false)
const error = ref('')

const runForm = ref({
  world_id: '',
  mode: 'llm',
  version: '正式版V1',
  ticks: null,
  seed: 12345,
  genre_id: 'horror',
  target_chapters: 10,
  chapter_no: 1,
  quality_controls: {
    style_focus: ['悬疑推进', '恐怖氛围'],
    generation_strength: '平衡',
    ending_hook_type: '线索钩子',
    rewrite_policy: 'auto_once',
  },
})

const rewriteForm = ref({
  rewrite_intent: '',
  preserve_facts: true,
  preserve_scene_plan: true,
})

const detailTabs = [
  { id: 'draft', label: '正文' },
  { id: 'state', label: 'State' },
  { id: 'plan', label: '章节计划' },
  { id: 'quality', label: '质量' },
  { id: 'controls', label: 'Quality Controls' },
  { id: 'budget', label: 'Reveal Budget' },
  { id: 'continuity', label: 'Continuity' },
  { id: 'status', label: 'Status' },
  { id: 'rewrite', label: 'Rewrite' },
  { id: 'raw', label: 'Raw' },
]

const panelStyle = {
  background: 'rgba(42, 45, 53, 0.9)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '16px',
  padding: '20px',
  marginBottom: '20px',
}

const labelStyle = {
  fontSize: '12px',
  color: '#9ca3af',
  display: 'block',
  marginBottom: '6px',
}

const inputStyle = {
  width: '100%',
  background: '#1c1e24',
  border: '1px solid #374151',
  color: '#f3f4f6',
  padding: '9px',
  borderRadius: '8px',
}

const preStyle = {
  whiteSpace: 'pre-wrap',
  maxHeight: '520px',
  overflow: 'auto',
  background: '#111827',
  color: '#d1d5db',
  padding: '12px',
  borderRadius: '10px',
  fontSize: '12px',
}

const buttonStyle = (background) => ({
  background,
  color: 'white',
  border: '1px solid #374151',
  padding: '9px 13px',
  borderRadius: '9px',
  cursor: 'pointer',
})

const tabButtonStyle = (active) => ({
  ...buttonStyle(active ? '#2563eb' : '#111827'),
  color: active ? 'white' : '#d1d5db',
})

const listButtonStyle = (active) => ({
  display: 'block',
  width: '100%',
  textAlign: 'left',
  marginBottom: '8px',
  background: active ? '#1d4ed8' : '#111827',
  color: '#e5e7eb',
  border: '1px solid #374151',
  borderRadius: '9px',
  padding: '10px',
  cursor: 'pointer',
})

const currentTabJson = computed(() => {
  const map = {
    state: detail.value?.state,
    plan: detail.value?.chapter_plan,
    quality: quality.value,
    controls: qualityControls.value,
    budget: revealBudget.value,
    continuity: continuity.value,
    status: status.value,
    raw: { detail: detail.value, quality: quality.value, qualityControls: qualityControls.value, revealBudget: revealBudget.value, continuity: continuity.value, status: status.value },
  }
  return formatJson(map[activeTab.value] || {})
})

const formatJson = (value) => JSON.stringify(value || {}, null, 2)
const formatTime = (value) => value ? new Date(value * 1000).toLocaleString() : '-'
const genreValue = (genre) => typeof genre === 'string' ? genre : genre.id || genre.genre_id || genre.name || ''
const genreLabel = (genre) => typeof genre === 'string' ? genre : `${genre.name || genre.id || genre.genre_id}${genre.id || genre.genre_id ? ` (${genre.id || genre.genre_id})` : ''}`

const loadWorlds = async () => {
  const data = await worldsApi.list()
  worlds.value = data.worlds || []
  if (!runForm.value.world_id) runForm.value.world_id = worlds.value[0]?.id || ''
}

const loadGenres = async () => {
  const data = await genresApi.list()
  genres.value = data.genres || []
  const firstGenre = genreValue(genres.value[0])
  if (!runForm.value.genre_id && firstGenre) runForm.value.genre_id = firstGenre
  await loadGenreProfile()
}

const loadGenreProfile = async () => {
  if (!runForm.value.genre_id) return
  try {
    const data = await genresApi.profile(runForm.value.genre_id)
    genreProfile.value = data.profile || data
  } catch {
    genreProfile.value = null
  }
}

const refreshSimulations = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await simulationsApi.list()
    simulations.value = data.simulations || []
  } catch (err) {
    error.value = err.message || '读取模拟列表失败'
  } finally {
    loading.value = false
  }
}

const loadSimulationArtifacts = async (simId) => {
  if (!simId) return
  loading.value = true
  error.value = ''
  try {
    const results = await Promise.allSettled([
      simulationsApi.get(simId),
      simulationsApi.quality(simId),
      simulationsApi.qualityControls(simId),
      simulationsApi.revealBudget(simId),
      simulationsApi.continuity(simId),
      simulationsApi.status(simId),
    ])
    detail.value = results[0].status === 'fulfilled' ? results[0].value : {}
    quality.value = results[1].status === 'fulfilled' ? results[1].value : { error: results[1].reason?.message }
    qualityControls.value = results[2].status === 'fulfilled' ? results[2].value : { error: results[2].reason?.message }
    revealBudget.value = results[3].status === 'fulfilled' ? results[3].value : { error: results[3].reason?.message }
    continuity.value = results[4].status === 'fulfilled' ? results[4].value : { error: results[4].reason?.message }
    status.value = results[5].status === 'fulfilled' ? results[5].value : { status: 'no_active_runtime_status', error: results[5].reason?.message }
  } catch (err) {
    error.value = err.message || '读取模拟详情失败'
  } finally {
    loading.value = false
  }
}

const selectSimulation = async (simId) => {
  selectedSimId.value = simId
  activeTab.value = 'draft'
  rewriteReport.value = null
  await loadSimulationArtifacts(simId)
}

const refreshStatus = async () => {
  if (!selectedSimId.value) return
  try {
    status.value = await simulationsApi.status(selectedSimId.value)
  } catch (err) {
    status.value = { status: 'no_active_runtime_status', error: err.message }
  }
}

const runSimulation = async () => {
  loading.value = true
  error.value = ''
  try {
    const payload = { ...runForm.value, ticks: runForm.value.ticks || null }
    const data = await simulationsApi.run(payload)
    selectedSimId.value = data.sim_id
    status.value = { status: 'started', ...data }
    await refreshSimulations()
    await refreshStatus()
  } catch (err) {
    error.value = err.message || '启动模拟失败'
  } finally {
    loading.value = false
  }
}

const rewriteSelectedSimulation = async () => {
  if (!selectedSimId.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await simulationsApi.rewrite(selectedSimId.value, rewriteForm.value)
    rewriteReport.value = data.report || data
    await loadSimulationArtifacts(selectedSimId.value)
  } catch (err) {
    error.value = err.message || '手动改写失败'
    rewriteReport.value = { error: error.value }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.allSettled([loadWorlds(), loadGenres(), refreshSimulations()])
})
</script>
