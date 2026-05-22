import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/Overview.vue'),
    meta: { title: '总览' }
  },
  {
    path: '/characters',
    name: 'characters',
    component: () => import('../views/Characters.vue'),
    meta: { title: '角色管理' }
  },
  {
    path: '/clues',
    name: 'clues',
    component: () => import('../views/Clues.vue'),
    meta: { title: '线索管理' }
  },
  {
    path: '/map',
    name: 'map',
    component: () => import('../views/MapEditor.vue'),
    meta: { title: '地图编辑' }
  },
  {
    path: '/plot-arc',
    name: 'plot-arc',
    component: () => import('../views/PlotArc.vue'),
    meta: { title: '剧情弧' }
  },
  {
    path: '/character-arc',
    name: 'character-arc',
    component: () => import('../views/CharacterArc.vue'),
    meta: { title: '角色弧' }
  },
  {
    path: '/generator/character',
    name: 'character-generator',
    component: () => import('../views/CharacterGenerator.vue'),
    meta: { title: '角色生成器' }
  },
  {
    path: '/generator/npc',
    name: 'npc-generator',
    component: () => import('../views/NPCGenerator.vue'),
    meta: { title: 'NPC生成器' }
  },
  {
    path: '/generator/clue',
    name: 'clue-generator',
    component: () => import('../views/ClueGenerator.vue'),
    meta: { title: '线索生成器' }
  },
  {
    path: '/generator/review',
    name: 'candidate-review',
    component: () => import('../views/CandidateReviewPanel.vue'),
    meta: { title: '候选审核面板' }
  },
  {
    path: '/bootstrap',
    name: 'bootstrap',
    component: () => import('../views/BootstrapPreview.vue'),
    meta: { title: 'Story Bootstrap' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = `${to.meta.title || '小说沙盘'} - V4.2`
  next()
})

export default router
