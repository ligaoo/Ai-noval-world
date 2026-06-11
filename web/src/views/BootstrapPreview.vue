<template>
  <div style="max-width: 1100px; margin: 0 auto; color: #f3f4f6;">
    <div style="margin-bottom: 24px;">
      <h2
        style="font-size: 28px; font-weight: 700; background: linear-gradient(135deg, #a855f7, #ec4899);
               -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;"
      >
        Story Bootstrap
      </h2>
      <p style="color: #9ca3af; margin-top: 4px;">
        输入一句话模糊设定，自动补全可运行的完整故事世界（V1 §22-§23）。
      </p>
    </div>

    <!-- ① 模糊设定输入 -->
    <section
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;"
    >
      <h3 style="font-weight: 600; margin-bottom: 12px;">① 模糊设定</h3>
      <textarea
        v-model="form.user_seed"
        placeholder="例：废弃医院，午夜出现五楼，主角调查失踪妹妹"
        rows="3"
        style="width: 100%; background: #1c1e24; border: 1px solid #374151;
               color: #f3f4f6; padding: 12px; border-radius: 10px; resize: vertical;"
      ></textarea>

      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-top: 12px;">
        <div>
          <label style="font-size: 12px; color: #9ca3af;">目标题材</label>
          <select
            v-model="form.target_genre"
            style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6;
                   padding: 8px; border-radius: 8px;"
          >
            <option value="horror_suspense">悬疑灵异</option>
            <option value="psychological_thriller">心理惊悚</option>
            <option value="mystery">推理</option>
            <option value="thriller">惊悚</option>
          </select>
        </div>
        <div>
          <label style="font-size: 12px; color: #9ca3af;">目标字数</label>
          <input
            v-model.number="form.target_words"
            type="number"
            style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6;
                   padding: 8px; border-radius: 8px;"
          />
        </div>
        <div>
          <label style="font-size: 12px; color: #9ca3af;">World ID（可选）</label>
          <input
            v-model="form.world_id"
            placeholder="留空自动生成"
            style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6;
                   padding: 8px; border-radius: 8px;"
          />
        </div>
      </div>

      <div style="display: flex; gap: 12px; margin-top: 16px;">
        <button
          @click="onBootstrap"
          :disabled="loading || !form.user_seed"
          style="background: linear-gradient(135deg, #a855f7, #ec4899); color: white; border: none;
                 padding: 10px 24px; border-radius: 10px; cursor: pointer; font-weight: 600;"
        >
          {{ loading ? '生成中...' : '生成可运行故事世界' }}
        </button>
        <button
          v-if="result"
          @click="onConfirm"
          :disabled="loading || !canConfirm"
          style="background: #10b981; color: white; border: none; padding: 10px 20px;
                 border-radius: 10px; cursor: pointer;"
        >
          确认并写盘
        </button>
        <button
          v-if="result"
          @click="onStartSim"
          :disabled="loading || !canConfirm"
          style="background: #3b82f6; color: white; border: none; padding: 10px 20px;
                 border-radius: 10px; cursor: pointer;"
        >
          确认 + 启动模拟
        </button>
      </div>

      <div v-if="error" style="margin-top: 12px; color: #f87171;">{{ error }}</div>
    </section>

    <!-- ② 候选预览 -->
    <section
      v-if="result"
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;"
    >
      <h3 style="font-weight: 600; margin-bottom: 8px;">② 候选预览</h3>
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 12px;">
        <div
          v-for="(item, idx) in summaryItems"
          :key="idx"
          style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;"
        >
          <div style="font-size: 12px; color: #9ca3af;">{{ item.label }}</div>
          <div style="font-size: 18px; font-weight: 700; color: #f3f4f6;">{{ item.value }}</div>
        </div>
      </div>
      <div style="font-size: 14px; color: #9ca3af;">
        Bootstrap ID：<code>{{ result.bootstrap_id }}</code>　
        状态：<span :style="{ color: canConfirm ? '#10b981' : '#f59e0b' }">{{ result.status }}</span>
      </div>
    </section>

    <!-- ③ 校验结果 -->
    <section
      v-if="result && result.validation"
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;"
    >
      <h3 style="font-weight: 600; margin-bottom: 8px;">
        ③ Bootstrap Validator
        <span :style="{ color: result.validation.passed ? '#10b981' : '#f87171' }">
          {{ result.validation.passed ? 'PASSED' : 'FAILED' }}
        </span>
      </h3>
      <div v-if="result.validation.issues && result.validation.issues.length">
        <h4 style="color: #f87171; font-size: 14px; margin-bottom: 4px;">错误</h4>
        <ul style="margin: 0; padding-left: 18px;">
          <li
            v-for="(i, idx) in result.validation.issues"
            :key="idx"
            style="font-size: 13px; color: #fca5a5;"
          >
            [{{ i.type }}] {{ i.message }}
          </li>
        </ul>
      </div>
      <div
        v-if="result.validation.warnings && result.validation.warnings.length"
        style="margin-top: 8px;"
      >
        <h4 style="color: #fbbf24; font-size: 14px; margin-bottom: 4px;">警告</h4>
        <ul style="margin: 0; padding-left: 18px;">
          <li
            v-for="(w, idx) in result.validation.warnings"
            :key="idx"
            style="font-size: 13px; color: #fde68a;"
          >
            [{{ w.type }}] {{ w.message }}
          </li>
        </ul>
      </div>
    </section>

    <!-- ④ 完整候选详情 -->
    <section
      v-if="result"
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;"
    >
      <h3 style="font-weight: 600; margin-bottom: 12px;">④ 完整候选详情</h3>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;">
          <h4 style="margin: 0 0 8px; color: #c084fc;">World Bible</h4>
          <div style="font-size: 13px; color: #d1d5db; line-height: 1.6;">
            题材：{{ result.world_bible?.genre || '-' }} / {{ result.world_bible?.sub_genre || '-' }}<br />
            地点：{{ result.world_bible?.core_location || result.parsed_seed?.core_location || '-' }}<br />
            基调：{{ result.world_bible?.tone || '-' }}
          </div>
        </div>

        <div style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;">
          <h4 style="margin: 0 0 8px; color: #c084fc;">Opening Plan</h4>
          <div style="font-size: 13px; color: #d1d5db; line-height: 1.6;">
            目标：{{ result.opening_chapter_plan?.protagonist_goal || result.chapter_goal?.goal || '-' }}<br />
            初始地点：{{ result.opening_chapter_plan?.initial_location || '-' }}<br />
            选中线索：{{ (result.opening_chapter_plan?.selected_clues || []).join(', ') || '-' }}
          </div>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <h4 style="margin: 0 0 8px; color: #93c5fd;">角色</h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
          <div
            v-for="c in result.characters || []"
            :key="c.character_id"
            style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;"
          >
            <strong>{{ c.name }}</strong> <span style="color: #9ca3af;">({{ c.role }})</span><br />
            <span style="color: #9ca3af;">{{ c.character_id }} / {{ c.visibility }} / active={{ c.active_agent }}</span><br />
            初始地点：{{ c.location_id || '-' }}
          </div>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <h4 style="margin: 0 0 8px; color: #93c5fd;">地点与对象</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
          <div
            v-for="loc in result.map || []"
            :key="loc.location_id"
            style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;"
          >
            <strong>{{ loc.name }}</strong> <span style="color: #9ca3af;">{{ loc.location_id }}</span><br />
            <span style="color: #9ca3af;">连接：{{ (loc.connected_to || []).join(', ') || '-' }}</span><br />
            对象：{{ (loc.objects || []).map(o => o.object_id).join(', ') || '-' }}
          </div>
        </div>
      </div>

      <div style="margin-top: 16px;">
        <h4 style="margin: 0 0 8px; color: #93c5fd;">线索与发现路线</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
          <div
            v-for="clue in result.clues || []"
            :key="clue.clue_id"
            style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;"
          >
            <strong>{{ clue.title }}</strong> <span style="color: #9ca3af;">{{ clue.clue_id }}</span><br />
            <div style="color: #d1d5db; margin: 4px 0;">{{ clue.content }}</div>
            <div v-for="(route, idx) in clue.discover_routes || []" :key="idx" style="color: #9ca3af;">
              {{ route.location_id }} / {{ route.action }} / {{ route.object_id || route.location_id }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="storyBlueprint" style="margin-top: 16px;">
        <h4 style="margin: 0 0 8px; color: #fbbf24;">前端蓝图预览</h4>
        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
          <div style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;">
            <strong>世界规则</strong>
            <div style="color: #9ca3af; margin-top: 4px;">{{ storyBlueprint.world_rules?.title || '-' }} / {{ storyBlueprint.world_rules?.genre || '-' }}</div>
            <ul style="margin: 6px 0 0; padding-left: 18px; color: #d1d5db;">
              <li v-for="(rule, idx) in storyBlueprint.world_rules?.rules || []" :key="idx">{{ rule }}</li>
            </ul>
          </div>
          <div style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;">
            <strong>第一章约束</strong>
            <div style="color: #d1d5db; margin-top: 4px;">{{ storyBlueprint.opening_chapter?.plan?.protagonist_goal || '-' }}</div>
            <div style="color: #9ca3af; margin-top: 6px;">结尾钩子：{{ storyBlueprint.opening_chapter?.ending_hook?.content || storyBlueprint.opening_chapter?.ending_hook || '-' }}</div>
          </div>
          <div style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;">
            <strong>悬念池</strong>
            <ul style="margin: 6px 0 0; padding-left: 18px; color: #d1d5db;">
              <li v-for="thread in storyBlueprint.open_threads || []" :key="thread.thread_id">
                {{ thread.thread_id }}：{{ thread.question }}
              </li>
            </ul>
          </div>
          <div style="background: rgba(28,30,36,0.6); padding: 10px; border-radius: 8px; font-size: 13px;">
            <strong>证据链</strong>
            <ul style="margin: 6px 0 0; padding-left: 18px; color: #d1d5db;">
              <li v-for="item in storyBlueprint.evidence_graph || []" :key="item.evidence_id">
                {{ item.evidence_id }} → {{ item.related_thread }}
              </li>
            </ul>
          </div>
        </div>
      </div>

      <details style="margin-top: 16px; color: #d1d5db;">
        <summary style="cursor: pointer; color: #fbbf24;">Story Blueprint / Truth Chain / Evidence / Open Threads / Anchors</summary>
        <pre style="white-space: pre-wrap; font-size: 12px; background: #111827; padding: 12px; border-radius: 8px; overflow: auto;">{{ JSON.stringify(extraPreview, null, 2) }}</pre>
      </details>
    </section>

    <!-- ⑤ 模拟结果 -->
    <section
      v-if="simulationResult"
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px;"
    >
      <h3 style="font-weight: 600; margin-bottom: 8px;">⑤ 已启动模拟</h3>
      <div style="font-size: 14px;">
        Sim ID：<code>{{ simulationResult.sim_id }}</code><br />
        Message：{{ simulationResult.message }}
      </div>
    </section>

    <!-- ⑥ 长篇生成 MVP -->
    <section
      v-if="result"
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1);"
    >
      <h3 style="font-weight: 600; margin-bottom: 12px;">⑥ 长篇生成 MVP</h3>
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 12px;">
        <div>
          <label style="font-size: 12px; color: #9ca3af;">目标章节数</label>
          <input v-model.number="longRunForm.target_chapters" type="number" min="1" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;" />
        </div>
        <div>
          <label style="font-size: 12px; color: #9ca3af;">Seed</label>
          <input v-model.number="longRunForm.seed" type="number" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;" />
        </div>
        <div>
          <label style="font-size: 12px; color: #9ca3af;">Genre ID</label>
          <input v-model="longRunForm.genre_id" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;" />
        </div>
      </div>

      <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px;">
        <button @click="createLongRun" :disabled="longRunLoading || !canConfirm" style="background: #8b5cf6; color: white; border: none; padding: 9px 16px; border-radius: 9px; cursor: pointer;">
          创建长篇运行
        </button>
        <button @click="generateNextLongRunChapter" :disabled="longRunLoading || !longRun || longRun.status === 'completed'" style="background: #2563eb; color: white; border: none; padding: 9px 16px; border-radius: 9px; cursor: pointer;">
          {{ longRunLoading ? '生成中...' : '生成下一章' }}
        </button>
        <button @click="refreshLongRun" :disabled="longRunLoading || !longRun" style="background: #374151; color: white; border: none; padding: 9px 16px; border-radius: 9px; cursor: pointer;">
          刷新
        </button>
      </div>

      <div v-if="longRunError" style="color: #f87171; margin-bottom: 10px;">{{ longRunError }}</div>
      <div v-if="longRun" style="font-size: 13px; color: #d1d5db; margin-bottom: 12px;">
        Long Run：<code>{{ longRun.long_run_id }}</code>　状态：{{ longRun.status }}　章节：{{ longRun.current_chapter || 0 }}/{{ longRun.target_chapters }}
      </div>

      <div v-if="longRunChapters.length" style="display: grid; grid-template-columns: 260px 1fr; gap: 14px; align-items: start;">
        <div style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;">
          <h4 style="margin: 0 0 8px; color: #93c5fd;">章节列表</h4>
          <button
            v-for="chapter in longRunChapters"
            :key="chapter.chapter_no"
            @click="selectLongRunChapter(chapter.chapter_no)"
            style="display: block; width: 100%; text-align: left; margin-bottom: 6px; background: #111827; color: #e5e7eb; border: 1px solid #374151; border-radius: 8px; padding: 8px; cursor: pointer;"
          >
            第 {{ chapter.chapter_no }} 章 · {{ chapter.status }}<br />
            <span style="font-size: 11px; color: #9ca3af;">{{ chapter.simulation_id }}</span>
          </button>
        </div>

        <div style="display: grid; gap: 12px;">
          <div v-if="selectedChapterDetail" style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;">
            <h4 style="margin: 0 0 8px; color: #c084fc;">章节正文</h4>
            <pre style="white-space: pre-wrap; max-height: 420px; overflow: auto; font-size: 13px; line-height: 1.7; background: #111827; padding: 12px; border-radius: 8px;">{{ selectedChapterDetail.chapter_draft || '暂无正文' }}</pre>
          </div>

          <div v-if="selectedChapterDetail" style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;">
            <h4 style="margin: 0 0 8px; color: #fbbf24;">Continuity</h4>
            <div style="font-size: 13px; color: #d1d5db; line-height: 1.7;">
              摘要：{{ selectedChapterDetail.chapter_continuity?.chapter_delta_summary || '-' }}<br />
              Open Threads：{{ (selectedChapterDetail.chapter_continuity?.open_threads || []).join(' / ') || '-' }}<br />
              New Questions：{{ (selectedChapterDetail.chapter_continuity?.new_questions || []).join(' / ') || '-' }}<br />
              New Facts：{{ (selectedChapterDetail.chapter_continuity?.new_facts || []).join(' / ') || '-' }}
            </div>
            <details style="margin-top: 8px;">
              <summary style="cursor: pointer; color: #93c5fd;">完整 continuity JSON</summary>
              <pre style="white-space: pre-wrap; font-size: 12px; background: #111827; padding: 10px; border-radius: 8px; overflow: auto;">{{ JSON.stringify(selectedChapterDetail.chapter_continuity || {}, null, 2) }}</pre>
            </details>
          </div>

          <div style="background: rgba(28,30,36,0.6); padding: 12px; border-radius: 10px;">
            <h4 style="margin: 0 0 8px; color: #34d399;">共享 Agent 记忆</h4>
            <div v-if="!longRunMemory.length" style="font-size: 13px; color: #9ca3af;">暂无记忆记录。</div>
            <div v-for="memory in longRunMemory.slice(-12).reverse()" :key="memory.memory_id" style="font-size: 12px; color: #d1d5db; border-bottom: 1px solid rgba(255,255,255,0.08); padding: 6px 0;">
              <strong>{{ memory.agent_id }}</strong> / {{ memory.type }} / importance={{ memory.importance }}<br />
              {{ memory.content }}<br />
              <span style="color: #9ca3af;">{{ (memory.tags || []).join(', ') }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const API = ''

const form = ref({
  user_seed: '',
  target_genre: 'generic',
  target_words: 100000,
  world_id: '',
})

const result = ref(null)
const simulationResult = ref(null)
const loading = ref(false)
const error = ref('')
const confirmedWorldId = ref('')
const longRunLoading = ref(false)
const longRunError = ref('')
const longRun = ref(null)
const longRunChapters = ref([])
const selectedChapterDetail = ref(null)
const longRunMemory = ref([])
const longRunForm = ref({
  target_chapters: 10,
  seed: 12345,
  genre_id: 'horror',
})

const canConfirm = computed(() => result.value && result.value.validation && result.value.validation.passed)

const summaryItems = computed(() => {
  if (!result.value) return []
  const s = result.value.summary || result.value
  return [
    { label: '标题', value: result.value.title || '-' },
    { label: '角色数', value: s.characters?.length ?? s.characters ?? '-' },
    { label: '地点数', value: s.map?.length ?? s.locations ?? '-' },
    { label: '线索数', value: s.clues?.length ?? s.clues ?? '-' },
  ]
})

const storyBlueprint = computed(() => result.value?.story_blueprint || null)

const extraPreview = computed(() => {
  if (!result.value) return {}
  return {
    story_blueprint: result.value.story_blueprint,
    truth_chain: result.value.truth_chain,
    evidence_graph: result.value.evidence_graph,
    open_threads: result.value.open_threads,
    writer_story_anchors: result.value.writer_story_anchors,
  }
})

const fetchFullBootstrap = async (bootstrapId) => {
  const res = await fetch(`${API}/api/story/bootstrap/${bootstrapId}`)
  const data = await res.json()
  if (!res.ok) {
    throw new Error(data.detail || '获取完整候选失败')
  }
  return data
}

const onBootstrap = async () => {
  loading.value = true
  error.value = ''
  result.value = null
  simulationResult.value = null
  try {
    const body = { ...form.value }
    if (!body.world_id) delete body.world_id

    const res = await fetch(`${API}/api/story/bootstrap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (!res.ok) {
      error.value = data.detail || '生成失败'
      return
    }
    result.value = await fetchFullBootstrap(data.bootstrap_id)
  } catch (e) {
    error.value = e.message || '请求失败'
  } finally {
    loading.value = false
  }
}

const onConfirm = async () => {
  if (!result.value || !result.value.bootstrap_id) return
  loading.value = true
  try {
    const res = await fetch(
      `${API}/api/story/bootstrap/${result.value.bootstrap_id}/confirm`,
      { method: 'POST' },
    )
    const data = await res.json()
    if (!res.ok) {
      error.value = (data.detail && data.detail.message) || data.detail || '确认失败'
      return
    }
    confirmedWorldId.value = data.world_id
    result.value.status = 'confirmed'
    alert(`已写入 worlds/${data.world_id}/ 共 ${data.summary && data.summary.locations} 个地点`)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const onStartSim = async () => {
  if (!result.value || !result.value.bootstrap_id) return
  loading.value = true
  try {
    const res = await fetch(
      `${API}/api/story/bootstrap/${result.value.bootstrap_id}/start`,
      { method: 'POST' },
    )
    const data = await res.json()
    if (!res.ok) {
      error.value = (data.detail && data.detail.message) || data.detail || '启动失败'
      return
    }
    simulationResult.value = data
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const resolveConfirmedWorldId = async () => {
  if (confirmedWorldId.value) return confirmedWorldId.value
  if (result.value?.world_id) return result.value.world_id
  if (result.value?.world_bible?.world_id) return result.value.world_bible.world_id
  if (form.value.world_id) return form.value.world_id
  if (!result.value?.bootstrap_id) throw new Error('缺少 bootstrap_id，无法确认世界')

  const res = await fetch(`${API}/api/story/bootstrap/${result.value.bootstrap_id}/confirm`, { method: 'POST' })
  const data = await res.json()
  if (!res.ok) throw new Error((data.detail && data.detail.message) || data.detail || '确认失败')
  confirmedWorldId.value = data.world_id
  result.value.status = 'confirmed'
  return data.world_id
}

const refreshLongRun = async () => {
  if (!longRun.value?.long_run_id) return
  const res = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}`)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || '刷新长篇运行失败')
  longRun.value = data
  longRunChapters.value = data.chapters || []
}

const loadLongRunMemory = async () => {
  if (!longRun.value?.long_run_id) return
  const res = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}/memory`)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || '读取记忆失败')
  longRunMemory.value = data.memories || []
}

const selectLongRunChapter = async (chapterNo) => {
  if (!longRun.value?.long_run_id) return
  const res = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}/chapters/${chapterNo}`)
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || '读取章节失败')
  selectedChapterDetail.value = data
  await loadLongRunMemory()
}

const createLongRun = async () => {
  longRunLoading.value = true
  longRunError.value = ''
  try {
    const worldId = await resolveConfirmedWorldId()
    const res = await fetch(`${API}/api/novel-runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        world_id: worldId,
        target_chapters: longRunForm.value.target_chapters,
        seed: longRunForm.value.seed,
        genre_id: longRunForm.value.genre_id,
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '创建长篇运行失败')
    longRun.value = data.run
    longRunChapters.value = data.run.chapters || []
    selectedChapterDetail.value = null
    longRunMemory.value = []
  } catch (e) {
    longRunError.value = e.message || '创建长篇运行失败'
  } finally {
    longRunLoading.value = false
  }
}

const generateNextLongRunChapter = async () => {
  if (!longRun.value?.long_run_id) return
  longRunLoading.value = true
  longRunError.value = ''
  try {
    const res = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}/chapters/next`, { method: 'POST' })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || '生成下一章失败')
    longRun.value = data.run
    longRunChapters.value = data.run.chapters || []
    await selectLongRunChapter(data.chapter.chapter_no)
  } catch (e) {
    longRunError.value = e.message || '生成下一章失败'
    await refreshLongRun().catch(() => {})
  } finally {
    longRunLoading.value = false
  }
}
</script>
