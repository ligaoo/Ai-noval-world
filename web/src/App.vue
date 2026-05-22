<template>
  <div class="app-container">
    <header class="app-header">
      <div class="header-content">
        <h1 class="app-title">🎭 小说沙盘 V4.2</h1>
        <span class="app-subtitle">AI辅助小说生成增强版</span>
      </div>
    </header>

    <div class="main-layout">
      <aside class="sidebar">
        <nav class="nav-menu">
          <div class="nav-section">
          <h3 class="nav-section-title">生成器</h3>
          <router-link
            v-for="item in generatorNavItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: $route.name === item.name }"
          >
            <component :is="item.icon" class="nav-icon" />
            <span>{{ item.title }}</span>
          </router-link>
        </div>
          <div class="nav-section">
          <h3 class="nav-section-title">管理</h3>
          <router-link
            v-for="item in managementNavItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: $route.name === item.name }"
          >
            <component :is="item.icon" class="nav-icon" />
            <span>{{ item.title }}</span>
          </router-link>
        </div>
        </nav>
      </aside>

      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useWorldStore } from '@/stores/world'
import { Home, Users, Users2, Map, Search, GitBranch, UserCheck, CheckCircle2, Wand2 } from 'lucide-vue-next'

const worldStore = useWorldStore()

onMounted(() => {
  if (worldStore.characters.length === 0) {
    worldStore.loadWorld('dark_city_001')
  }
})

const generatorNavItems = [
  {
    path: '/',
    name: 'home',
    title: '总览',
    icon: Home
  },
  {
    path: '/bootstrap',
    name: 'bootstrap',
    title: 'Story Bootstrap',
    icon: Wand2
  },
  {
    path: '/generator/character',
    name: 'character-generator',
    title: '角色生成器',
    icon: Users
  },
  {
    path: '/generator/npc',
    name: 'npc-generator',
    title: 'NPC生成器',
    icon: Users2
  },
  {
    path: '/generator/clue',
    name: 'clue-generator',
    title: '线索生成器',
    icon: Search
  }
]

const managementNavItems = [
  {
    path: '/characters',
    name: 'characters',
    title: '角色管理',
    icon: Users
  },
  {
    path: '/clues',
    name: 'clues',
    title: '线索管理',
    icon: Search
  },
  {
    path: '/map',
    name: 'map',
    title: '地图编辑',
    icon: Map
  },
  {
    path: '/plot-arc',
    name: 'plot-arc',
    title: '剧情弧',
    icon: GitBranch
  },
  {
    path: '/character-arc',
    name: 'character-arc',
    title: '角色弧',
    icon: UserCheck
  },
  {
    path: '/generator/review',
    name: 'candidate-review',
    title: '候选审核面板',
    icon: CheckCircle2
  }
]
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
}

.app-header {
  background: rgba(26, 26, 46, 0.95);
  border-bottom: 1px solid rgba(139, 92, 246, 0.3);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  gap: 1rem;
}

.app-title {
  font-size: 1.5rem;
  font-weight: bold;
  background: linear-gradient(90deg, #8b5cf6, #ec4899, #8b5cf6);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.app-subtitle {
  color: #9ca3af;
  font-size: 0.875rem;
}

.main-layout {
  display: flex;
  flex: 1;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.sidebar {
  width: 260px;
  background: rgba(26, 26, 46, 0.6);
  border-right: 1px solid rgba(139, 92, 246, 0.2);
  padding: 1.5rem 1rem;
  position: sticky;
  top: 70px;
  height: calc(100vh - 70px);
  overflow-y: auto;
}

.nav-section {
  margin-bottom: 2rem;
}

.nav-section-title {
  color: #9ca3af;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
  padding-left: 0.5rem;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  color: #9ca3af;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.2s ease;
}

.nav-item:hover {
  background: rgba(139, 92, 246, 0.1);
  color: #c7d2fe;
}

.nav-item.active {
  background: linear-gradient(90deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.1));
  color: #a78bfa;
  border-left: 3px solid #8b5cf6;
}

.nav-icon {
  width: 18px;
  height: 18px;
}

.main-content {
  flex: 1;
  padding: 2rem;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .sidebar {
    width: 220px;
  }

  .main-content {
    padding: 1.5rem 1rem;
  }
}
</style>
