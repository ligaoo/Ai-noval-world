import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useWorldStore = defineStore('world', () => {
  // 状态初始化：尝试从 localStorage 读取
  const loadState = () => {
    const saved = localStorage.getItem('novel_world_store')
    return saved ? JSON.parse(saved) : null
  }

  const savedState = loadState()

  const worldId = ref(savedState?.worldId || '')
  const worldBible = ref(savedState?.worldBible || null)
  const characters = ref(savedState?.characters || [])
  const locations = ref(savedState?.locations || [])
  const clues = ref(savedState?.clues || [])
  const plotArcs = ref(savedState?.plotArcs || [])
  const characterArcs = ref(savedState?.characterArcs || [])

  // 自动保存至 localStorage
  const saveToStorage = () => {
    localStorage.setItem('novel_world_store', JSON.stringify({
      worldId: worldId.value,
      worldBible: worldBible.value,
      characters: characters.value,
      locations: locations.value,
      clues: clues.value,
      plotArcs: plotArcs.value,
      characterArcs: characterArcs.value,
    }))
  }

  // 监听所有数据变化并自动保存
  watch([worldId, worldBible, characters, locations, clues, plotArcs, characterArcs], saveToStorage, { deep: true })

  // 计算属性：配置完整度
  const completeness = computed(() => {
    let total = 0
    let complete = 0

    // 世界圣经
    if (worldBible.value) {
      total += 1
      complete += 1
    }

    // 角色 (至少 2 个)
    if (characters.value.length >= 2) {
      total += 1
      complete += 1
    } else {
      total += 1
    }

    // 地点 (至少 3 个)
    if (locations.value.length >= 3) {
      total += 1
      complete += 1
    } else {
      total += 1
    }

    // 线索 (至少 5 个)
    if (clues.value.length >= 5) {
      total += 1
      complete += 1
    } else {
      total += 1
    }

    // 剧情弧
    if (plotArcs.value.length >= 1) {
      total += 1
      complete += 1
    } else {
      total += 1
    }

    return total > 0 ? Math.round((complete / total) * 100) : 0
  })

  // 方法
  function loadWorld(id) {
    worldId.value = id

    // 模拟加载数据
    // 实际项目中这里会调用 API
    worldBible.value = {
      world_id: id,
      title: '旧医院真相',
      genre: '悬疑灵异',
      tone: '克制、压抑、现实中透出诡异',
      era: '现代都市',
      rules: [
        '旧医院午夜后才会出现四楼',
        '看门人害怕惹事，不会主动说出完整真相',
      ],
      themes: ['记忆是否可靠', '人如何逃避愧疚'],
    }

    characters.value = [
      {
        character_id: 'char_linzho',
        name: '林舟',
        role: 'protagonist',
        agent_type: 'core_agent',
        traits: ['克制', '敏感', '逃避冲突'],
        goals: {
          short_term: '确认旧医院是否与噩梦有关',
          long_term: '找回童年事故的真相',
        },
        skills: { observation: 75, social: 40, courage: 35, logic: 70 },
        initial_location: 'old_hospital_gate',
      },
      {
        character_id: 'char_guard',
        name: '老周',
        role: 'gatekeeper',
        agent_type: 'semi_agent_npc',
        traits: ['警惕', '怕惹事', '贪小便宜', '内心有愧'],
        goals: {
          short_term: '别让陌生人惹麻烦',
          long_term: '拿到钱就退休',
        },
        skills: { observation: 50, social: 60 },
        initial_location: 'old_hospital_gate',
      },
    ]

    locations.value = [
      {
        location_id: 'old_hospital_gate',
        name: '医院大门',
        public_description: '铁栅栏门锈迹斑斑，透过缝隙能看到里面破旧的住院楼。',
        connected_to: ['hospital_lobby'],
        objects: ['hospital_gate_lock', 'guard_booth'],
        available_topics: ['hospital_history', 'lock_condition'],
        danger_level: 1,
      },
      {
        location_id: 'hospital_lobby',
        name: '医院大厅',
        public_description: '大厅里落满灰尘，前台后方有一排旧柜子。',
        connected_to: ['old_hospital_gate', 'archive_room', 'second_floor'],
        objects: ['front_desk', 'old_cabinet', 'stairs'],
        available_topics: ['hospital_history', 'archive_room'],
        danger_level: 2,
      },
      {
        location_id: 'archive_room',
        name: '档案室',
        public_description: '一排排金属架子堆满了积灰的档案，空气中弥漫着陈旧的气味。',
        connected_to: ['hospital_lobby'],
        objects: ['file_shelf_1', 'file_shelf_2', 'locked_drawer'],
        available_topics: ['patient_records', 'old_incidents'],
        danger_level: 3,
      },
    ]

    clues.value = [
      {
        clue_id: 'hf_001',
        name: '最近更换的铁锁',
        content: '医院大门的锁最近被换过。',
        level: 'minor',
        arc_id: 'arc_hospital_truth',
        allowed_stages: ['setup', 'investigation'],
        importance: 60,
        discover_routes: [
          {
            route_id: 'route_hf001_inspect_lock',
            action_type: 'inspect',
            target: 'hospital_gate_lock',
            location_id: 'old_hospital_gate',
            required_skill: 'observation',
            difficulty: 60,
            result: '锁芯比锁身干净得多，像是最近刚换过。',
          },
        ],
      },
    ]

    plotArcs.value = [
      {
        arc_id: 'arc_hospital_truth',
        name: '旧医院真相篇',
        status: 'active',
        current_stage: 'setup',
        progress: 0,
        stages: [
          {
            stage_id: 'setup',
            name: '建立异常',
            purpose: '建立医院并非完全废弃的认知',
            allowed_clue_levels: ['surface', 'minor'],
            forbidden_revelations: ['ten_years_truth', 'real_killer_identity'],
          },
          {
            stage_id: 'investigation',
            name: '调查线索',
            purpose: '收集旧案相关证据',
            allowed_clue_levels: ['surface', 'minor', 'medium'],
            forbidden_revelations: ['real_killer_identity'],
          },
          {
            stage_id: 'confrontation',
            name: '冲突阶段',
            purpose: '与隐瞒者产生正面冲突',
            allowed_clue_levels: ['surface', 'minor', 'medium', 'major'],
            forbidden_revelations: [],
          },
          {
            stage_id: 'revelation',
            name: '真相揭露',
            purpose: '揭露部分真相',
            allowed_clue_levels: ['surface', 'minor', 'medium', 'major', 'truth'],
            forbidden_revelations: [],
          },
        ],
      },
    ]

    characterArcs.value = [
      {
        arc_id: 'arc_char_linzhou',
        character_id: 'char_linzho',
        character_name: '林舟',
        identity: '调查记者',
        core_desire: '找回童年记忆',
        psychological_wound: '童年目睹死亡却失忆',
        fear: '真相可能无法接受',
        lie: '我只是想了解医院历史',
        current_stage_index: 0,
        psychological_stages: [
          {
            stage_id: 'denial',
            stage_name: '否认',
            direction: 'growth',
            description: '拒绝承认自己与旧医院有任何联系',
            required_experiences: ['看到医院照片', '触发零星记忆'],
          },
          {
            stage_id: 'confusion',
            stage_name: '困惑',
            direction: 'growth',
            description: '开始怀疑自己的记忆，但无法确定真相',
            required_experiences: ['找到旧物品', '听到传闻'],
          },
          {
            stage_id: 'acceptance',
            stage_name: '接受',
            direction: 'growth',
            description: '逐渐接受过去的真相',
            required_experiences: ['找到证据', '面对知情人'],
          },
        ],
        reflection_points: [],
      },
    ]
  }

  function saveWorld() {
    // 模拟保存
    console.log('Saving world:', {
      worldId: worldId.value,
      worldBible: worldBible.value,
      characters: characters.value,
      locations: locations.value,
      clues: clues.value,
      plotArcs: plotArcs.value,
    })
  }

  function addCharacter(char) {
    characters.value.push(char)
  }

  function updateCharacter(index, char) {
    characters.value[index] = char
  }

  function removeCharacter(index) {
    characters.value.splice(index, 1)
  }

  function addLocation(location) {
    locations.value.push(location)
  }

  function updateLocation(index, location) {
    locations.value[index] = location
  }

  function removeLocation(index) {
    locations.value.splice(index, 1)
  }

  function addClue(clue) {
    clues.value.push(clue)
  }

  function updateClue(index, clue) {
    clues.value[index] = clue
  }

  function removeClue(index) {
    clues.value.splice(index, 1)
  }

  return {
    // state
    worldId,
    worldBible,
    characters,
    locations,
    clues,
    plotArcs,
    characterArcs,

    // computed
    completeness,

    // methods
    loadWorld,
    saveWorld,
    addCharacter,
    updateCharacter,
    removeCharacter,
    addLocation,
    updateLocation,
    removeLocation,
    addClue,
    updateClue,
    removeClue,
  }
})
