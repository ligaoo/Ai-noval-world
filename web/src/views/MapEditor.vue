<template>
  <div class="space-y-8">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-3xl font-bold bg-gradient-to-r from-neon-purple to-neon-pink bg-clip-text text-transparent">
          地图编辑器
        </h2>
        <p class="text-gray-400 mt-1">设计地点、连接关系和危险等级</p>
      </div>
      <div class="flex items-center gap-3">
        <PButton
          :label="isGraphView ? '列表视图' : '节点视图'"
          :icon="isGraphView ? 'pi pi-list' : 'pi pi-sitemap'"
          text
          @click="isGraphView = !isGraphView"
        />
        <PButton label="添加地点" icon="pi pi-plus" @click="showAddDialog = true" />
      </div>
    </div>

    <!-- 图形视图 -->
    <div v-if="isGraphView" class="glass-card p-8 min-h-[600px] relative overflow-hidden">
      <!-- 图例 -->
      <div class="absolute top-4 right-4 z-10 bg-noir-800/80 backdrop-blur-sm p-4 rounded-xl space-y-2">
        <div class="text-sm font-medium mb-2">图例</div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-green-500"></div>
          <span class="text-xs text-gray-400">安全</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-amber-500"></div>
          <span class="text-xs text-gray-400">中等</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 rounded-full bg-red-500"></div>
          <span class="text-xs text-gray-400">危险</span>
        </div>
      </div>

      <!-- SVG 画布 -->
      <svg class="w-full h-full" style="min-height: 500px;">
        <!-- 连接线 -->
        <g v-for="loc in locations" :key="`lines-${loc.location_id}`">
          <line
            v-for="targetId in loc.connected_to"
            :key="`${loc.location_id}-${targetId}`"
            :x1="getNodePosition(loc.location_id).x"
            :y1="getNodePosition(loc.location_id).y"
            :x2="getNodePosition(targetId).x"
            :y2="getNodePosition(targetId).y"
            stroke="#4b5563"
            stroke-width="2"
            stroke-dasharray="8,4"
          />
        </g>

        <!-- 节点 -->
        <g v-for="loc in locations" :key="loc.location_id">
          <!-- 节点圆圈 -->
          <circle
            :cx="getNodePosition(loc.location_id).x"
            :cy="getNodePosition(loc.location_id).y"
            r="50"
            :fill="getDangerColor(loc.danger_level)"
            class="cursor-pointer hover:opacity-80 transition-opacity"
            :stroke="selectedNode === loc.location_id ? '#a855f7' : '#4b5563'"
            stroke-width="3"
            @click="selectedNode = loc.location_id"
          />

          <!-- 节点标签 -->
          <text
            :x="getNodePosition(loc.location_id).x"
            :y="getNodePosition(loc.location_id).y"
            text-anchor="middle"
            dominant-baseline="middle"
            fill="white"
            font-size="14"
            font-weight="600"
            class="pointer-events-none"
          >
            {{ loc.name }}
          </text>

          <!-- 危险等级 -->
          <text
            :x="getNodePosition(loc.location_id).x"
            :y="getNodePosition(loc.location_id).y + 22"
            text-anchor="middle"
            fill="#9ca3af"
            font-size="11"
            class="pointer-events-none"
          >
            危险等级: {{ loc.danger_level }} / 5
          </text>
        </g>
      </svg>

      <!-- 选中节点信息 -->
      <div
        v-if="selectedNode"
        class="absolute bottom-4 left-4 right-4 glass-card p-4"
      >
        <div class="flex items-start justify-between">
          <div>
            <h4 class="font-semibold text-lg">{{ selectedLocation?.name }}</h4>
            <p class="text-gray-400 text-sm mt-1">{{ selectedLocation?.public_description }}</p>
            <div class="flex items-center gap-4 mt-3">
              <div class="text-sm">
                <span class="text-gray-500">可前往：</span>
                <span class="text-neon-cyan">{{ selectedLocation?.connected_to?.length || 0 }} 个地点</span>
              </div>
              <div class="text-sm">
                <span class="text-gray-500">物品：</span>
                <span class="text-neon-blue">{{ selectedLocation?.objects?.length || 0 }} 个</span>
              </div>
            </div>
          </div>
          <PButton
            label="编辑"
            icon="pi pi-pencil"
            text
            size="small"
            @click="editLocation(selectedNode)"
          />
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-else class="space-y-4">
      <div
        v-for="(loc, index) in locations"
        :key="loc.location_id"
        class="glass-card p-6 hover-lift"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-start gap-4 flex-1">
            <!-- 危险等级指示器 -->
            <div
              class="w-16 h-16 rounded-xl flex items-center justify-center text-xl font-bold"
              :class="getDangerColor(loc.danger_level)"
            >
              {{ loc.danger_level }}
            </div>

            <div class="flex-1">
              <div class="flex items-center gap-3 mb-2">
                <h3 class="text-lg font-semibold">{{ loc.name }}</h3>
                <span class="text-xs text-gray-500">{{ loc.location_id }}</span>
              </div>
              <p class="text-gray-400 text-sm mb-3">{{ loc.public_description }}</p>

              <!-- 物品标签 -->
              <div class="flex flex-wrap gap-2 mb-2">
                <span
                  v-for="obj in loc.objects"
                  :key="obj"
                  class="tag tag-info"
                >
                  {{ obj }}
                </span>
              </div>

              <!-- 可前往地点 -->
              <div class="flex items-center gap-2 text-sm">
                <span class="text-gray-500">可前往：</span>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="targetId in loc.connected_to"
                    :key="targetId"
                    class="px-2 py-0.5 rounded-full text-xs bg-neon-purple/20 text-neon-purple"
                  >
                    {{ getLocationName(targetId) }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <PButton
              icon="pi pi-pencil"
              text
              class="p-button-text"
              @click="editLocation(loc.location_id)"
            />
            <PButton
              icon="pi pi-trash"
              text
              class="p-button-text p-button-danger"
              @click="deleteLocation(index)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 添加/编辑地点弹窗 -->
    <PDialog
      v-model:visible="showAddDialog"
      header="添加地点"
      :modal="true"
      class="w-full max-w-2xl"
      contentStyle="background: #2a2d35; border: 1px solid #374151"
    >
      <div class="space-y-6">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="text-sm text-gray-400 block mb-2">地点 ID</label>
            <PInputText
              v-model="newLocation.location_id"
              class="w-full input-dark"
              placeholder="例如：hospital_lobby"
            />
          </div>
          <div>
            <label class="text-sm text-gray-400 block mb-2">地点名称</label>
            <PInputText
              v-model="newLocation.name"
              class="w-full input-dark"
              placeholder="例如：医院大厅"
            />
          </div>
        </div>

        <div>
          <label class="text-sm text-gray-400 block mb-2">公开描述</label>
          <PTextarea
            v-model="newLocation.public_description"
            class="w-full input-dark"
            rows="3"
            placeholder="描述这个地点的外观..."
          />
        </div>

        <div>
          <label class="text-sm text-gray-400 block mb-2">危险等级</label>
          <input
            type="range"
            v-model.number="newLocation.danger_level"
            min="1"
            max="5"
            class="w-full accent-neon-purple"
          />
          <div class="text-center text-neon-purple font-bold mt-1">
            {{ newLocation.danger_level }} / 5
          </div>
        </div>

        <div>
          <label class="text-sm text-gray-400 block mb-2">可前往地点</label>
          <div class="flex flex-wrap gap-2 mb-3">
            <span
              v-for="(targetId, i) in newLocation.connected_to"
              :key="i"
              class="px-3 py-1 rounded-full text-sm bg-noir-700 text-gray-300 flex items-center gap-2"
            >
              {{ getLocationName(targetId) }}
              <button class="hover:text-neon-pink" @click="newLocation.connected_to.splice(i, 1)">
                ×
              </button>
            </span>
          </div>
          <PDropdown
            v-model="selectedConnection"
            :options="availableConnections"
            optionLabel="name"
            optionValue="id"
            placeholder="选择连接地点"
            class="w-full"
            @change="addConnection"
          />
        </div>

        <div>
          <label class="text-sm text-gray-400 block mb-2">物品列表</label>
          <div class="flex flex-wrap gap-2 mb-3">
            <span
              v-for="(obj, i) in newLocation.objects"
              :key="i"
              class="px-3 py-1 rounded-full text-sm bg-noir-700 text-gray-300 flex items-center gap-2"
            >
              {{ obj }}
              <button class="hover:text-neon-pink" @click="newLocation.objects.splice(i, 1)">
                ×
              </button>
            </span>
          </div>
          <div class="flex gap-2">
            <PInputText
              v-model="newObject"
              class="input-dark flex-1"
              placeholder="添加物品..."
              @keyup.enter="addObject"
            />
            <PButton label="添加" text @click="addObject" />
          </div>
        </div>
      </div>

      <template #footer>
        <PButton label="取消" severity="secondary" text @click="showAddDialog = false" />
        <PButton label="保存" @click="saveLocation" />
      </template>
    </PDialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useWorldStore } from '@/stores/world'

const worldStore = useWorldStore()

const isGraphView = ref(true)
const showAddDialog = ref(false)
const selectedNode = ref(null)
const selectedConnection = ref(null)
const newObject = ref('')

const locations = computed(() => worldStore.locations)

const selectedLocation = computed(() => {
  return locations.value.find(l => l.location_id === selectedNode.value)
})

const availableConnections = computed(() => {
  return locations.value
    .filter(l => !newLocation.value.connected_to.includes(l.location_id) && l.location_id !== newLocation.value.location_id)
    .map(l => ({ id: l.location_id, name: l.name }))
})

const newLocation = ref({
  location_id: '',
  name: '',
  public_description: '',
  connected_to: [],
  objects: [],
  available_topics: [],
  danger_level: 1,
})

// 节点位置计算
function getNodePosition(locationId) {
  const index = locations.value.findIndex(l => l.location_id === locationId)
  const total = locations.value.length
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2

  const centerX = 400
  const centerY = 250
  const radius = 180

  return {
    x: centerX + Math.cos(angle) * radius,
    y: centerY + Math.sin(angle) * radius,
  }
}

function getDangerColor(level) {
  const colors = {
    1: 'rgba(34, 197, 94, 0.3)',
    2: 'rgba(168, 85, 247, 0.3)',
    3: 'rgba(59, 130, 246, 0.3)',
    4: 'rgba(245, 158, 11, 0.3)',
    5: 'rgba(239, 68, 68, 0.3)',
  }
  return colors[level] || colors[1]
}

function getLocationName(locationId) {
  const loc = locations.value.find(l => l.location_id === locationId)
  return loc ? loc.name : locationId
}

function addConnection() {
  if (selectedConnection.value && !newLocation.value.connected_to.includes(selectedConnection.value)) {
    newLocation.value.connected_to.push(selectedConnection.value)
    selectedConnection.value = null
  }
}

function addObject() {
  if (newObject.value.trim() && !newLocation.value.objects.includes(newObject.value.trim())) {
    newLocation.value.objects.push(newObject.value.trim())
    newObject.value = ''
  }
}

function editLocation(locationId) {
  const loc = locations.value.find(l => l.location_id === locationId)
  if (loc) {
    newLocation.value = { ...loc }
    showAddDialog.value = true
  }
}

function deleteLocation(index) {
  if (confirm('确定删除这个地点吗？')) {
    worldStore.removeLocation(index)
  }
}

function saveLocation() {
  if (newLocation.value.location_id && newLocation.value.name) {
    const existingIndex = locations.value.findIndex(
      l => l.location_id === newLocation.value.location_id
    )
    if (existingIndex >= 0) {
      worldStore.updateLocation(existingIndex, { ...newLocation.value })
    } else {
      worldStore.addLocation({ ...newLocation.value })
    }
    showAddDialog.value = false
    // 重置表单
    newLocation.value = {
      location_id: '',
      name: '',
      public_description: '',
      connected_to: [],
      objects: [],
      available_topics: [],
      danger_level: 1,
    }
  }
}
</script>
