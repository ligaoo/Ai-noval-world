from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient


@dataclass
class CharacterGenerationRequest:
    """角色生成请求"""
    world_id: str
    count: int = 3
    genre: str = "horror"
    agent_types: Optional[List[str]] = None  # 可选：指定要生成的角色类型


@dataclass
class CharacterCandidate:
    """角色候选"""
    character_id: str
    name: str
    role: str
    agent_type: str
    traits: List[str]
    goals: Dict[str, str]
    skills: Dict[str, int]
    backstory: str
    emotional_core: Optional[Dict[str, Any]] = None


class LLMCharacterGenerator:
    """
    基于 LLM 的角色生成器
    根据世界观背景随机生成符合设定的角色
    """

    # 角色类型选项
    AGENT_TYPES = [
        "core_agent",      # 核心主角
        "full_npc_agent",  # 完整 NPC
        "semi_agent_npc",  # 半响应 NPC
        "reactive_npc",    # 被动响应 NPC
        "background_npc",  # 背景 NPC
    ]

    # 性格标签库
    TRAIT_POOL = [
        "内向", "外向", "谨慎", "冲动", "理性", "感性",
        "勇敢", "懦弱", "乐观", "悲观", "冷静", "焦虑",
        "细心", "粗心", "善良", "自私", "诚实", "虚伪",
        "坚强", "脆弱", "好奇", "冷漠", "热情", "孤僻",
        "固执", "随和", "聪明", "迟钝", "果断", "犹豫",
    ]

    # 角色定位
    ROLE_POOL = [
        "protagonist", "sidekick", "antagonist", "mentor",
        "love_interest", "victim", "witness", "caretaker",
        "skeptic", "mysterious_stranger", "local_resident",
        "former_employee", "family_member", "friend",
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.client = OpenAICompatibleClient.from_config(project_root)

    def _load_world_context(self, world_id: str) -> Dict[str, Any]:
        """加载世界观上下文"""
        world_dir = self.project_root / "worlds" / world_id

        context = {}

        # 加载 world_bible
        bible_file = world_dir / "world_bible.json"
        if bible_file.exists():
            with open(bible_file, "r", encoding="utf-8") as f:
                context["world_bible"] = json.load(f)

        # 加载现有角色（避免重复）
        characters_file = world_dir / "characters.json"
        if characters_file.exists():
            with open(characters_file, "r", encoding="utf-8") as f:
                context["existing_characters"] = json.load(f).get("characters", [])

        return context

    def _build_prompt(self, request: CharacterGenerationRequest, world_context: Dict[str, Any]) -> tuple[str, str]:
        """构建 LLM 提示词"""
        world_bible = world_context.get("world_bible", {})
        existing = world_context.get("existing_characters", [])

        system_prompt = """你是一个专业的小说角色设计师。
请根据提供的世界观背景，生成符合设定的小说角色。

要求：
1. 角色必须严格符合世界观的时代、题材、地点和氛围
2. 每个角色要有独特的性格和与世界观相关的背景故事
3. 技能值在 0-100 之间，符合角色定位
4. 性格标签 3-5 个
5. 短期目标和长期目标要符合角色设定和世界观
6. 必须返回纯 JSON 格式，不要包含其他文字

返回格式示例：
{
  "candidates": [
    {
      "character_id": "char_zhangwei",
      "name": "张伟",
      "role": "protagonist",
      "agent_type": "core_agent",
      "traits": ["内向", "细心", "勇敢"],
      "goals": {
        "short_term": "找到失踪的亲人",
        "long_term": "揭开这个地方的秘密"
      },
      "skills": {
        "observation": 75,
        "social": 40,
        "courage": 65,
        "logic": 80
      },
      "backstory": "张伟是一名记者，三年前有亲人在事发地失踪...",
      "emotional_core": {
        "guilt_source": "当年没有陪亲人一起去",
        "current_drive": "找到真相，弥补愧疚"
      }
    }
  ]
}"""

        world_title = world_bible.get('world_name', world_bible.get('title', '未知世界'))

        world_desc = f"""世界观名称：{world_title}

世界观背景：
- 题材：{world_bible.get('genre', '悬疑')}
- 时代：{world_bible.get('era', '现代')}
- 基调：{world_bible.get('tone', '压抑')}
- 世界规则：{json.dumps(world_bible.get('rules', []), ensure_ascii=False)}
- 核心主题：{json.dumps(world_bible.get('themes', []), ensure_ascii=False)}

时间线：
{json.dumps(world_bible.get('timeline_explanations', {}), ensure_ascii=False, indent=2)}

重要提示：所有角色的背景故事、目标必须与"{world_title}"这个世界观紧密相关，不要生成与世界观无关的内容（如医院、学校等除非世界观明确包含它们）。"""

        if existing:
            existing_names = [c.get('name', '') for c in existing]
            world_desc += f"\n已存在角色（请勿重复）：{', '.join(existing_names)}"

        agent_types = request.agent_types or self.AGENT_TYPES
        world_desc += f"\n\n请生成 {request.count} 个角色。"
        world_desc += f"\n角色类型可以从以下选择：{', '.join(agent_types)}"

        return system_prompt, world_desc

    def generate(self, request: CharacterGenerationRequest) -> List[CharacterCandidate]:
        """
        生成角色
        优先使用 LLM，如果 LLM 不可用则使用回退机制生成
        """
        world_context = self._load_world_context(request.world_id)

        # 尝试使用 LLM
        if self.client:
            try:
                return self._generate_with_llm(request, world_context)
            except Exception as e:
                print(f"LLM 生成失败，使用回退机制: {e}")

        # 回退：使用规则生成
        return self._generate_fallback(request, world_context)

    def _generate_with_llm(
        self,
        request: CharacterGenerationRequest,
        world_context: Dict[str, Any]
    ) -> List[CharacterCandidate]:
        """使用 LLM 生成角色"""
        system_prompt, user_prompt = self._build_prompt(request, world_context)

        response = self.client.chat_json(
            system=system_prompt,
            user=user_prompt,
            temperature=0.8,  # 较高温度增加随机性
            use_cache=False,
        )

        if not response.parsed_json:
            raise ValueError("LLM 返回的 JSON 解析失败")

        candidates_data = response.parsed_json.get("candidates", [])

        candidates = []
        for data in candidates_data:
            candidate = CharacterCandidate(
                character_id=data.get("character_id", ""),
                name=data.get("name", ""),
                role=data.get("role", ""),
                agent_type=data.get("agent_type", "full_npc_agent"),
                traits=data.get("traits", []),
                goals=data.get("goals", {"short_term": "", "long_term": ""}),
                skills=data.get("skills", {"observation": 50, "social": 50, "courage": 50, "logic": 50}),
                backstory=data.get("backstory", ""),
                emotional_core=data.get("emotional_core"),
            )
            candidates.append(candidate)

        return candidates

    def _generate_fallback(
        self,
        request: CharacterGenerationRequest,
        world_context: Dict[str, Any]
    ) -> List[CharacterCandidate]:
        """
        回退机制：使用规则生成角色
        当 LLM 不可用时使用
        """
        world_bible = world_context.get("world_bible", {})
        genre = world_bible.get("genre", "悬疑")
        world_name = world_bible.get("world_name", world_bible.get("title", "未知世界"))
        era = world_bible.get("era", "现代")

        # 从世界观中提取关键地点/事件（用于生成背景）
        themes = world_bible.get("themes", [])
        rules = world_bible.get("rules", [])
        world_keywords = self._extract_world_keywords(world_bible)

        candidates = []
        existing_ids = set(c.get("character_id", "") for c in world_context.get("existing_characters", []))

        for i in range(request.count):
            # 随机选择角色类型
            agent_type = random.choice(request.agent_types or self.AGENT_TYPES)

            # 随机生成名字（中文常见姓氏+名字）
            surnames = ["张", "李", "王", "刘", "陈", "杨", "赵", "周", "吴", "郑",
                       "孙", "马", "朱", "胡", "郭", "林", "何", "高", "罗", "梁"]
            given_names = ["伟", "芳", "娜", "敏", "静", "强", "磊", "军", "洋", "勇",
                          "杰", "娟", "涛", "明", "超", "秀兰", "平", "刚", "桂英"]

            name = random.choice(surnames) + random.choice(given_names)

            # 生成唯一ID
            char_id = f"char_{name.lower()}_{random.randint(100, 999)}"
            while char_id in existing_ids:
                char_id = f"char_{name.lower()}_{random.randint(100, 999)}"
            existing_ids.add(char_id)

            # 随机性格
            traits = random.sample(self.TRAIT_POOL, random.randint(3, 5))

            # 随机角色定位
            role = random.choice(self.ROLE_POOL)

            # 随机技能（根据角色类型调整）
            if agent_type == "core_agent":
                # 主角技能较高
                skills = {
                    "observation": random.randint(60, 90),
                    "social": random.randint(40, 80),
                    "courage": random.randint(50, 90),
                    "logic": random.randint(60, 90),
                }
            else:
                skills = {
                    "observation": random.randint(30, 70),
                    "social": random.randint(30, 70),
                    "courage": random.randint(20, 70),
                    "logic": random.randint(30, 70),
                }

            # 根据世界观信息动态生成背景和目标
            short_goals, long_goals, backstories = self._generate_world_based_content(
                name, world_name, genre, themes, rules, world_keywords
            )

            candidate = CharacterCandidate(
                character_id=char_id,
                name=name,
                role=role,
                agent_type=agent_type,
                traits=traits,
                goals={
                    "short_term": random.choice(short_goals),
                    "long_term": random.choice(long_goals),
                },
                skills=skills,
                backstory=random.choice(backstories),
                emotional_core={
                    "guilt_source": "过去的某个选择",
                    "current_drive": "弥补愧疚，找到真相",
                },
            )
            candidates.append(candidate)

        return candidates

    def _extract_world_keywords(self, world_bible: Dict[str, Any]) -> List[str]:
        """从世界观中提取关键关键词"""
        keywords = []

        # 尝试从标题/名称中提取
        world_name = world_bible.get("world_name", world_bible.get("title", ""))
        if "医院" in world_name:
            keywords.append("医院")
        elif "学校" in world_name:
            keywords.append("学校")
        elif "公寓" in world_name or "楼" in world_name:
            keywords.append("公寓")
        elif "村" in world_name:
            keywords.append("村庄")
        elif "岛" in world_name:
            keywords.append("岛屿")

        # 从规则和主题中提取
        for rule in world_bible.get("rules", []):
            for word in ["医院", "学校", "公寓", "村庄", "森林", "古宅", "实验室", "工厂"]:
                if word in rule and word not in keywords:
                    keywords.append(word)

        return keywords if keywords else ["神秘地点"]

    def _generate_world_based_content(
        self, name: str, world_name: str, genre: str,
        themes: List[str], rules: List[str], keywords: List[str]
    ) -> tuple:
        """根据世界观信息生成角色背景和目标"""
        location = keywords[0] if keywords else "这个地方"

        # 通用基础模板（不绑定特定地点）
        base_short_goals = [
            "找到失踪的亲人",
            "调查事件的真相",
            "弄清当年发生了什么",
            "解开这里的谜团",
            "保护身边的人",
        ]

        base_long_goals = [
            "揭开所有秘密的真相",
            "结束这一切的源头",
            "弥补当年犯下的错误",
            "找到事件的最终答案",
        ]

        base_backstories = [
            f"{name}曾经与{location}有过一段渊源，多年后因为某个原因回到了这里...",
            f"{name}为了调查某件事来到{location}，却发现事情远没有想象的简单...",
            f"{name}的亲人在这里失踪，为了寻找亲人来到这个充满谜团的地方...",
            f"{name}收到了一封神秘来信，信的内容让{name}不得不来到{location}...",
            f"{name}只是偶然路过{location}，却被卷入了一连串的怪事之中...",
        ]

        # 根据题材调整
        if "灵异" in genre or "恐怖" in genre:
            short_goals = [
                "调查奇怪的声音来源",
                "弄清那些异象的原因",
                "找到离开这里的方法",
            ] + base_short_goals

            long_goals = [
                "解脱被困在这里的灵魂",
                "彻底结束这一切诅咒",
            ] + base_long_goals

            backstories = [
                f"{name}来到{location}后，开始经历各种无法解释的怪事...",
                f"{name}从小就能看到一些别人看不到的东西，这次来到{location}也是如此...",
                f"{name}的家族与{location}有着千丝万缕的联系，这一次{name}必须面对...",
            ] + base_backstories
        else:
            short_goals = base_short_goals
            long_goals = base_long_goals
            backstories = base_backstories

        return short_goals, long_goals, backstories
