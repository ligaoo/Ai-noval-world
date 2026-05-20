<template>
  <div style="max-width: 1200px; margin: 0 auto;">
    <!-- 页面标题 -->
    <div style="margin-bottom: 32px; display: flex; align-items: center; justify-content: space-between;">
      <div>
        <h2 style="font-size: 32px; font-weight: 700; background: linear-gradient(135deg, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
          世界总览
        </h2>
        <p style="color: #9ca3af; margin-top: 8px;">管理和配置你的小说世界</p>
      </div>
      <div style="display: flex; gap: 12px;">
        <PButton label="生成 NPC" icon="pi pi-users" @click="goTo('/generator/npc')" />
        <PButton label="生成线索" icon="pi pi-search" @click="goTo('/generator/clue')" />
        <PButton label="生成角色" icon="pi pi-user-plus" @click="goTo('/generator/character')" />
        <PButton 
          :label="isSimulating ? '模拟中...' : '开始模拟'" 
          icon="pi pi-play" 
          severity="info" 
          @click="startSimulation"
          :disabled="isSimulating"
          :loading="isSimulating"
        />
      </div>
    </div>
    <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 12px; padding: 12px 16px; margin-bottom: 20px; color: #d1fae5;">
      当前默认运行链路：`开 move` · `开记忆` · `开 LLM 叙事改写` · `开一致性检查+修订`（`llm + v2.3`）
    </div>

    <!-- 世界选择器 -->
    <div style="background: rgba(42, 45, 53, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px; margin-bottom: 24px;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
        <h3 style="font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 12px;">
          <Globe style="width: 20px; height: 20px; color: #a855f7;" />
          选择世界
        </h3>
        <button 
          @click="showCreateDialog = true"
          style="background: linear-gradient(135deg, #a855f7, #ec4899); color: white; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; display: flex; align-items: center; gap: 6px;"
        >
          <Plus style="width: 16px; height: 16px;" />
          创建新世界
        </button>
      </div>
      <div style="display: flex; gap: 12px; align-items: flex-end;">
        <div style="flex: 1;">
          <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">已有的世界</label>
          <select
            v-model="selectedWorldId"
            @change="loadSelectedWorld"
            style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none; cursor: pointer;"
          >
            <option value="" disabled>-- 请选择世界 --</option>
            <option v-for="world in availableWorlds" :key="world.id" :value="world.id">
              {{ world.title || world.id }} ({{ world.id }})
            </option>
          </select>
        </div>
        <button 
          @click="loadWorldsList"
          style="background: #374151; color: white; border: none; padding: 12px; border-radius: 12px; cursor: pointer;"
          title="刷新列表"
        >
          <RefreshCw style="width: 18px; height: 18px;" />
        </button>
      </div>
    </div>

    <!-- 世界圣经卡片 -->
    <div style="display: grid; grid-template-columns: repeat(1, minmax(0, 1fr)); gap: 24px; margin-bottom: 32px;">
      <div style="background: rgba(42, 45, 53, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
          <h3 style="font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 12px;">
            <BookOpen style="width: 24px; height: 24px; color: #a855f7;" />
            世界圣经
          </h3>
        </div>

        <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 16px;">
          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">世界 ID</label>
            <input
              v-model="worldBible.world_id"
              placeholder="例如：dark_city_001"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
          </div>
          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">标题</label>
            <input
              v-model="worldBible.title"
              placeholder="世界名称"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
          </div>
          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">题材</label>
            <select
              v-model="worldBible.genre"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            >
              <option value="悬疑">选择题材</option>
              <option value="悬疑灵异">悬疑灵异</option>
              <option value="都市异能">都市异能</option>
              <option value="武侠仙侠">武侠仙侠</option>
              <option value="科幻未来">科幻未来</option>
            </select>
          </div>
          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">时代背景</label>
            <input
              v-model="worldBible.era"
              placeholder="例如：现代都市"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
          </div>
        </div>

        <div style="margin-bottom: 16px;">
          <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">基调</label>
          <textarea
            v-model="worldBible.tone"
            rows="2"
            placeholder="描述整个世界的基调氛围..."
            style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none; resize: vertical;"
          ></textarea>
        </div>

        <div style="margin-bottom: 16px;">
          <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">世界规则</label>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <input
              v-for="(rule, index) in worldBible.rules"
              :key="index"
              v-model="worldBible.rules[index]"
              placeholder="例如：旧医院午夜后才会出现四楼"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
          </div>
          <button
            @click="worldBible.rules.push('')"
            style="margin-top: 8px; background: transparent; color: #a855f7; border: none; cursor: pointer; font-size: 14px; display: flex; align-items: center; gap: 8px;"
          >
            <Plus style="width: 16px; height: 16px;" />
            添加规则
          </button>
        </div>

        <div>
          <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">主题</label>
          <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            <span
              v-for="(theme, index) in worldBible.themes"
              :key="index"
              style="background: rgba(168, 85, 247, 0.2); color: #a855f7; padding: 4px 12px; border-radius: 20px; font-size: 14px; display: flex; align-items: center; gap: 8px;"
            >
              {{ theme }}
              <button
                @click="worldBible.themes.splice(index, 1)"
                style="background: none; border: none; color: #a855f7; cursor: pointer; padding: 0;"
              >
                ×
              </button>
            </span>
            <button
              @click="addTheme"
              style="background: rgba(168, 85, 247, 0.1); color: #a855f7; border: 1px dashed #a855f7; padding: 4px 12px; border-radius: 20px; font-size: 14px; cursor: pointer;"
            >
              + 添加主题
            </button>
          </div>
        </div>
      </div>

      <!-- 配置统计卡片 -->
      <div style="background: rgba(42, 45, 53, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px;">
        <h3 style="font-size: 20px; font-weight: 600; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
          <BarChart3 style="width: 24px; height: 24px; color: #3b82f6;" />
          配置统计
        </h3>
        <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px;">
          <div style="background: rgba(28, 30, 36, 0.6); padding: 16px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <Users style="width: 20px; height: 20px; color: #10b981;" />
              <span style="color: #9ca3af;">角色</span>
            </div>
            <span style="color: #10b981; font-weight: 600; font-size: 18px;">{{ characterCount }}</span>
          </div>
          <div style="background: rgba(28, 30, 36, 0.6); padding: 16px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <Map style="width: 20px; height: 20px; color: #3b82f6;" />
              <span style="color: #9ca3af;">地点</span>
            </div>
            <span style="color: #3b82f6; font-weight: 600; font-size: 18px;">{{ locationCount }}</span>
          </div>
          <div style="background: rgba(28, 30, 36, 0.6); padding: 16px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <Search style="width: 20px; height: 20px; color: #f59e0b;" />
              <span style="color: #9ca3af;">线索</span>
            </div>
            <span style="color: #f59e0b; font-weight: 600; font-size: 18px;">{{ clueCount }}</span>
          </div>
          <div style="background: rgba(28, 30, 36, 0.6); padding: 16px; border-radius: 12px; display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center; gap: 12px;">
              <GitBranch style="width: 20px; height: 20px; color: #ec4899;" />
              <span style="color: #9ca3af;">剧情弧</span>
            </div>
            <span style="color: #ec4899; font-weight: 600; font-size: 18px;">{{ plotArcCount }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 快速操作卡片 -->
    <div style="background: rgba(42, 45, 53, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px; margin-bottom: 32px;">
      <h3 style="font-size: 20px; font-weight: 600; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
        <Zap style="width: 24px; height: 24px; color: #f59e0b;" />
        快速操作
      </h3>
      <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px;">
        <div
          @click="goTo('/characters')"
          class="quick-action-card"
          style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #10b981; padding: 16px; border-radius: 12px; text-align: left; cursor: pointer; transition: all 0.2s ease;"
        >
          <Users style="width: 24px; height: 24px; margin-bottom: 8px;" />
          <div style="font-weight: 600;">添加新角色</div>
          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">创建小说中的重要人物</div>
        </div>
        <div
          @click="goTo('/map')"
          class="quick-action-card"
          style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); color: #3b82f6; padding: 16px; border-radius: 12px; text-align: left; cursor: pointer; transition: all 0.2s ease;"
        >
          <Map style="width: 24px; height: 24px; margin-bottom: 8px;" />
          <div style="font-weight: 600;">编辑地图</div>
          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">管理地点和连通关系</div>
        </div>
        <div
          @click="goTo('/clues')"
          class="quick-action-card"
          style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: #f59e0b; padding: 16px; border-radius: 12px; text-align: left; cursor: pointer; transition: all 0.2s ease;"
        >
          <Search style="width: 24px; height: 24px; margin-bottom: 8px;" />
          <div style="font-weight: 600;">设计线索</div>
          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">创建悬念和发现路径</div>
        </div>
        <div
          @click="goTo('/plot-arc')"
          class="quick-action-card"
          style="background: rgba(236, 72, 153, 0.1); border: 1px solid rgba(236, 72, 153, 0.3); color: #ec4899; padding: 16px; border-radius: 12px; text-align: left; cursor: pointer; transition: all 0.2s ease;"
        >
          <GitBranch style="width: 24px; height: 24px; margin-bottom: 8px;" />
          <div style="font-weight: 600;">规划剧情</div>
          <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">设计剧情弧和阶段</div>
        </div>
      </div>
    </div>

    <!-- 配置验证 -->
    <div style="background: rgba(42, 45, 53, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px;">
      <h3 style="font-size: 20px; font-weight: 600; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
        <CheckCircle style="width: 24px; height: 24px; color: #10b981;" />
        配置验证
      </h3>
      <div style="display: flex; flex-direction: column; gap: 12px;">
        <div
          v-for="check in validationChecks"
          :key="check.name"
          class="validation-item"
          :class="{ passed: check.passed, failed: !check.passed }"
        >
          <CheckCircle v-if="check.passed" style="width: 20px; height: 20px; color: #10b981;" />
          <XCircle v-else style="width: 20px; height: 20px; color: #ef4444;" />
          <span :style="{ color: check.passed ? '#10b981' : '#ef4444', fontWeight: '500' }">{{ check.name }}</span>
          <span style="color: #6b7280; font-size: 14px;">{{ check.message }}</span>
        </div>
      </div>
    </div>

    <!-- 创建新世界对话框 -->
    <div 
      v-if="showCreateDialog"
      style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 1000;"
    >
      <div style="background: #2a2d35; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 32px; width: 100%; max-width: 500px;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
          <h3 style="font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 12px;">
            <Plus style="width: 24px; height: 24px; color: #a855f7;" />
            创建新世界
          </h3>
          <button 
            @click="showCreateDialog = false"
            style="background: none; border: none; color: #9ca3af; cursor: pointer; padding: 4px; font-size: 24px;"
          >
            ×
          </button>
        </div>

        <div style="display: flex; flex-direction: column; gap: 16px;">
          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">世界 ID <span style="color: #ef4444;">*</span></label>
            <input
              v-model="newWorldForm.world_id"
              placeholder="例如：my_world_001"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
            <p style="font-size: 12px; color: #6b7280; margin-top: 4px;">只能包含字母、数字、下划线和连字符</p>
          </div>

          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">世界标题 <span style="color: #ef4444;">*</span></label>
            <input
              v-model="newWorldForm.title"
              placeholder="例如：我的小说世界"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
          </div>

          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">题材类型</label>
            <select
              v-model="newWorldForm.genre"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            >
              <option value="horror">恐怖/悬疑</option>
              <option value="fantasy">奇幻</option>
              <option value="scifi">科幻</option>
              <option value="romance">言情</option>
              <option value="mystery">推理</option>
            </select>
          </div>

          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">时代背景</label>
            <input
              v-model="newWorldForm.era"
              placeholder="例如：现代都市"
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
            />
          </div>

          <div>
            <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">基调</label>
            <textarea
              v-model="newWorldForm.tone"
              rows="2"
              placeholder="描述整个世界的基调氛围..."
              style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none; resize: vertical;"
            ></textarea>
          </div>
        </div>

        <div style="display: flex; gap: 12px; margin-top: 24px;">
          <button
            @click="showCreateDialog = false"
            style="flex: 1; background: #374151; color: white; border: none; padding: 12px; border-radius: 12px; cursor: pointer; font-size: 14px;"
          >
            取消
          </button>
          <button
            @click="createNewWorld"
            :disabled="isCreatingWorld"
            style="flex: 1; background: linear-gradient(135deg, #a855f7, #ec4899); color: white; border: none; padding: 12px; border-radius: 12px; cursor: pointer; font-size: 14px; opacity: isCreatingWorld ? 0.5 : 1;"
          >
            {{ isCreatingWorld ? '创建中...' : '创建世界' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWorldStore } from '@/stores/world'
import {
  BookOpen,
  Users,
  Map,
  Search,
  GitBranch,
  BarChart3,
  Zap,
  CheckCircle,
  XCircle,
  Plus,
  Globe,
  RefreshCw,
} from 'lucide-vue-next'

const router = useRouter()
const worldStore = useWorldStore()

// 世界列表相关
const availableWorlds = ref([])
const selectedWorldId = ref('')
const showCreateDialog = ref(false)
const isCreatingWorld = ref(false)

// 创建新世界的表单数据
const newWorldForm = ref({
  world_id: '',
  title: '',
  genre: 'horror',
  tone: '',
  era: 'Modern'
})

// 加载世界列表
const loadWorldsList = async () => {
  try {
    const response = await fetch('http://localhost:8421/api/worlds')
    const data = await response.json()
    availableWorlds.value = data.worlds || []
  } catch (error) {
    console.error('加载世界列表失败:', error)
  }
}

// 加载选中的世界
const loadSelectedWorld = async () => {
  if (!selectedWorldId.value) return
  
  try {
    const response = await fetch(`http://localhost:8421/api/worlds/${selectedWorldId.value}`)
    if (!response.ok) throw new Error('World not found')
    
    const worldData = await response.json()
    
    worldStore.worldBible = worldData.world_bible || {}
    worldStore.characters = worldData.characters?.characters || []
    worldStore.locations = worldData.map?.locations || []
    worldStore.clues = worldData.clues?.clues || []
    
    alert(`✅ 已加载世界: ${worldStore.worldBible.title}`)
  } catch (error) {
    console.error('加载世界失败:', error)
    alert(`❌ 加载世界失败: ${error.message}`)
  }
}

// 创建新世界
const createNewWorld = async () => {
  if (!newWorldForm.value.world_id || !newWorldForm.value.title) {
    alert('请填写世界 ID 和标题')
    return
  }
  
  if (!/^[a-zA-Z0-9_-]+$/.test(newWorldForm.value.world_id)) {
    alert('世界 ID 只能包含字母、数字、下划线和连字符')
    return
  }

  isCreatingWorld.value = true
  
  try {
    const response = await fetch('http://localhost:8421/api/worlds/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newWorldForm.value)
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '创建失败')
    }

    const result = await response.json()
    
    if (result.success) {
      alert(`✅ 创建成功！\n\n世界: ${result.message}`)
      showCreateDialog.value = false
      
      newWorldForm.value = {
        world_id: '',
        title: '',
        genre: 'horror',
        tone: '',
        era: 'Modern'
      }
      
      await loadWorldsList()
      selectedWorldId.value = result.world_id
      await loadSelectedWorld()
    }
  } catch (error) {
    console.error('创建世界失败:', error)
    alert(`❌ 创建失败\n\n${error.message}`)
  } finally {
    isCreatingWorld.value = false
  }
}

// 确保 worldBible 始终是一个有效对象，防止 v-model 绑定到临时空对象导致数据丢失
const worldBible = computed(() => {
  if (!worldStore.worldBible) {
    worldStore.worldBible = {
      world_id: 'dark_city_001',
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
  }
  return worldStore.worldBible
})

// 初始化加载
onMounted(async () => {
  await loadWorldsList()
  
  if (!worldStore.worldBible && availableWorlds.value.length > 0) {
    selectedWorldId.value = availableWorlds.value[0].id
    await loadSelectedWorld()
  }
})

const characterCount = computed(() => worldStore.characters.length)
const locationCount = computed(() => worldStore.locations.length)
const clueCount = computed(() => worldStore.clues.length)
const plotArcCount = computed(() => worldStore.plotArcs.length)

const validationChecks = computed(() => [
  {
    name: '世界圣经',
    passed: !!worldBible.value.title && worldBible.value.rules.length > 0,
    message: worldBible.value.title && worldBible.value.rules.length > 0 ? '已配置' : '需要完善',
  },
  {
    name: '角色配置',
    passed: characterCount.value >= 2,
    message: characterCount.value >= 2 ? `已配置 ${characterCount.value} 个角色` : `至少需要 2 个角色`,
  },
  {
    name: '地点配置',
    passed: locationCount.value >= 3,
    message: locationCount.value >= 3 ? `已配置 ${locationCount.value} 个地点` : `至少需要 3 个地点`,
  },
  {
    name: '线索配置',
    passed: clueCount.value >= 5,
    message: clueCount.value >= 5 ? `已配置 ${clueCount.value} 条线索` : `建议至少 5 条线索`,
  },
])

const addTheme = () => {
  worldBible.value.themes.push('新主题')
}

const goTo = (path) => {
  router.push(path)
}

const isSimulating = ref(false)
const simulationResult = ref(null)

const startSimulation = async () => {
  if (isSimulating.value) return
  
  // 验证基本配置
  if (!worldBible.value.world_id || !worldBible.value.title) {
    alert('请先填写世界圣经的基本信息（世界 ID 和标题）')
    return
  }

  isSimulating.value = true
  simulationResult.value = null

  try {
    // 1. 启动模拟
    const response = await fetch('http://localhost:8421/api/simulations/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        world_id: worldBible.value.world_id,
        mode: 'llm',
        v2_phase: 'v2.3',
        seed: 12345,
        genre_id: 'horror',
        target_chapters: 10,
        chapter_no: 1
      })
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || '启动模拟失败')
    }

    const startResult = await response.json()
    const simId = startResult.sim_id
    
    console.log('模拟已启动，ID:', simId)

    // 2. 轮询检查状态
    let pollCount = 0
    const maxPolls = 300 // 最多等 5 分钟（每次 1 秒）
    
    while (pollCount < maxPolls) {
      await new Promise(resolve => setTimeout(resolve, 1000))
      pollCount++

      try {
        const statusRes = await fetch(`http://localhost:8421/api/simulations/${simId}/status`)
        if (!statusRes.ok) continue
        
        const status = await statusRes.json()
        console.log('模拟状态:', status)

        if (status.status === 'completed') {
          simulationResult.value = status
          alert(`✅ 模拟完成！\n\n模拟 ID: ${status.simulation_id || simId}\n运行模式: llm / v2.3`)
          break
        } else if (status.status === 'failed') {
          throw new Error(status.error || '模拟运行失败')
        }
        // 继续等待 running 状态
      } catch (e) {
        console.warn('检查状态失败:', e)
      }
    }

    if (pollCount >= maxPolls) {
      alert(`⏱ 模拟仍在运行中...\n\n模拟 ID: ${simId}\n请稍后在模拟列表中查看结果`)
    }

  } catch (error) {
    console.error('模拟请求失败:', error)
    alert(`❌ 模拟请求失败\n\n错误信息: ${error.message}\n\n请确保后端服务正在运行 (端口 8421)`)
  } finally {
    isSimulating.value = false
  }
}
</script>

<style scoped>
.quick-action-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.validation-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
}

.validation-item.passed {
  background: rgba(16, 185, 129, 0.1);
}

.validation-item.failed {
  background: rgba(239, 68, 68, 0.1);
}
</style>
