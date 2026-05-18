from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorldBible(BaseModel):
    world_id: str
    genre: str = ""
    tone: str = ""
    era: str = ""
    rules: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)


class WorldObject(BaseModel):
    id: str
    name: str
    visible: bool = True
    state: str = ""
    description: str = ""


class Location(BaseModel):
    id: str
    name: str
    public_description: str
    objects: List[WorldObject] = Field(default_factory=list)
    connected_to: List[str] = Field(default_factory=list)
    danger_level: int = 0
    time_effects: Dict[str, Any] = Field(default_factory=dict)


class MapConfig(BaseModel):
    locations: List[Location]

    def get_location(self, location_id: str) -> Location:
        for loc in self.locations:
            if loc.id == location_id:
                return loc
        raise KeyError(f"location_id not found: {location_id}")

    def all_object_ids(self) -> List[str]:
        ids: List[str] = []
        for loc in self.locations:
            ids.extend([o.id for o in loc.objects])
        return ids

    def all_object_names(self) -> List[str]:
        names: List[str] = []
        for loc in self.locations:
            names.extend([o.name for o in loc.objects])
        return names


class CharacterProfile(BaseModel):
    id: str
    name: str
    role: str = ""
    personality: Dict[str, Any] = Field(default_factory=dict)
    goals: Dict[str, Any] = Field(default_factory=dict)
    fears: List[str] = Field(default_factory=list)
    secrets: List[str] = Field(default_factory=list)
    skills: Dict[str, int] = Field(default_factory=dict)
    # V5.1 新增：角色专属 LLM temperature（可选，未设置时用默认）
    llm_temperature: Optional[float] = None


class CharactersConfig(BaseModel):
    characters: List[CharacterProfile]

    def get_character(self, character_id: str) -> CharacterProfile:
        for c in self.characters:
            if c.id == character_id:
                return c
        raise KeyError(f"character_id not found: {character_id}")

    def ids(self) -> List[str]:
        return [c.id for c in self.characters]

    def get_llm_temperature(self, character_id: str, default: float = 0.3) -> float:
        """获取角色的 temperature，如果未设置则推导默认值"""
        try:
            char = self.get_character(character_id)
            if char.llm_temperature is not None:
                return char.llm_temperature
            # 根据性格推导 temperature
            return TraitTemperatureMapper.infer_from_traits(char.personality)
        except KeyError:
            return default


class TraitTemperatureMapper:
    """
    V5.1 性格特征到温度的映射器
    根据角色性格自动推导合理的 temperature 值
    """

    # 高温度（更随机、情绪化）的关键词
    HIGH_TEMPERATURE_TRAITS = {
        # 情绪波动
        "冲动": 0.7, "冲动的": 0.7, "易怒": 0.7, "情绪化": 0.7, "暴躁": 0.8,
        # 冒险精神
        "鲁莽": 0.75, "大胆": 0.65, "冒险": 0.65, "激进": 0.7,
        # 不可预测
        "疯癫": 0.85, "疯狂": 0.8, "神秘": 0.55, "古怪": 0.6,
        # 其他特质
        "热血": 0.6, "激情": 0.6, "焦虑": 0.55, "恐慌": 0.7,
    }

    # 中温度（平衡）的关键词
    MEDIUM_TEMPERATURE_TRAITS = {
        # 社交性格
        "外向": 0.45, "开朗": 0.4, "幽默": 0.45, "健谈": 0.4,
        # 决策模式
        "灵活": 0.4, "变通": 0.4, "随机应变": 0.45,
        # 情绪状态
        "好奇": 0.5, "困惑": 0.5, "疑惑": 0.5, "怀疑": 0.45,
        "犹豫": 0.5, "纠结": 0.5,
    }

    # 低温度（更稳定、理智）的关键词
    LOW_TEMPERATURE_TRAITS = {
        # 理性类
        "冷静": 0.15, "理智": 0.15, "理性": 0.15, "逻辑": 0.1,
        # 克制类
        "克制": 0.2, "内敛": 0.2, "沉稳": 0.15, "稳重": 0.15,
        # 思考类
        "深思熟虑": 0.1, "严谨": 0.15, "保守": 0.2, "谨慎": 0.2,
        # 其他
        "冷漠": 0.25, "冷酷": 0.2, "无情": 0.2, "平静": 0.25,
        "专注": 0.2, "专业": 0.2, "克制": 0.2, "压抑": 0.3,
        "胆小": 0.25, "胆怯": 0.25, "懦弱": 0.25,
    }

    # 恐怖题材的经典角色预设
    HORROR_CHARACTER_PRESETS = {
        "冷静侦探": 0.15,
        "理智医生": 0.2,
        "胆小受害者": 0.6,
        "疯狂凶手": 0.8,
        "神秘老者": 0.5,
        "焦虑证人": 0.55,
        "怀疑论者": 0.45,
        "热血记者": 0.6,
        "保守警察": 0.3,
        "神秘灵媒": 0.6,
        "失忆主角": 0.4,
        "看门老人": 0.3,
    }

    @classmethod
    def infer_from_traits(cls, personality: Dict[str, Any]) -> float:
        """
        根据角色性格推导 temperature
        返回范围: 0.1 ~ 0.9
        默认: 0.3
        """
        scores: List[float] = []

        traits_text = ""
        if isinstance(personality, dict):
            if "traits" in personality and isinstance(personality["traits"], list):
                traits_text = " ".join(personality["traits"])
            if "type" in personality and isinstance(personality["type"], str):
                traits_text += " " + personality["type"]
            if "archetype" in personality and isinstance(personality["archetype"], str):
                traits_text += " " + personality["archetype"]
        elif isinstance(personality, list):
            traits_text = " ".join(personality)

        if not traits_text:
            return 0.3

        scores.clear()

        # 检查高温度关键词
        for trait, temp in cls.HIGH_TEMPERATURE_TRAITS.items():
            if trait in traits_text:
                scores.append(temp)

        # 检查中温度关键词
        for trait, temp in cls.MEDIUM_TEMPERATURE_TRAITS.items():
            if trait in traits_text:
                scores.append(temp)

        # 检查低温度关键词
        for trait, temp in cls.LOW_TEMPERATURE_TRAITS.items():
            if trait in traits_text:
                scores.append(temp)

        # 计算最终温度（取平均值，边界约束）
        if scores:
            avg_score = sum(scores) / len(scores)
            return max(0.1, min(0.9, avg_score))

        return 0.3


class ChapterGoal(BaseModel):
    goal: str
    pov: str
    start_time: str = "day1_20:00"
    target_progress: int = 100
    tick_limit: int = 30
    no_progress_limit: int = 4


class DiscoverRoute(BaseModel):
    route_id: str
    action_type: str
    target: str
    topic: Optional[str] = None
    required_skill: Optional[str] = None
    difficulty: int = 0
    min_attitude: Optional[int] = None
    result_text: str


class PlotValue(BaseModel):
    mystery: int = 0
    progress: int = 0
    conflict: int = 0


class OnDiscovered(BaseModel):
    add_known_fact_to: str = "discoverer"  # discoverer | all
    plot_value: PlotValue = Field(default_factory=PlotValue)


class Clue(BaseModel):
    id: str
    name: str = ""
    content: str
    truth_level: str = "hidden_fact"  # hidden_fact / visible_fact / rumor
    importance: int = 0
    discover_routes: List[DiscoverRoute] = Field(default_factory=list)
    on_discovered: OnDiscovered = Field(default_factory=OnDiscovered)


class CluesConfig(BaseModel):
    clues: List[Clue]

    def get_clue(self, clue_id: str) -> Clue:
        for c in self.clues:
            if c.id == clue_id:
                return c
        raise KeyError(f"clue_id not found: {clue_id}")

    def clue_ids(self) -> List[str]:
        return [c.id for c in self.clues]

    def all_topics_for_target(self, target_id: str) -> List[str]:
        topics: List[str] = []
        for clue in self.clues:
            for r in clue.discover_routes:
                if r.target == target_id and r.topic:
                    topics.append(r.topic)
        return sorted(list(set(topics)))


class WorldConfig(BaseModel):
    bible: WorldBible
    map: MapConfig
    characters: CharactersConfig
    clues: CluesConfig
    chapter_goal: ChapterGoal
    world_id: str = ""

    @classmethod
    def from_directory(cls, world_dir: Path) -> "WorldConfig":
        """从目录加载世界配置"""
        # 加载 world_bible.json
        bible_file = world_dir / "world_bible.json"
        with open(bible_file, "r", encoding="utf-8") as f:
            bible_data = json.load(f)
        bible = WorldBible(**bible_data)

        # 加载 characters.json
        characters_file = world_dir / "characters.json"
        with open(characters_file, "r", encoding="utf-8") as f:
            characters_data = json.load(f)
        # characters.json 可能是列表或包含 characters 键的字典
        if isinstance(characters_data, list):
            characters = CharactersConfig(characters=characters_data)
        else:
            characters = CharactersConfig(**characters_data)

        # 加载 map.json
        map_file = world_dir / "map.json"
        with open(map_file, "r", encoding="utf-8") as f:
            map_data = json.load(f)
        map_config = MapConfig(**map_data)

        # 加载 clues.json
        clues_file = world_dir / "clues.json"
        with open(clues_file, "r", encoding="utf-8") as f:
            clues_data = json.load(f)
        # clues.json 可能是列表或包含 clues 键的字典
        if isinstance(clues_data, list):
            clues = CluesConfig(clues=clues_data)
        else:
            clues = CluesConfig(**clues_data)

        # 加载 chapter_goal.json
        chapter_goal_file = world_dir / "chapter_goal.json"
        with open(chapter_goal_file, "r", encoding="utf-8") as f:
            chapter_goal_data = json.load(f)
        chapter_goal = ChapterGoal(**chapter_goal_data)

        return cls(
            bible=bible,
            map=map_config,
            characters=characters,
            clues=clues,
            chapter_goal=chapter_goal,
            world_id=bible.world_id,
        )
