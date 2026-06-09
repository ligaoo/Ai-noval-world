import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export const useWorldStore = defineStore('world', () => {
  // 状态初始化：尝试从 localStorage 读取（添加版本号，防止旧数据冲突）
  const STORE_VERSION = '1.0.1'
  const loadState = () => {
    const saved = localStorage.getItem('novel_world_store')
    if (!saved) return null

    try {
      const parsed = JSON.parse(saved)
      // 如果版本不匹配，丢弃旧数据
      if (parsed._version !== STORE_VERSION) {
        console.log('Store version mismatch, discarding old data')
        return null
      }
      return parsed
    } catch {
      return null
    }
  }

  const savedState = loadState()

  const worldId = ref(savedState?.worldId || '')
  const worldBible = ref(savedState?.worldBible || null)
  const characters = ref(savedState?.characters || [])
  const locations = ref(savedState?.locations || [])
  const clues = ref(savedState?.clues || [])
  const plotArcs = ref(savedState?.plotArcs || [])
  const characterArcs = ref(savedState?.characterArcs || [])
  const isLoading = ref(false)
  const loadError = ref('')

  // 自动保存至 localStorage
  const saveToStorage = () => {
    localStorage.setItem('novel_world_store', JSON.stringify({
      _version: STORE_VERSION,
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
  const asArray = (value, key) => {
    if (Array.isArray(value)) return value
    if (value && Array.isArray(value[key])) return value[key]
    return []
  }

  const normalizeCharacters = (value) => asArray(value, 'characters').map((char, index) => {
    const characterId = char.character_id || char.id || `char_${index + 1}`
    return {
      ...char,
      character_id: characterId,
      id: char.id || characterId,
      traits: char.traits || char.personality_traits || char.personality?.traits || [],
      goals: char.goals || (char.goal ? { short_term: char.goal, long_term: char.goal } : { short_term: '', long_term: '' }),
      initial_location: char.initial_location || char.location_id || '',
    }
  })

  const normalizeLocations = (value) => asArray(value, 'locations').map((location, index) => {
    const locationId = location.location_id || location.id || `location_${index + 1}`
    return {
      ...location,
      location_id: locationId,
      id: location.id || locationId,
      connected_to: location.connected_to || [],
      objects: location.objects || [],
    }
  })

  const normalizeClues = (value) => asArray(value, 'clues').map((clue, index) => {
    const clueId = clue.clue_id || clue.id || `clue_${index + 1}`
    return {
      ...clue,
      clue_id: clueId,
      id: clue.id || clueId,
      name: clue.name || clue.title || clueId,
      level: clue.level || clue.truth_level || 'minor',
      discover_routes: clue.discover_routes || [],
    }
  })

  const normalizePlotArcs = (value) => asArray(value, 'arcs')
  const normalizeCharacterArcs = (value) => asArray(value, 'arcs')

  function applyWorldPayload(payload, fallbackId = '') {
    const bible = payload?.world_bible || {}
    worldId.value = payload?.id || bible.world_id || fallbackId
    worldBible.value = {
      ...bible,
      world_id: bible.world_id || payload?.id || fallbackId,
      rules: bible.rules || [],
      themes: bible.themes || [],
    }
    characters.value = normalizeCharacters(payload?.characters)
    locations.value = normalizeLocations(payload?.map)
    clues.value = normalizeClues(payload?.clues)
    plotArcs.value = normalizePlotArcs(payload?.plot_arcs)
    characterArcs.value = normalizeCharacterArcs(payload?.character_arcs)
  }

  function clearWorld() {
    worldId.value = ''
    worldBible.value = null
    characters.value = []
    locations.value = []
    clues.value = []
    plotArcs.value = []
    characterArcs.value = []
  }

  async function loadWorld(id) {
    if (!id) {
      clearWorld()
      return null
    }

    isLoading.value = true
    loadError.value = ''
    try {
      const response = await fetch(`http://localhost:8421/api/worlds/${id}`)
      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.detail || data?.message || '加载世界失败')
      }
      applyWorldPayload(data, id)
      return data
    } catch (error) {
      loadError.value = error?.message || '加载世界失败'
      clearWorld()
      throw error
    } finally {
      isLoading.value = false
    }
  }

  async function saveWorld() {
    const currentWorldId = worldId.value || worldBible.value?.world_id
    if (!currentWorldId) {
      throw new Error('请先选择一个世界')
    }
    const response = await fetch(`http://localhost:8421/api/worlds/${currentWorldId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        world_bible: worldBible.value || {},
        characters: characters.value,
        map: locations.value,
        clues: clues.value,
        plot_arcs: plotArcs.value,
        character_arcs: characterArcs.value,
      }),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new Error(data?.detail || data?.message || '保存世界失败')
    }
    return data
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
    isLoading,
    loadError,

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
