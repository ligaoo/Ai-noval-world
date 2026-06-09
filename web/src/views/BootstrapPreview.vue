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

      <details style="margin-top: 16px; color: #d1d5db;">
        <summary style="cursor: pointer; color: #fbbf24;">Truth Chain / Evidence / Open Threads / Anchors</summary>
        <pre style="white-space: pre-wrap; font-size: 12px; background: #111827; padding: 12px; border-radius: 8px; overflow: auto;">{{ JSON.stringify(extraPreview, null, 2) }}</pre>
      </details>
    </section>

    <!-- ⑤ 模拟结果 -->
    <section
      v-if="simulationResult"
      style="background: rgba(42, 45, 53, 0.9); padding: 20px; border-radius: 14px;
             border: 1px solid rgba(255,255,255,0.1);"
    >
      <h3 style="font-weight: 600; margin-bottom: 8px;">⑤ 已启动模拟</h3>
      <div style="font-size: 14px;">
        Sim ID：<code>{{ simulationResult.sim_id }}</code><br />
        Message：{{ simulationResult.message }}
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const API = 'http://localhost:8421'

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

const extraPreview = computed(() => {
  if (!result.value) return {}
  return {
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
</script>
