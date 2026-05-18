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
            "医院": [
                {"pattern": "值班室", "content": "桌上放着一本翻旧的值班记录，最后几页的字迹格外潦草。", "progress": 2, "mystery": 3},
                {"pattern": "走廊", "content": "走廊尽头的灯光在微微摇晃，投下奇怪的影子。", "progress": 1, "mystery": 2},
                {"pattern": "病房", "content": "床头柜上有一只半满的水杯，杯壁还残留着水渍。", "progress": 2, "mystery": 2},
                {"pattern": "档案室", "content": "某个抽屉没有完全关上，里面露出来的文件日期有些异常。", "progress": 3, "mystery": 4},
            ],
            "旧楼": [
                {"pattern": "楼梯", "content": "楼梯扶手上有一道新鲜的划痕。", "progress": 2, "mystery": 2},
                {"pattern": "阁楼", "content": "阁楼的地板上有一层薄尘，但某个角落的灰尘被扫开过。", "progress": 3, "mystery": 3},
                {"pattern": "地下室", "content": "空气里弥漫着一股淡淡的消毒水味。", "progress": 1, "mystery": 4},
            ],
            "办公室": [
                {"pattern": "办公桌", "content": "抽屉里有一张撕碎的纸条，拼起来看像是某种收据。", "progress": 2, "mystery": 3},
                {"pattern": "文件柜", "content": "文件的排列有些异常，好像被人重新整理过。", "progress": 2, "mystery": 2},
            ],
            "通用": [
                {"pattern": "门", "content": "门锁上有新鲜的划痕，像是最近被人撬过。", "progress": 2, "mystery": 3},
                {"pattern": "窗户", "content": "窗户边缘有一些泥土，不是这里的土。", "progress": 2, "mystery": 3},
                {"pattern": "地板", "content": "地板上有几个不完整的脚印，朝向某个方向。", "progress": 2, "mystery": 2},
            ],
        }

    def _build_object_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """构建物品发现模板"""
        return {
            "锁": [
                "锁芯异常干净，说明最近经常被人使用。",
                "锁的样式很特别，不是这里常见的类型。",
                "锁上面有几道新鲜的划痕，像是钥匙插入的痕迹。",
            ],
            "抽屉": [
                "抽屉最里面藏着一个信封，没有邮票也没有地址。",
                "抽屉里的东西被人翻过，但少了几样。",
                "抽屉底部贴着一张小纸条，写着一串数字。",
            ],
            "文件": [
                "文件里夹着一张照片，背面写着一个名字。",
                "某一页的边缘有被水浸过的痕迹。",
                "最后几页被人撕掉了，只剩下一些碎纸。",
            ],
            "照片": [
                "照片里的某个人被用红笔圈了出来。",
                "照片背面写着一个日期，是最近的。",
                "照片边缘有折痕，像是经常被拿出来看。",
            ],
            "杯子": [
                "杯口有口红印，但不是这里任何人的。",
                "杯子里还有半杯水，还没完全冷透。",
                "杯子底部有一个奇怪的标记。",
            ],
            "通用": [
                "上面有几枚新鲜的指纹。",
                "东西摆放的位置有些奇怪，像是被人移动过。",
                "凑近闻能闻到一股淡淡的奇怪气味。",
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
            threads = ["神秘人物的真实身份", "十年前的往事", "隐藏的秘密关系"]
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

        # 根据类型决定线索内容
        clue_templates = [
            "一张泛黄的照片",
            "一本破旧的日记",
            "一张撕碎的纸条",
            "一把奇怪的钥匙",
            "一个空的药瓶",
            "一张收据",
            "一张地图",
            "一个录音笔",
        ]

        description = random.choice(clue_templates)

        # 根据地点类型生成内容
        location_specific = ""
        if "医院" in location_id or "hospital" in location_id.lower():
            location_specific = random.choice([
                "病历记录有些奇怪，有一页被撕掉了。",
                "药品清单上少了几样东西。",
                "值班记录的字迹有些异常。",
            ])
        elif "办公室" in location_id:
            location_specific = random.choice([
                "文件里夹着一张奇怪的便签。",
                "抽屉最里面有一个奇怪的标记。",
                "日历上某个日期被圈了出来。",
            ])

        full_content = f"{description}——{location_specific}" if location_specific else description

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
