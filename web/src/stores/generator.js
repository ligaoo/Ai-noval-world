import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useWorldStore } from './world'

export const useGeneratorStore = defineStore('generator', () => {
  const worldStore = useWorldStore()

  // 所有候选
  const candidates = ref([])
  const isGenerating = ref(false)
  const generationLog = ref([])

  // 按类型分组的候选
  const characterCandidates = computed(() => 
    candidates.value.filter(c => c.candidate_type === 'character')
  )
  const npcCandidates = computed(() => 
    candidates.value.filter(c => c.candidate_type === 'npc')
  )
  const locationCandidates = computed(() => 
    candidates.value.filter(c => c.candidate_type === 'location')
  )
  const clueCandidates = computed(() => 
    candidates.value.filter(c => c.candidate_type === 'clue')
  )
  const relationshipCandidates = computed(() => 
    candidates.value.filter(c => c.candidate_type === 'relationship')
  )
  const secretCandidates = computed(() => 
    candidates.value.filter(c => c.candidate_type === 'secret')
  )

  // 按状态筛选
  const pendingCandidates = computed(() => 
    candidates.value.filter(c => c.status === 'generated' || c.status === 'edited')
  )
  const validatedCandidates = computed(() => 
    candidates.value.filter(c => c.status === 'validated')
  )
  const approvedCandidates = computed(() => 
    candidates.value.filter(c => c.status === 'approved')
  )

  // 添加候选
  function addCandidate(candidate) {
    const newCandidate = {
      ...candidate,
      candidate_id: `candidate_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      status: 'generated',
      source: {
        generator: candidate.generator || 'Unknown',
        prompt_version: 'v4.2.0',
        created_at: new Date().toISOString()
      },
      validation_report: null,
      user_edits: []
    }
    candidates.value.push(newCandidate)
    addLog(`✅ 新增候选: ${newCandidate.name || newCandidate.candidate_id}`)
    return newCandidate
  }

  // 批量添加候选
  function addCandidates(newCandidates) {
    newCandidates.forEach(c => addCandidate(c))
  }

  // 更新候选
  function updateCandidate(candidateId, updates) {
    const index = candidates.value.findIndex(c => c.candidate_id === candidateId)
    if (index !== -1) {
      candidates.value[index] = {
        ...candidates.value[index],
        ...updates,
        status: 'edited'
      }
      addLog(`✏️ 编辑候选: ${candidates.value[index].name || candidateId}`)
    }
  }

  // 运行校验
  function validateCandidate(candidateId) {
    const candidate = candidates.value.find(c => c.candidate_id === candidateId)
    if (!candidate) return

    // 模拟校验逻辑
    const report = {
      schema_valid: true,
      references_valid: true,
      knowledge_boundary_valid: true,
      no_duplication: true,
      plot_stage_appropriate: true,
      warnings: [],
      errors: [],
      score: Math.floor(Math.random() * 30) + 70
    }

    candidate.validation_report = report
    candidate.status = report.errors.length === 0 ? 'validated' : 'invalid'
    
    addLog(`🔍 校验完成: ${candidate.name || candidateId} - ${candidate.status}`)
    return report
  }

  // 批准候选
  function approveCandidate(candidateId) {
    const candidate = candidates.value.find(c => c.candidate_id === candidateId)
    if (candidate) {
      candidate.status = 'approved'
      addLog(`✅ 批准候选: ${candidate.name || candidateId}`)
    }
  }

  // 提交候选（入库）- 将候选数据同步到 worldStore
  function commitCandidate(candidateId) {
    const candidate = candidates.value.find(c => c.candidate_id === candidateId)
    if (candidate && candidate.status === 'approved') {
      candidate.status = 'committed'
      addLog(`📦 已入库: ${candidate.name || candidateId}`)
      
      // 根据候选类型同步到 worldStore
      const type = candidate.candidate_type
      
      if (type === 'character') {
        const chars = worldStore.characters
        const exists = chars.some(c => c.character_id === candidate.character_id || c.name === candidate.name)
        if (!exists) {
          const newChar = {
            character_id: candidate.character_id || `char_${Date.now()}`,
            name: candidate.name,
            role: candidate.role || 'supporting',
            agent_type: candidate.agent_type || 'full_npc_agent',
            traits: candidate.traits || [],
            goals: candidate.goals || { short_term: '', long_term: '' },
            skills: candidate.skills || { observation: 50, social: 50, logic: 50, courage: 50 },
            summary: candidate.summary || ''
          }
          worldStore.addCharacter(newChar)
          addLog(`✅ 已添加角色到世界配置: ${newChar.name}`)
        } else {
          addLog(`⚠️ 角色已存在，跳过入库: ${candidate.name}`)
        }
      } else if (type === 'npc') {
        const chars = worldStore.characters
        const exists = chars.some(c => c.character_id === candidate.character_id || c.name === candidate.name)
        if (!exists) {
          const newNpc = {
            character_id: candidate.character_id || `npc_${Date.now()}`,
            name: candidate.name,
            role: candidate.role || 'npc',
            agent_type: candidate.agent_type || 'semi_agent_npc',
            traits: candidate.traits || [],
            goals: candidate.goals || { short_term: '', long_term: '' },
            skills: candidate.skills || { observation: 50, social: 50 },
            summary: candidate.summary || '',
            location_id: candidate.location_id || ''
          }
          worldStore.addCharacter(newNpc)
          addLog(`✅ 已添加 NPC 到世界配置: ${newNpc.name}`)
        } else {
          addLog(`⚠️ NPC 已存在，跳过入库: ${candidate.name}`)
        }
      } else if (type === 'location') {
        const locs = worldStore.locations
        const exists = locs.some(l => l.location_id === candidate.location_id || l.name === candidate.name)
        if (!exists) {
          const newLoc = {
            location_id: candidate.location_id || `loc_${Date.now()}`,
            name: candidate.name,
            public_description: candidate.description || candidate.summary || '',
            connected_to: candidate.connected_to || [],
            objects: candidate.objects || [],
            danger_level: candidate.danger_level || 1
          }
          worldStore.addLocation(newLoc)
          addLog(`✅ 已添加地点到世界配置: ${newLoc.name}`)
        }
      } else if (type === 'clue') {
        const cls = worldStore.clues
        const exists = cls.some(c => c.clue_id === candidate.clue_id || c.name === candidate.name)
        if (!exists) {
          const newClue = {
            clue_id: candidate.clue_id || `clue_${Date.now()}`,
            name: candidate.name,
            content: candidate.content || candidate.summary || '',
            level: candidate.level || 'minor',
            arc_id: candidate.arc_id || '',
            importance: candidate.importance || 50,
            discover_routes: candidate.discover_routes || []
          }
          worldStore.addClue(newClue)
          addLog(`✅ 已添加线索到世界配置: ${newClue.name}`)
        }
      }
      
      return true
    }
    return false
  }

  // 批量批准
  function batchApprove(candidateIds) {
    candidateIds.forEach(id => approveCandidate(id))
  }

  // 批量提交
  function batchCommit(candidateIds) {
    candidateIds.forEach(id => commitCandidate(id))
  }

  // 拒绝候选
  function rejectCandidate(candidateId) {
    const index = candidates.value.findIndex(c => c.candidate_id === candidateId)
    if (index !== -1) {
      const name = candidates.value[index].name
      candidates.value.splice(index, 1)
      addLog(`❌ 已拒绝: ${name || candidateId}`)
    }
  }

  // 添加日志
  function addLog(message) {
    generationLog.value.unshift({
      timestamp: new Date().toISOString(),
      message
    })
    if (generationLog.value.length > 100) {
      generationLog.value = generationLog.value.slice(0, 100)
    }
  }

  // 清除日志
  function clearLog() {
    generationLog.value = []
  }

  // 设置生成状态
  function setGenerating(val) {
    isGenerating.value = val
  }

  return {
    // 状态
    candidates,
    isGenerating,
    generationLog,

    // 计算属性
    characterCandidates,
    npcCandidates,
    locationCandidates,
    clueCandidates,
    relationshipCandidates,
    secretCandidates,
    pendingCandidates,
    validatedCandidates,
    approvedCandidates,

    // 方法
    addCandidate,
    addCandidates,
    updateCandidate,
    validateCandidate,
    approveCandidate,
    commitCandidate,
    batchApprove,
    batchCommit,
    rejectCandidate,
    addLog,
    clearLog,
    setGenerating
  }
})
