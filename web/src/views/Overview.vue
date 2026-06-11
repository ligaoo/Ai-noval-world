﻿﻿﻿﻿﻿<template>
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
          :label="primaryRunButtonLabel"
          icon="pi pi-play"
          severity="info"
          @click="startSimulation"
          :disabled="longRunLoading || isLongRunCompleted"
          :loading="longRunLoading"
        />
      </div>
    </div>
    <div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 12px; padding: 12px 16px; margin-bottom: 20px; color: #d1fae5;">
      当前默认运行链路：正式版V1（`开 move` · `开记忆` · `开 LLM 叙事改写` · `开一致性检查+修订`）
    </div>

    <div style="background: rgba(42, 45, 53, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 16px; margin-bottom: 20px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px;">
      <div>
        <label style="font-size: 13px; color: #9ca3af; display: block; margin-bottom: 6px;">章节风格</label>
        <select v-model="qualityStyleFocus" multiple style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px; min-height: 88px;">
          <option value="悬疑推进">悬疑推进</option>
          <option value="恐怖氛围">恐怖氛围</option>
          <option value="角色冲突">角色冲突</option>
          <option value="线索密集">线索密集</option>
          <option value="慢热铺垫">慢热铺垫</option>
        </select>
      </div>
      <div>
        <label style="font-size: 13px; color: #9ca3af; display: block; margin-bottom: 6px;">生成强度</label>
        <select v-model="generationStrength" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;">
          <option value="保守">保守：更忠实事件</option>
          <option value="平衡">平衡：忠实 + 文学化</option>
          <option value="强化">强化：更重成稿质感</option>
        </select>
      </div>
      <div>
        <label style="font-size: 13px; color: #9ca3af; display: block; margin-bottom: 6px;">结尾类型</label>
        <select v-model="endingHookType" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;">
          <option value="感官钩子">感官钩子</option>
          <option value="线索钩子">线索钩子</option>
          <option value="关系钩子">关系钩子</option>
          <option value="危险钩子">危险钩子</option>
        </select>
      </div>
    </div>

    <!-- 章节管理 -->
    <div style="background: rgba(42, 45, 53, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 20px; margin-bottom: 24px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px;">
        <div>
          <h3 style="font-size: 20px; font-weight: 600; margin-bottom: 6px;">章节管理</h3>
          <div style="font-size: 13px; color: #9ca3af;">
            当前章节：{{ currentChapter }}/{{ targetChapters }}
            <span v-if="longRun">　状态：{{ longRun.status }}　Long Run：<code>{{ longRun.long_run_id }}</code></span>
          </div>
        </div>
        <div style="display: flex; gap: 10px;">
          <button @click="startSimulation" :disabled="longRunLoading || isLongRunCompleted" style="background: #2563eb; color: white; border: none; padding: 9px 16px; border-radius: 9px; cursor: pointer;">
            {{ primaryRunButtonLabel }}
          </button>
          <button @click="refreshLongRun" :disabled="longRunLoading || !longRun" style="background: #374151; color: white; border: none; padding: 9px 16px; border-radius: 9px; cursor: pointer;">
            刷新
          </button>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px;">
        <div>
          <label style="font-size: 12px; color: #9ca3af; display: block; margin-bottom: 6px;">目标章节数</label>
          <input v-model.number="longRunForm.target_chapters" type="number" min="1" :disabled="!!longRun" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;" />
        </div>
        <div>
          <label style="font-size: 12px; color: #9ca3af; display: block; margin-bottom: 6px;">Seed</label>
          <input v-model.number="longRunForm.seed" type="number" :disabled="!!longRun" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;" />
        </div>
        <div>
          <label style="font-size: 12px; color: #9ca3af; display: block; margin-bottom: 6px;">Genre ID</label>
          <input v-model="longRunForm.genre_id" :disabled="!!longRun" style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 8px; border-radius: 8px;" />
        </div>
      </div>

      <div v-if="longRunError" style="color: #f87171; margin-bottom: 10px; white-space: pre-wrap;">{{ longRunError }}</div>

      <div v-if="longRunChapters.length" style="display: grid; grid-template-columns: 260px 1fr; gap: 14px; align-items: start; margin-top: 14px;">
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
              placeholder="例如：my_world_001"
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
              placeholder="输入一条世界规则"
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

        <div style="margin-top: 16px;">
          <label style="font-size: 14px; color: #9ca3af; display: block; margin-bottom: 8px;">剧情线（逗号分隔）</label>
          <input
            v-model="plotArcIdsText"
            @blur="applyPlotArcIdsFromText"
            placeholder="例如：arc_hospital_truth, arc_identity_mystery"
            style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none;"
          />
          <p style="font-size: 12px; color: #6b7280; margin-top: 6px;">用于生成器下拉联动；详细阶段可到“剧情弧”页面编辑。</p>
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

    <!-- 自动补全 -->
    <div style="background: rgba(42, 45, 53, 0.9); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 24px; margin-bottom: 32px;">
      <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px;">
        <div>
          <h3 style="font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 12px;">
            <Zap style="width: 24px; height: 24px; color: #a855f7;" />
            Bootstrap 自动补全
          </h3>
          <p style="color: #9ca3af; font-size: 14px; margin-top: 6px;">保存当前手动草稿，用 Bootstrap 补齐缺失 NPC、隐藏行动者、地图、线索和开场目标。</p>
        </div>
        <button
          @click="completeCurrentWorld"
          :disabled="isCompletingWorld || !selectedWorldId"
          style="background: linear-gradient(135deg, #a855f7, #ec4899); color: white; border: none; padding: 12px 16px; border-radius: 12px; cursor: pointer; font-size: 14px; min-width: 180px;"
        >
          {{ isCompletingWorld ? '补全中...' : '自动补全为正式世界' }}
        </button>
      </div>

      <textarea
        v-model="completionSeed"
        rows="2"
        placeholder="可选：补充你希望保留或强化的方向，例如：NPC 都与失踪案有关，但每个人只知道一部分真相。"
        style="width: 100%; background: #1c1e24; border: 1px solid #374151; color: #f3f4f6; padding: 12px 16px; border-radius: 12px; outline: none; resize: vertical; margin-bottom: 16px;"
      ></textarea>

      <div v-if="completionResult" style="background: rgba(28, 30, 36, 0.7); border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 12px; padding: 16px;">
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px;">
          <div>
            <div style="font-weight: 600; color: #f3f4f6;">补全候选：{{ completionResult.title || completionResult.world_id }}</div>
            <div :style="{ color: completionResult.validation?.passed ? '#10b981' : '#ef4444', fontSize: '14px', marginTop: '4px' }">
              {{ completionResult.validation?.passed ? '校验通过，可确认写入' : '校验未通过，请查看问题' }}
            </div>
          </div>
          <button
            @click="confirmCompletion"
            :disabled="isConfirmingCompletion || !completionResult.validation?.passed"
            style="background: #10b981; color: white; border: none; padding: 10px 14px; border-radius: 10px; cursor: pointer; font-size: 14px;"
          >
            {{ isConfirmingCompletion ? '写入中...' : '确认写入' }}
          </button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; color: #d1d5db; font-size: 13px;">
          <div>
            <div style="color: #10b981; font-weight: 600; margin-bottom: 6px;">保留用户内容</div>
            <div>角色：{{ completionResult.fusion_report?.preserved?.characters?.length || 0 }}</div>
            <div>地点：{{ completionResult.fusion_report?.preserved?.locations?.length || 0 }}</div>
            <div>线索：{{ completionResult.fusion_report?.preserved?.clues?.length || 0 }}</div>
          </div>
          <div>
            <div style="color: #a855f7; font-weight: 600; margin-bottom: 6px;">自动新增</div>
            <div>角色/NPC：{{ completionResult.fusion_report?.generated?.characters?.length || 0 }}</div>
            <div>地点：{{ completionResult.fusion_report?.generated?.locations?.length || 0 }}</div>
            <div>线索：{{ completionResult.fusion_report?.generated?.clues?.length || 0 }}</div>
          </div>
          <div>
            <div style="color: #f59e0b; font-weight: 600; margin-bottom: 6px;">自动修复</div>
            <div>{{ completionResult.fusion_report?.repaired?.length || 0 }} 项引用/路线修复</div>
          </div>
        </div>

        <div v-if="completionResult.validation?.issues?.length" style="margin-top: 12px; color: #fca5a5; font-size: 13px;">
          <div v-for="issue in completionResult.validation.issues" :key="issue.message || issue" style="margin-top: 4px;">- {{ issue.message || issue }}</div>
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

const API = ''

const router = useRouter()
const worldStore = useWorldStore()

// 世界列表相关
const availableWorlds = ref([])
const selectedWorldId = ref('')
const showCreateDialog = ref(false)
const isCreatingWorld = ref(false)
const isCompletingWorld = ref(false)
const isConfirmingCompletion = ref(false)
const completionResult = ref(null)
const completionSeed = ref('')

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
    const response = await fetch(`${API}/api/worlds`)
    const data = await response.json()
    availableWorlds.value = data.worlds || []
  } catch (error) {
    console.error('加载世界列表失败:', error)
  }
}

const formatApiError = (payload, fallback) => {
  const detail = payload?.detail ?? payload?.message ?? payload
  if (!detail) return fallback
  if (typeof detail === 'string') return detail

  const parts = []
  if (detail.message) parts.push(detail.message)
  if (Array.isArray(detail.issues) && detail.issues.length > 0) {
    parts.push(`问题：\n${detail.issues.map(issue => `- ${issue}`).join('\n')}`)
  }
  if (Array.isArray(detail.warnings) && detail.warnings.length > 0) {
    parts.push(`警告：\n${detail.warnings.map(warning => `- ${warning}`).join('\n')}`)
  }

  return parts.length > 0 ? parts.join('\n\n') : JSON.stringify(detail)
}

const resetLongRunState = () => {
  longRunError.value = ''
  longRun.value = null
  longRunChapters.value = []
  selectedChapterDetail.value = null
  longRunMemory.value = []
}

// 加载选中的世界
const loadSelectedWorld = async (silent = false) => {
  if (!selectedWorldId.value) return

  try {
    await worldStore.loadWorld(selectedWorldId.value)
    completionResult.value = null
    resetLongRunState()

    if (!silent) alert(`✅ 已加载世界: ${worldStore.worldBible?.title || selectedWorldId.value}`)
  } catch (error) {
    console.error('加载世界失败:', error)
    if (!silent) alert(`❌ 加载世界失败: ${error.message}`)
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
    const response = await fetch(`${API}/api/worlds/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(newWorldForm.value)
    })

    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new Error(formatApiError(error, '创建失败'))
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
const worldBible = computed({
  get() {
    return worldStore.worldBible || { world_id: '', title: '', genre: '', tone: '', era: '', rules: [], themes: [] }
  },
  set(value) {
    worldStore.worldBible = value
  }
})

const plotArcIdsText = computed({
  get() {
    const arcs = Array.isArray(worldStore.plotArcs) ? worldStore.plotArcs : []
    return arcs.map(arc => arc?.arc_id).filter(Boolean).join(', ')
  },
  set() {}
})

const applyPlotArcIdsFromText = (event) => {
  const raw = (event?.target?.value || '').trim()
  if (!raw) {
    worldStore.plotArcs = []
    return
  }

  const ids = [...new Set(raw.split(',').map(s => s.trim()).filter(Boolean))]
  const existingMap = new Map((worldStore.plotArcs || []).map(arc => [arc.arc_id, arc]))
  worldStore.plotArcs = ids.map(id => existingMap.get(id) || {
    arc_id: id,
    name: id,
    status: 'active',
    progress: 0,
    current_stage: '',
    stages: [],
  })
}

// 初始化加载
onMounted(async () => {
  await loadWorldsList()

  // 同步 localStorage 中的 world_id 与下拉框选中状态
  const storedWorldId = worldStore.worldBible?.world_id
  if (storedWorldId) {
    // 如果 localStorage 中有世界数据，检查是否在可用列表中
    const worldExists = availableWorlds.value.some(w => w.id === storedWorldId)
    if (worldExists) {
      // 如果存在，选中并加载该世界
      selectedWorldId.value = storedWorldId
      await loadSelectedWorld(true)
    } else if (availableWorlds.value.length > 0) {
      // 如果不存在（数据被删除），选中第一个可用世界并加载
      selectedWorldId.value = availableWorlds.value[0].id
      await loadSelectedWorld(true)
    }
  } else if (availableWorlds.value.length > 0) {
    // 如果没有存储数据，选中第一个可用世界并加载
    selectedWorldId.value = availableWorlds.value[0].id
    await loadSelectedWorld(true)
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
const qualityStyleFocus = ref(['悬疑推进', '恐怖氛围'])
const generationStrength = ref('平衡')
const endingHookType = ref('线索钩子')

const currentChapter = computed(() => longRun.value?.current_chapter || 0)
const targetChapters = computed(() => longRun.value?.target_chapters || longRunForm.value.target_chapters)
const hasLongRun = computed(() => !!longRun.value?.long_run_id)
const isLongRunCompleted = computed(() => longRun.value?.status === 'completed')
const primaryRunButtonLabel = computed(() => {
  if (longRunLoading.value) return '生成中...'
  if (!hasLongRun.value) return '创建长篇运行'
  if (isLongRunCompleted.value) return '已完成'
  return `生成第 ${currentChapter.value + 1} 章`
})

const saveCurrentWorldDraft = async () => {
  const currentWorldId = selectedWorldId.value || worldBible.value.world_id
  if (!currentWorldId) throw new Error('请先选择一个世界')

  const response = await fetch(`${API}/api/worlds/${currentWorldId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      world_bible: worldStore.worldBible,
      characters: worldStore.characters,
      map: worldStore.locations,
      clues: worldStore.clues,
      plot_arcs: worldStore.plotArcs,
      character_arcs: worldStore.characterArcs,
      chapter_goal: {},
    })
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(formatApiError(error, '保存草稿失败'))
  }

  return currentWorldId
}

const completeCurrentWorld = async () => {
  if (isCompletingWorld.value) return
  isCompletingWorld.value = true
  completionResult.value = null

  try {
    const currentWorldId = await saveCurrentWorldDraft()
    const response = await fetch(`${API}/api/worlds/${currentWorldId}/complete`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_seed: completionSeed.value || null,
        target_genre: worldBible.value.genre || 'horror_suspense',
        target_words: 100000,
        auto_confirm: false,
      })
    })

    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new Error(formatApiError(error, '自动补全失败'))
    }

    completionResult.value = await response.json()
  } catch (error) {
    console.error('自动补全失败:', error)
    alert(`❌ 自动补全失败\n\n${error.message}`)
  } finally {
    isCompletingWorld.value = false
  }
}

const confirmCompletion = async () => {
  if (!completionResult.value?.bootstrap_id || isConfirmingCompletion.value) return
  isConfirmingCompletion.value = true

  try {
    const response = await fetch(`${API}/api/story/bootstrap/${completionResult.value.bootstrap_id}/confirm`, {
      method: 'POST'
    })

    if (!response.ok) {
      const error = await response.json().catch(() => null)
      throw new Error(formatApiError(error, '确认写入失败'))
    }

    await loadWorldsList()
    selectedWorldId.value = completionResult.value.world_id
    await loadSelectedWorld()
    completionResult.value = null
    alert('✅ 世界已补全并写入，现在可以正式运行模拟')
  } catch (error) {
    console.error('确认补全失败:', error)
    alert(`❌ 确认写入失败\n\n${error.message}`)
  } finally {
    isConfirmingCompletion.value = false
  }
}

const getRunnableWorldId = () => {
  const currentWorldId = selectedWorldId.value || worldBible.value.world_id
  if (!currentWorldId) throw new Error('请先选择一个世界')

  const selectedWorld = availableWorlds.value.find(world => world.id === currentWorldId)
  if (selectedWorld && selectedWorld.formal_run_ready === false) {
    const issues = selectedWorld.formal_run_issues || []
    throw new Error(`当前世界尚未满足正式运行条件，请先点击“自动补全为正式世界”。${issues.length > 0 ? `\n\n问题：\n${issues.map(issue => `- ${issue}`).join('\n')}` : ''}`)
  }

  return currentWorldId
}

const refreshLongRun = async () => {
  if (!longRun.value?.long_run_id) return
  longRunLoading.value = true
  longRunError.value = ''
  try {
    const response = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}`)
    const data = await response.json()
    if (!response.ok) throw new Error(formatApiError(data, '刷新长篇运行失败'))
    longRun.value = data
    longRunChapters.value = data.chapters || []
  } catch (error) {
    longRunError.value = error.message || '刷新长篇运行失败'
  } finally {
    longRunLoading.value = false
  }
}

const loadLongRunMemory = async () => {
  if (!longRun.value?.long_run_id) return
  const response = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}/memory`)
  const data = await response.json()
  if (!response.ok) throw new Error(formatApiError(data, '读取记忆失败'))
  longRunMemory.value = data.memories || []
}

const selectLongRunChapter = async (chapterNo) => {
  if (!longRun.value?.long_run_id) return
  longRunError.value = ''
  try {
    const response = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}/chapters/${chapterNo}`)
    const data = await response.json()
    if (!response.ok) throw new Error(formatApiError(data, '读取章节失败'))
    selectedChapterDetail.value = data
    await loadLongRunMemory()
  } catch (error) {
    longRunError.value = error.message || '读取章节失败'
  }
}

const createLongRun = async () => {
  if (longRunLoading.value) return
  longRunLoading.value = true
  longRunError.value = ''

  try {
    const currentWorldId = getRunnableWorldId()
    const response = await fetch(`${API}/api/novel-runs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        world_id: currentWorldId,
        mode: 'llm',
        version: '正式版V1',
        seed: longRunForm.value.seed,
        genre_id: longRunForm.value.genre_id,
        target_chapters: longRunForm.value.target_chapters,
        quality_controls: {
          style_focus: qualityStyleFocus.value,
          generation_strength: generationStrength.value,
          ending_hook_type: endingHookType.value,
          rewrite_policy: 'auto_once',
        },
      }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(formatApiError(data, '创建长篇运行失败'))

    longRun.value = data.run
    longRunChapters.value = data.run.chapters || []
    selectedChapterDetail.value = null
    longRunMemory.value = []
  } catch (error) {
    longRunError.value = error.message || '创建长篇运行失败'
  } finally {
    longRunLoading.value = false
  }
}

const generateNextLongRunChapter = async () => {
  if (!longRun.value?.long_run_id || longRunLoading.value || isLongRunCompleted.value) return
  longRunLoading.value = true
  longRunError.value = ''

  try {
    const response = await fetch(`${API}/api/novel-runs/${longRun.value.long_run_id}/chapters/next`, { method: 'POST' })
    const data = await response.json()
    if (!response.ok) throw new Error(formatApiError(data, '生成下一章失败'))

    longRun.value = data.run
    longRunChapters.value = data.run.chapters || []
    await selectLongRunChapter(data.chapter.chapter_no)
  } catch (error) {
    const message = error.message || '生成下一章失败'
    longRunError.value = message
    await refreshLongRun().catch(() => {})
    longRunError.value = message
  } finally {
    longRunLoading.value = false
  }
}

const startSimulation = async () => {
  if (longRunLoading.value || isLongRunCompleted.value) return
  if (!hasLongRun.value) {
    await createLongRun()
    return
  }
  await generateNextLongRunChapter()
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
