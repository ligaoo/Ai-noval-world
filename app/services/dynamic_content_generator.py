from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.models.event import PlotValue
from app.models.world import Clue, DiscoverRoute, WorldConfig


@dataclass
class GeneratedClue:
    """生成的线索"""
    clue_id: str
    description: str
    location: str
    discover_method: str  # inspect, ask, search
    content: str
    plot_value: PlotValue
    related_threads: List[str] = field(default_factory=list)


@dataclass
class GeneratedDiscovery:
    """生成的发现内容"""
    content: str
    plot_value: PlotValue
    new_thread_hint: Optional[str] = None
    new_suspect_hint: Optional[str] = None
    requires_followup: bool = False


class DynamicContentGenerator:
    """
    V5.0 动态内容生成器
    核心能力：
    1. 当用户没有提供完整线索时，自动生成合理的线索
    2. 当角色检查无预设内容的对象时，动态生成有意义的发现
    3. 生成符合当前故事氛围和类型的内容
    """

    def __init__(self, world_config: WorldConfig, llm_client=None):
        self.world = world_config
        self.llm_client = llm_client
        self.genre = world_config.bible.genre or "悬疑"
        self.tone = world_config.bible.tone or "压抑"
        self.generated_clues: Dict[str, GeneratedClue] = {}
        self.generated_discoveries: Dict[str, GeneratedDiscovery] = {}

        # 按地点类型对应的发现模板
        self.location_discovery_templates = self._build_location_templates()
        self.object_discovery_templates = self._build_object_templates()
        self.conversation_templates = self._build_conversation_templates()

    def _build_location_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """构建地点发现模板"""
        return {
            "boundary": [
                {"pattern": "gate", "content": "边界处留下了近期变化的痕迹，和表面状态并不一致。", "progress": 2, "mystery": 3},
                {"pattern": "entrance", "content": "入口附近有一处细节被反复触碰过，像是在提示某种进入或离开的条件。", "progress": 2, "mystery": 3},
            ],
            "record": [
                {"pattern": "archive", "content": "记录的排列出现缺口，像是有人刻意改变过信息顺序。", "progress": 3, "mystery": 4},
                {"pattern": "record", "content": "留存信息之间互相矛盾，需要更多证据才能确认哪一部分可信。", "progress": 2, "mystery": 3},
            ],
            "trace": [
                {"pattern": "trace", "content": "这里有一组不属于当前可见角色的行动痕迹，方向避开了最直接的路径。", "progress": 2, "mystery": 3},
                {"pattern": "inner", "content": "空间深处的反馈更强，说明异常并不是随机出现的。", "progress": 2, "mystery": 4},
            ],
            "通用": [
                {"pattern": "", "content": "这里出现了新的可检查细节，说明环境状态刚刚发生过变化。", "progress": 2, "mystery": 2},
                {"pattern": "", "content": "某个细节和角色已有认知不一致，值得进一步验证。", "progress": 2, "mystery": 3},
            ],
        }

    def _build_object_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """构建物品发现模板"""
        return {
            "boundary": [
                "边界痕迹比周围环境更新，说明近期有人或某种力量改变过这里。",
                "这个位置的状态和它应有的状态不一致，像是被反复验证过。",
            ],
            "record": [
                "记录内容存在缺口，缺失部分正好避开了关键因果。",
                "信息被重新排列过，表面顺序无法解释实际发生的事。",
            ],
            "trace": [
                "痕迹指向更深处，但留下痕迹的人显然刻意避开了直接接触。",
                "残留细节显示这里近期发生过一次未被记录的行动。",
            ],
            "通用": [
                "它的位置被轻微移动过，变化幅度不大，却足以说明有人介入。",
                "表面留下了近期接触痕迹，和周围长期静止的状态不一致。",
                "细节之间存在轻微矛盾，需要和其他线索互相印证。",
            ],
        }

    def _build_conversation_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """构建对话发现模板"""
        return {
            "紧张": [
                "对方说话时眼神有些躲闪，好像在隐瞒什么。",
                "他/她的手在微微发抖，声音也有些不自然。",
            ],
            "回避": [
                "对方转移了话题，好像不想谈论这个。",
                "他/她笑了笑，但笑容有些僵硬。",
            ],
            "犹豫": [
                "对方停顿了很久才回答，像是在组织语言。",
                "他/她说话有些支支吾吾，前后有些矛盾。",
            ],
        }

    def generate_discovery_for_inspect(
        self,
        location_id: str,
        target: str,
        current_chapter: int,
        current_progress: int,
    ) -> GeneratedDiscovery:
        """
        为 inspect 动作生成发现内容
        当角色检查一个没有预设线索的对象时调用
        """
        cache_key = f"{location_id}:{target}:{current_chapter}"
        if cache_key in self.generated_discoveries:
            return self.generated_discoveries[cache_key]

        # 1. 尝试匹配对象类型
        content = ""
        base_progress = 2
        base_mystery = 2

        for obj_type, templates in self.object_discovery_templates.items():
            if obj_type in target.lower():
                content = random.choice(templates)
                break

        # 2. 如果没有匹配，尝试匹配地点类型
        if not content:
            for loc_type, templates in self.location_discovery_templates.items():
                if loc_type in location_id.lower() or any(t["pattern"] in target for t in templates):
                    for t in templates:
                        if t["pattern"] in target.lower() or t["pattern"] in location_id.lower():
                            content = t["content"]
                            base_progress = t["progress"]
                            base_mystery = t["mystery"]
                            break
                if content:
                    break

        # 3. 还是没有，用通用模板
        if not content:
            content = random.choice(self.object_discovery_templates["通用"])

        # 根据剧情进度调整内容的重要性
        progress_multiplier = min(1.5, current_progress / 50 + 0.5)
        adjusted_progress = int(base_progress * progress_multiplier)
        adjusted_mystery = int(base_mystery * progress_multiplier)

        # 5. 随机决定是否开启新线索链
        new_thread_hint = None
        if random.random() < 0.3 and current_progress > 30:
            threads = ["隐藏行动者的真实目的", "异常规则的运行条件", "角色选择造成的后果"]
            new_thread_hint = random.choice(threads)

        discovery = GeneratedDiscovery(
            content=content,
            plot_value=PlotValue(
                progress=adjusted_progress,
                mystery=adjusted_mystery,
                conflict=0,
                danger=1 if self.genre == "恐怖" else 0,
                relationship=0,
                novelty=2,
                emotion=1,
            ),
            new_thread_hint=new_thread_hint,
            requires_followup=random.random() < 0.4,
        )

        self.generated_discoveries[cache_key] = discovery
        return discovery

    def generate_discovery_for_ask(
        self,
        speaker_id: str,
        listener_id: str,
        topic: str,
        current_chapter: int,
    ) -> Tuple[str, PlotValue]:
        """
        为 ask 动作生成回答内容
        当没有预设对话时调用
        """
        # 检查是否已经生成过
        cache_key = f"{speaker_id}:{listener_id}:{topic}"

        # 根据话题类型生成回答
        if "锁" in topic or "钥匙" in topic:
            responses = [
                "那个锁啊...我也不太清楚，好像一直就在那里了。",
                "我没怎么注意，不过最近好像有人动过。",
                "这个嘛...我不方便多说，你自己去看看吧。",
            ]
        elif "时间" in topic or "那天" in topic:
            responses = [
                "那天我记得不太清楚了，好像和平常一样。",
                "时间太久了，我也记不太准。",
                "你问这个做什么？这和案子有什么关系？",
            ]
        else:
            responses = [
                "这个我也不太清楚，你还是问问别人吧。",
                "我没怎么注意，不过好像有点不对劲。",
                "你说的这个...我真的不知道。",
                "这个话题我不太方便多说。",
            ]

        content = random.choice(responses)

        # 根据角色性格调整紧张程度
        plot_value = PlotValue(
            progress=1,
            mystery=2,
            conflict=1,
            danger=0,
            relationship=1,
            novelty=1,
            emotion=1,
        )

        return content, plot_value

    def generate_clue_for_location(
        self,
        location_id: str,
        chapter_no: int,
        clue_type: str = "physical",
    ) -> GeneratedClue:
        """
        为某个地点动态生成一个线索
        当该地点缺少线索时调用
        """
        clue_id = f"gen_clue_{location_id}_{chapter_no}_{len(self.generated_clues)}"

        clue_templates = [
            "一处边界状态变化",
            "一组近期行动痕迹",
            "一段缺失或错位的记录",
            "一个被移动过的可检查物",
            "一条与已有认知矛盾的细节",
            "一个指向后续区域的环境标记",
        ]

        description = random.choice(clue_templates)
        location_name = self._location_name(location_id)
        full_content = f"{location_name}中出现{description}，需要通过后续行动与其他证据互相验证。"

        generated = GeneratedClue(
            clue_id=clue_id,
            description=description,
            location=location_id,
            discover_method=random.choice(["inspect", "search"]),
            content=full_content,
            plot_value=PlotValue(
                progress=3,
                mystery=4,
                conflict=1,
                danger=1,
                relationship=0,
                novelty=3,
                emotion=2,
            ),
        )

        self.generated_clues[clue_id] = generated
        return generated

    def _location_name(self, location_id: str) -> str:
        try:
            return self.world.map.get_location(location_id).name
        except Exception:
            return location_id

    def generate_environment_description(
        self,
        location_id: str,
        time_of_day: str = "夜晚",
        mood: str = "紧张",
    ) -> str:
        """
        生成环境氛围描述
        丰富场景细节
        """
        weather_choices = [
            "{}的月光透过窗户洒进来，在墙上投下奇怪的影子。",
            "空气里弥漫着一股{}的气味。",
            "远处传来一阵{}的声音。",
            "{}的风声在走廊里回荡。",
        ]

        mood_adjectives = {
            "紧张": ["苍白", "冷冽", "沙沙", "凄厉"],
            "压抑": ["惨淡", "潮湿", "沉闷", "低沉"],
            "诡异": ["惨淡", "腐烂", "轻微", "呜咽"],
        }

        template = random.choice(weather_choices)
        adj = random.choice(mood_adjectives.get(mood, mood_adjectives["压抑"]))

        return template.format(adj)

    def generate_character_action_idea(
        self,
        character_id: str,
        current_location: str,
        known_facts: List[str],
    ) -> Dict[str, Any]:
        """
        为角色生成一个主动行动想法
        让角色有自己的主动性
        """
        action_templates = [
            {
                "type": "inspect",
                "intent": "仔细检查周围环境，看看有没有漏掉的线索",
                "target": "某个可疑的地方",
                "reasoning": "直觉告诉我这里有问题",
            },
            {
                "type": "search",
                "intent": "翻找一下，说不定能发现什么",
                "target": "某个角落",
                "reasoning": "线索可能藏在某个地方",
            },
            {
                "type": "ask",
                "intent": "再问问，说不定能想起什么",
                "target": "某个角色",
                "reasoning": "对方好像隐瞒了什么",
            },
            {
                "type": "move",
                "intent": "去别的地方看看",
                "target": "另一个地点",
                "reasoning": "这里没什么可看的了",
            },
        ]

        chosen = random.choice(action_templates)

        # 根据已知事实调整意图
        if known_facts:
            latest_fact = known_facts[-1]
            if "锁" in latest_fact:
                chosen["intent"] = "再仔细检查那个锁"
            elif "人" in latest_fact:
                chosen["intent"] = "问问关于这个人的情况"

        return chosen

    def get_generated_clue(self, clue_id: str) -> Optional[GeneratedClue]:
        """获取已生成的线索"""
        return self.generated_clues.get(clue_id)

    def save_generated_content(self, output_dir: Path) -> None:
        """保存生成的内容记录"""
        record = {
            "generated_clues": [
                    {
                        "clue_id": c.clue_id,
                        "description": c.description,
                        "location": c.location,
                        "content": c.content,
                    }
                for c in self.generated_clues.values()
            ],
            "generated_discoveries_count": len(self.generated_discoveries),
        }

        with open(output_dir / "dynamic_content_record.json", "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
