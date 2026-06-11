<template>
  <div style="max-width: 1320px; margin: 0 auto;">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 24px;">
      <div>
        <h2 style="font-size: 32px; font-weight: 700; margin: 0; background: linear-gradient(135deg, #60a5fa, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">长篇运行</h2>
        <p style="color: #9ca3af; margin-top: 8px;">以整本书计划、状态、线索账本、真相边界和章节连续性推进长篇生成。</p>
      </div>
      <div style="display: flex; gap: 10px;">
        <button @click="refreshRuntime" :disabled="loading || !longRun" :style="buttonStyle('#374151')">刷新 Runtime</button>
        <button @click="refreshAll" :disabled="loading || !longRun" :style="buttonStyle('#1f2937')">刷新全部</button>
      </div>
    </div>

    <section :style="panelStyle">
      <h3 style="margin: 0 0 14px; font-size: 20px;">创建 / 加载 / 推进长篇</h3>
      <div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px;">
        <div>
          <label :style="labelStyle">世界</label>
          <select v-model="form.world_id" :disabled="!!longRun" :style="inputStyle">
            <option value="" disabled>请选择世界</option>
            <option v-for="world in worlds" :key="world.id" :value="world.id">{{ world.title || world.id }} ({{ world.id }})</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">目标章节数</label>
          <input v-model.number="form.target_chapters" :disabled="!!longRun" type="number" min="1" :style="inputStyle" />
        </div>
        <div>
          <label :style="labelStyle">Seed</label>
          <input v-model.number="form.seed" :disabled="!!longRun" type="number" :style="inputStyle" />
        </div>
        <div>
          <label :style="labelStyle">Genre</label>
          <select v-model="form.genre_id" :disabled="!!longRun" :style="inputStyle" @change="loadGenreProfile">
            <option v-for="genre in genres" :key="genreValue(genre)" :value="genreValue(genre)">{{ genreLabel(genre) }}</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">Long Run ID</label>
          <input v-model="loadId" placeholder="long_..." :style="inputStyle" />
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 14px;">
        <div>
          <label :style="labelStyle">章节风格</label>
          <select v-model="form.quality_controls.style_focus" multiple :disabled="!!longRun" :style="{ ...inputStyle, minHeight: '86px' }">
            <option value="悬疑推进">悬疑推进</option>
            <option value="恐怖氛围">恐怖氛围</option>
            <option value="角色冲突">角色冲突</option>
            <option value="线索密集">线索密集</option>
            <option value="慢热铺垫">慢热铺垫</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">生成强度</label>
          <select v-model="form.quality_controls.generation_strength" :disabled="!!longRun" :style="inputStyle">
            <option value="保守">保守：更忠实事件</option>
            <option value="平衡">平衡：忠实 + 文学化</option>
            <option value="强化">强化：更重成稿质感</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">结尾类型</label>
          <select v-model="form.quality_controls.ending_hook_type" :disabled="!!longRun" :style="inputStyle">
            <option value="感官钩子">感官钩子</option>
            <option value="线索钩子">线索钩子</option>
            <option value="关系钩子">关系钩子</option>
            <option value="危险钩子">危险钩子</option>
          </select>
        </div>
        <div>
          <label :style="labelStyle">改写策略</label>
          <select v-model="form.quality_controls.rewrite_policy" :disabled="!!longRun" :style="inputStyle">
            <option value="auto_once">auto_once</option>
            <option value="manual">manual</option>
            <option value="disabled">disabled</option>
          </select>
        </div>
      </div>

      <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <button @click="createNovelRun" :disabled="loading || !!longRun || !form.world_id" :style="buttonStyle('#7c3aed')">{{ loading && !longRun ? '创建中...' : '创建长篇运行' }}</button>
        <button @click="loadExistingRun" :disabled="loading || !loadId.trim()" :style="buttonStyle('#0891b2')">加载已有运行</button>
        <button @click="loadAllRuns" :disabled="loading" :style="buttonStyle('#0f766e')">加载所有运行</button>
        <button @click="generateNextChapter" :disabled="loading || !longRun || isCompleted" :style="buttonStyle('#2563eb')">{{ loading && longRun ? '生成中...' : nextChapterLabel }}</button>
        <button @click="resetRun" :disabled="loading" :style="buttonStyle('#4b5563')">新建另一个运行</button>
        <span v-if="longRun" style="color: #d1d5db; font-size: 13px;">Long Run：<code>{{ longRun.long_run_id }}</code>　状态：{{ longRun.status }}　章节：{{ longRun.current_chapter || 0 }}/{{ longRun.target_chapters }}</span>
      </div>
      <div v-if="genreProfile" style="margin-top: 12px;">
        <button @click="showGenreProfile = !showGenreProfile" :style="buttonStyle('#111827')">{{ showGenreProfile ? '隐藏' : '查看' }} Genre Profile</button>
        <pre v-if="showGenreProfile" :style="preStyle">{{ formatJson(genreProfile) }}</pre>
      </div>
      <div v-if="runs.length" style="margin-top: 14px; display: grid; gap: 8px;">
        <div style="color: #9ca3af; font-size: 13px;">已有运行（{{ runs.length }}）</div>
        <button v-for="run in runs" :key="run.long_run_id" @click="loadRunFromList(run)" :disabled="loading" :style="listButtonStyle(longRun?.long_run_id === run.long_run_id)">
          <strong>{{ run.long_run_id }}</strong> · {{ run.world_id }} · {{ run.status }} · {{ run.current_chapter || 0 }}/{{ run.target_chapters }} 章
        </button>
      </div>
      <div v-if="error" style="margin-top: 12px; color: #f87171; white-space: pre-wrap;">{{ error }}</div>
    </section>

    <section v-if="longRun" :style="panelStyle">
      <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 14px;">
        <h3 style="margin: 0; font-size: 20px;">整本书运行时</h3>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button @click="refreshRuntime" :disabled="loading" :style="buttonStyle('#374151')">刷新 Runtime</button>
          <button @click="loadDirectArtifacts" :disabled="loading" :style="buttonStyle('#1f2937')">刷新直接 Artifacts</button>
          <button @click="loadMemory" :disabled="loading" :style="buttonStyle('#111827')">刷新 Memory</button>
        </div>
      </div>
      <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
        <button v-for="tab in runtimeTabs" :key="tab.id" @click="activeRuntimeTab = tab.id" :style="tabButtonStyle(activeRuntimeTab === tab.id)">{{ tab.label }}</button>
      </div>
      <div v-if="activeRuntimeTab === 'summary'" style="display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; color: #d1d5db;">
        <div :style="metricStyle">当前章节<br /><strong>{{ runtime?.novel_state?.current_chapter || longRun.current_chapter || 0 }}/{{ runtime?.novel_state?.target_chapters || longRun.target_chapters || '-' }}</strong></div>
        <div :style="metricStyle">进度<br /><strong>{{ Math.round((runtime?.novel_state?.progress_ratio || 0) * 100) }}%</strong></div>
        <div :style="metricStyle">当前字数<br /><strong>{{ runtime?.novel_state?.current_words || 0 }}</strong></div>
        <div :style="metricStyle">线索数<br /><strong>{{ runtime?.clue_ledger?.clues?.length || artifacts.clueLedger?.clues?.length || 0 }}</strong></div>
        <div :style="metricStyle">悬念数<br /><strong>{{ runtime?.open_threads_state?.threads?.length || artifacts.openThreadsState?.threads?.length || 0 }}</strong></div>
        <div :style="metricStyle">记忆数<br /><strong>{{ memory.length }}</strong></div>
      </div>
      <pre v-else :style="preStyle">{{ runtimeTabJson }}</pre>
    </section>

    <section v-if="longRun" style="display: grid; grid-template-columns: 300px 1fr; gap: 16px; align-items: start;">
      <div :style="panelStyle">
        <h3 style="margin: 0 0 12px; font-size: 18px; color: #93c5fd;">章节</h3>
        <div v-if="!chapters.length" style="color: #9ca3af; font-size: 13px;">还没有生成章节。</div>
        <button v-for="chapter in chapters" :key="chapter.chapter_no" @click="selectChapter(chapter.chapter_no)" :style="chapterButtonStyle(chapter, selectedChapterNo === chapter.chapter_no)">
          第 {{ chapter.chapter_no }} 章 · {{ statusLabel(chapter.status) }}<br />
          <span style="font-size: 11px; color: #9ca3af;">{{ chapter.simulation_id }}</span>
          <span v-if="chapter.validation_status === 'failed'" style="display: block; margin-top: 4px; font-size: 11px; color: #fecaca;">验证失败 {{ chapter.validation_error_count || 0 }} 项</span>
        </button>
      </div>

      <div :style="panelStyle">
        <div v-if="!selectedChapterDetail" style="color: #9ca3af;">选择一个章节查看正文、计划、continuity、质量报告和运行状态。</div>
        <template v-else>
          <div style="display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 12px;">
            <h3 style="margin: 0; font-size: 18px; color: #c084fc;">第 {{ selectedChapterNo }} 章控制台</h3>
            <button @click="refreshCurrentChapter" :disabled="loading" :style="buttonStyle('#374151')">刷新当前章节</button>
          </div>
          <div v-if="selectedChapterDetail.run_status?.validation_status === 'failed'" style="margin-bottom: 12px; padding: 12px; border-radius: 10px; background: rgba(127, 29, 29, 0.55); border: 1px solid rgba(248, 113, 113, 0.45); color: #fecaca;">
            本章验证失败：{{ selectedChapterDetail.run_status?.validation_errors?.length || 0 }} 项。当前状态：{{ statusLabel(selectedChapterDetail.run_status?.status) }}。
          </div>
          <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 12px; color: #d1d5db;">
            <div :style="metricStyle">章节目标<br /><strong>{{ selectedChapterDetail.chapter_plan?.chapter_goal?.goal || selectedChapterDetail.chapter_plan?.goal || '-' }}</strong></div>
            <div :style="metricStyle">计划线索<br /><strong>{{ plannedCluesLabel }}</strong></div>
            <div :style="metricStyle">新增事实<br /><strong>{{ selectedChapterDetail.chapter_continuity?.new_facts?.length || 0 }}</strong></div>
            <div :style="metricStyle">质量分<br /><strong>{{ chapterQualityScore }}</strong></div>
          </div>
          <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px;">
            <button v-for="tab in chapterTabs" :key="tab.id" @click="activeChapterTab = tab.id" :style="tabButtonStyle(activeChapterTab === tab.id)">{{ tab.label }}</button>
          </div>
          <pre v-if="activeChapterTab === 'draft'" :style="{ ...preStyle, maxHeight: '620px', color: '#e5e7eb', lineHeight: '1.7' }">{{ selectedChapterDetail.chapter_draft || '暂无正文' }}</pre>
          <pre v-else :style="{ ...preStyle, maxHeight: '620px' }">{{ chapterTabJson }}</pre>
        </template>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { genresApi, novelRunsApi, worldsApi } from '@/lib/api'
import { useWorldStore } from '@/stores/world'

const worldStore = useWorldStore()

const worlds = ref([])
const genres = ref([])
const runs = ref([])
const genreProfile = ref(null)
const showGenreProfile = ref(false)
const loading = ref(false)
const error = ref('')
const longRun = ref(null)
const runtime = ref(null)
const artifacts = ref({ run: null, plan: null, state: null, clueLedger: null, truthState: null, openThreadsState: null })
const selectedChapterDetail = ref(null)
const selectedChapterNo = ref(null)
const memory = ref([])
const activeRuntimeTab = ref('summary')
const activeChapterTab = ref('draft')
const loadId = ref('')

const form = ref({
  world_id: '',
  target_chapters: 10,
  seed: 12345,
  genre_id: 'horror',
  quality_controls: {
    style_focus: ['悬疑推进', '恐怖氛围'],
    generation_strength: '平衡',
    ending_hook_type: '线索钩子',
    rewrite_policy: 'auto_once',
  },
})

const runtimeTabs = [
  { id: 'summary', label: '摘要' },
  { id: 'run', label: 'Run' },
  { id: 'plan', label: 'Plan' },
  { id: 'state', label: 'State' },
  { id: 'ledger', label: 'Clue Ledger' },
  { id: 'truth', label: 'Truth State' },
  { id: 'threads', label: 'Open Threads' },
  { id: 'memory', label: 'Memory' },
  { id: 'runtime', label: 'Runtime Raw' },
]

const chapterTabs = [
  { id: 'draft', label: '正文' },
  { id: 'plan', label: '章节计划' },
  { id: 'continuity', label: 'Continuity' },
  { id: 'quality', label: '质量报告' },
  { id: 'status', label: '运行状态' },
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
  maxHeight: '420px',
  overflow: 'auto',
  background: '#111827',
  color: '#d1d5db',
  padding: '12px',
  borderRadius: '10px',
  fontSize: '12px',
}

const metricStyle = {
  background: '#111827',
  borderRadius: '10px',
  padding: '12px',
  overflow: 'hidden',
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
  padding: '9px',
  cursor: 'pointer',
})

const chapterButtonStyle = (chapter, active) => ({
  ...listButtonStyle(active),
  border: chapter.validation_status === 'failed' ? '1px solid #f87171' : '1px solid #374151',
  background: active ? (chapter.validation_status === 'failed' ? '#991b1b' : '#1d4ed8') : '#111827',
})

const statusLabel = (status) => {
  const labels = {
    completed: '完成',
    completed_with_validation_errors: '完成但验证失败',
    idle: '空闲',
    idle_with_validation_errors: '空闲但有验证失败',
    running: '运行中',
    failed: '失败',
    created: '已创建',
  }
  return labels[status] || status || '-'
}

const chapters = computed(() => longRun.value?.chapters || [])
const isCompleted = computed(() => longRun.value?.status === 'completed' || longRun.value?.status === 'completed_with_validation_errors')
const nextChapterLabel = computed(() => {
  if (!longRun.value) return '生成下一章'
  return isCompleted.value ? '已完成' : `生成第 ${(longRun.value.current_chapter || 0) + 1} 章`
})

const runtimeTabJson = computed(() => {
  const map = {
    run: artifacts.value.run || longRun.value,
    plan: artifacts.value.plan || runtime.value?.novel_plan,
    state: artifacts.value.state || runtime.value?.novel_state,
    ledger: artifacts.value.clueLedger || runtime.value?.clue_ledger,
    truth: artifacts.value.truthState || runtime.value?.truth_state,
    threads: artifacts.value.openThreadsState || runtime.value?.open_threads_state,
    memory: memory.value,
    runtime: runtime.value,
  }
  return formatJson(map[activeRuntimeTab.value] || {})
})

const chapterTabJson = computed(() => {
  const map = {
    plan: selectedChapterDetail.value?.chapter_plan,
    continuity: selectedChapterDetail.value?.chapter_continuity,
    quality: selectedChapterDetail.value?.quality_reports,
    status: selectedChapterDetail.value?.run_status,
    raw: selectedChapterDetail.value,
  }
  return formatJson(map[activeChapterTab.value] || {})
})

const plannedCluesLabel = computed(() => {
  const plan = selectedChapterDetail.value?.chapter_plan || {}
  const clues = plan.selected_clues || plan.required_clues || plan.clues || []
  if (!Array.isArray(clues)) return '-'
  return clues.length ? clues.slice(0, 3).join(', ') : '-'
})

const chapterQualityScore = computed(() => {
  const report = selectedChapterDetail.value?.quality_reports?.[0]
  return report?.overall_score ?? report?.grade ?? '-'
})

const formatJson = (value) => JSON.stringify(value || {}, null, 2)
const genreValue = (genre) => typeof genre === 'string' ? genre : genre.id || genre.genre_id || genre.name || ''
const genreLabel = (genre) => typeof genre === 'string' ? genre : `${genre.name || genre.id || genre.genre_id}${genre.id || genre.genre_id ? ` (${genre.id || genre.genre_id})` : ''}`

const loadWorlds = async () => {
  const data = await worldsApi.list()
  worlds.value = data.worlds || []
  if (!form.value.world_id) {
    form.value.world_id = worldStore.worldBible?.world_id || worldStore.worldId || worlds.value[0]?.id || ''
  }
}

const loadGenres = async () => {
  const data = await genresApi.list()
  genres.value = data.genres || []
  const firstGenre = genreValue(genres.value[0])
  if (!form.value.genre_id && firstGenre) form.value.genre_id = firstGenre
  await loadGenreProfile()
}

const loadGenreProfile = async () => {
  if (!form.value.genre_id) return
  try {
    const data = await genresApi.profile(form.value.genre_id)
    genreProfile.value = data.profile || data
  } catch {
    genreProfile.value = null
  }
}

const setRun = (run) => {
  longRun.value = run
  artifacts.value.run = run
  loadId.value = run?.long_run_id || loadId.value
}

const refreshRuntime = async () => {
  if (!longRun.value?.long_run_id) return
  const data = await novelRunsApi.runtime(longRun.value.long_run_id)
  runtime.value = data
  setRun(data.run)
}

const loadDirectArtifacts = async () => {
  if (!longRun.value?.long_run_id) return
  const id = longRun.value.long_run_id
  const [run, plan, state, clueLedger, truthState, openThreadsState] = await Promise.all([
    novelRunsApi.get(id),
    novelRunsApi.plan(id),
    novelRunsApi.state(id),
    novelRunsApi.clueLedger(id),
    novelRunsApi.truthState(id),
    novelRunsApi.openThreadsState(id),
  ])
  artifacts.value = { run, plan, state, clueLedger, truthState, openThreadsState }
  setRun(run)
}

const loadMemory = async () => {
  if (!longRun.value?.long_run_id) return
  const data = await novelRunsApi.memory(longRun.value.long_run_id)
  memory.value = data.memories || []
}

const refreshCurrentChapter = async () => {
  if (selectedChapterNo.value) await selectChapter(selectedChapterNo.value)
}

const refreshAll = async () => {
  if (!longRun.value?.long_run_id) return
  loading.value = true
  error.value = ''
  try {
    await refreshRuntime()
    await loadDirectArtifacts()
    await loadMemory()
    await refreshCurrentChapter()
  } catch (err) {
    error.value = err.message || '刷新失败'
  } finally {
    loading.value = false
  }
}

const createNovelRun = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await novelRunsApi.create(form.value)
    setRun(data.run)
    runtime.value = null
    selectedChapterDetail.value = null
    selectedChapterNo.value = null
    await refreshAll()
  } catch (err) {
    error.value = err.message || '创建长篇运行失败'
  } finally {
    loading.value = false
  }
}

const loadAllRuns = async () => {
  loading.value = true
  error.value = ''
  try {
    const data = await novelRunsApi.list()
    runs.value = data.runs || []
    if (!runs.value.length) error.value = '还没有找到长篇运行'
  } catch (err) {
    error.value = err.message || '加载所有运行失败'
  } finally {
    loading.value = false
  }
}

const loadRunFromList = async (run) => {
  loadId.value = run.long_run_id
  await loadExistingRun()
}

const loadExistingRun = async () => {
  const id = loadId.value.trim()
  if (!id) return
  loading.value = true
  error.value = ''
  try {
    const run = await novelRunsApi.get(id)
    setRun(run)
    selectedChapterDetail.value = null
    selectedChapterNo.value = null
    await refreshAll()
  } catch (err) {
    error.value = err.message || '加载长篇运行失败'
  } finally {
    loading.value = false
  }
}

const generateNextChapter = async () => {
  if (!longRun.value?.long_run_id || isCompleted.value) return
  loading.value = true
  error.value = ''
  try {
    const data = await novelRunsApi.generateNextChapter(longRun.value.long_run_id)
    setRun(data.run)
    await refreshAll()
    if (data.chapter?.chapter_no) await selectChapter(data.chapter.chapter_no)
  } catch (err) {
    error.value = err.message || '生成下一章失败'
    await refreshRuntime().catch(() => {})
  } finally {
    loading.value = false
  }
}

const selectChapter = async (chapterNo) => {
  if (!longRun.value?.long_run_id) return
  selectedChapterNo.value = chapterNo
  activeChapterTab.value = 'draft'
  selectedChapterDetail.value = await novelRunsApi.chapter(longRun.value.long_run_id, chapterNo)
}

const resetRun = () => {
  longRun.value = null
  runtime.value = null
  artifacts.value = { run: null, plan: null, state: null, clueLedger: null, truthState: null, openThreadsState: null }
  selectedChapterDetail.value = null
  selectedChapterNo.value = null
  memory.value = []
  error.value = ''
}

onMounted(async () => {
  await Promise.allSettled([loadWorlds(), loadGenres(), loadAllRuns()])
})
</script>
