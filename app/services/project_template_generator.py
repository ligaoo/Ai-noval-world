from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.llm_client import OpenAICompatibleClient
from app.models.template import (
    ChapterSeed,
    ProjectTemplate,
    TemplateGenerationRequest,
)
from app.services.trace_service import TraceService


class ProjectTemplateGenerator:
    """
    V5.6 项目模板生成器
    用户输入简单想法，系统生成完整结构化项目模板
    - 生成世界圣经
    - 生成角色设定
    - 生成地图节点
    - 生成主线剧情弧
    - 生成线索网络
    - 生成人物弧
    - 生成文风圣经
    - 生成章节种子
    """

    def __init__(
        self,
        project_dir: Path,
        llm_client: Optional[OpenAICompatibleClient] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.project_dir = project_dir
        self.llm_client = llm_client
        self.trace_service = trace_service
        self.templates_dir = project_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)

    def generate_template(
        self,
        request: TemplateGenerationRequest,
    ) -> ProjectTemplate:
        """生成项目模板"""
        template_id = f"tpl_{request.genre[:2]}_{request.theme[:2]}_{hash(request.protagonist_seed) % 1000:03d}"

        world_bible = self._generate_world_bible(request)
        characters = self._generate_characters(request)
        npcs = self._generate_npcs(request)
        map_data = self._generate_map(request)
        clues = self._generate_clues(request)
        plot_arcs = self._generate_plot_arcs(request)
        character_arcs = self._generate_character_arcs(request)
        style_bible = self._generate_style_bible(request)
        voice_profiles = self._generate_voice_profiles(request, characters)
        chapter_seeds = self._generate_chapter_seeds(request, plot_arcs)

        validation_report = self._validate_template(
            world_bible, characters, map_data, clues, plot_arcs, chapter_seeds
        )

        template = ProjectTemplate(
            template_id=template_id,
            world_bible=world_bible,
            characters=characters,
            npcs=npcs,
            map=map_data,
            clues=clues,
            plot_arcs=plot_arcs,
            character_arcs=character_arcs,
            style_bible=style_bible,
            character_voice_profiles=voice_profiles,
            chapter_seed_plan=chapter_seeds,
            validation_report=validation_report,
        )

        self._save_template(template)
        return template

    def _generate_world_bible(self, request: TemplateGenerationRequest) -> Dict[str, Any]:
        """生成世界圣经"""
        return {
            "world_name": f"{request.core_location}的秘密",
            "genre": request.genre,
            "theme": request.theme,
            "time_period": "现代",
            "location": request.core_location,
            "atmosphere": request.tone,
            "core_concept": f"一个关于{request.protagonist_seed}在{request.core_location}中探索真相的故事",
            "world_rules": [
                "过去不会轻易被遗忘",
                "每个角落都可能藏着秘密",
                "记忆可能是不可靠的",
                "真相往往比想象的更残酷",
            ],
            "historical_events": [
                "十年前发生了一起神秘事件",
                "医院因为不明原因被废弃",
                "有传言说这里进行过非法实验",
            ],
        }

    def _generate_characters(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        """生成核心角色"""
        return [
            {
                "character_id": "protagonist_001",
                "name": "林舟",
                "role": "主角",
                "description": request.protagonist_seed,
                "background": "十年前的事件后失去了部分记忆",
                "motivation": "寻找失去的记忆，揭开过去的真相",
                "personality_traits": ["内向", "细心", "坚韧", "有些偏执"],
                "relationships": {},
                "location_id": "old_hospital_gate",
            },
            {
                "character_id": "antagonist_001",
                "name": "看守人",
                "role": "阻碍者",
                "description": "废弃医院的神秘看守人",
                "background": "似乎与十年前的事件有关",
                "motivation": "阻止主角发现真相",
                "personality_traits": ["沉默", "警觉", "忠诚"],
                "relationships": {},
                "location_id": "guard_room",
            },
        ]

    def _generate_npcs(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        """生成NPC"""
        return [
            {
                "npc_id": "npc_witness_001",
                "name": "老陈",
                "role": "目击者",
                "description": "住在医院附近的老人",
                "background": "见证了医院被废弃的过程",
                "knowledge_level": "partial",
                "can_reveal_clues": ["clue_history_001"],
                "location_id": "nearby_shop",
            },
            {
                "npc_id": "npc_ghost_001",
                "name": "幻影",
                "role": "线索提供者",
                "description": "偶尔出现在医院中的神秘身影",
                "background": "可能是过去的残影",
                "knowledge_level": "fragmented",
                "can_reveal_clues": ["clue_memory_001"],
                "location_id": "basement_corridor",
            },
        ]

    def _generate_map(self, request: TemplateGenerationRequest) -> Dict[str, Any]:
        """生成地图"""
        return {
            "locations": [
                {
                    "location_id": "old_hospital_gate",
                    "name": "旧医院大门",
                    "description": "生锈的铁门上挂着一把大锁",
                    "type": "entrance",
                    "connections": ["entrance_hall"],
                    "clues": ["clue_lock_001"],
                },
                {
                    "location_id": "entrance_hall",
                    "name": "入口大厅",
                    "description": "阴暗潮湿，空气中弥漫着旧消毒水的味道",
                    "type": "main_area",
                    "connections": ["old_hospital_gate", "ward_corridor", "nurse_station"],
                    "clues": ["clue_logbook_001"],
                },
                {
                    "location_id": "ward_corridor",
                    "name": "病房走廊",
                    "description": "两侧是关着门的病房，偶尔传来轻微的声响",
                    "type": "corridor",
                    "connections": ["entrance_hall", "room_302", "basement_stairs"],
                    "clues": ["clue_footprints_001"],
                },
                {
                    "location_id": "nurse_station",
                    "name": "护士站",
                    "description": "桌上散落着旧病历和被遗弃的医疗用品",
                    "type": "clue_room",
                    "connections": ["entrance_hall"],
                    "clues": ["clue_medical_records_001"],
                },
                {
                    "location_id": "room_302",
                    "name": "302病房",
                    "description": "似乎是主角曾经住过的房间",
                    "type": "personal_room",
                    "connections": ["ward_corridor"],
                    "clues": ["clue_personal_item_001"],
                },
                {
                    "location_id": "basement_stairs",
                    "name": "地下室楼梯",
                    "description": "通往地下室的楼梯，楼梯口有一道铁门",
                    "type": "transition",
                    "connections": ["ward_corridor", "basement_corridor"],
                    "clues": ["clue_basement_key_001"],
                },
                {
                    "location_id": "basement_corridor",
                    "name": "地下室走廊",
                    "description": "最深处隐藏着十年前的真相",
                    "type": "truth_room",
                    "connections": ["basement_stairs", "hidden_room"],
                    "clues": ["clue_experiment_001"],
                },
                {
                    "location_id": "hidden_room",
                    "name": "密室",
                    "description": "真相所在的地方",
                    "type": "final_room",
                    "connections": ["basement_corridor"],
                    "clues": ["clue_truth_001"],
                },
                {
                    "location_id": "guard_room",
                    "name": "看守人房间",
                    "description": "看守人居住的地方",
                    "type": "npc_room",
                    "connections": ["entrance_hall"],
                    "clues": [],
                },
                {
                    "location_id": "nearby_shop",
                    "name": "附近的小店",
                    "description": "医院附近的杂货店",
                    "type": "npc_room",
                    "connections": [],
                    "clues": [],
                },
            ],
            "starting_location": "old_hospital_gate",
        }

    def _generate_clues(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        """生成线索"""
        return [
            {
                "clue_id": "clue_lock_001",
                "name": "新锁",
                "description": "大门上的锁看起来很新，不像放了十年的样子",
                "reveal_stage": 1,
                "discover_routes": [
                    {"location": "old_hospital_gate", "method": "inspect"},
                ],
            },
            {
                "clue_id": "clue_logbook_001",
                "name": "访客记录",
                "description": "最后一页有被撕掉的痕迹",
                "reveal_stage": 2,
                "discover_routes": [
                    {"location": "entrance_hall", "method": "search"},
                ],
            },
            {
                "clue_id": "clue_footprints_001",
                "name": "新鲜脚印",
                "description": "走廊地上有新鲜的脚印",
                "reveal_stage": 2,
                "discover_routes": [
                    {"location": "ward_corridor", "method": "observe"},
                ],
            },
            {
                "clue_id": "clue_medical_records_001",
                "name": "医疗记录",
                "description": "有一份主角的医疗记录，但关键信息被涂黑",
                "reveal_stage": 3,
                "discover_routes": [
                    {"location": "nurse_station", "method": "search"},
                    {"npc": "npc_witness_001", "method": "talk"},
                ],
            },
            {
                "clue_id": "clue_personal_item_001",
                "name": "旧照片",
                "description": "病房里有一张主角和某人的合影",
                "reveal_stage": 4,
                "discover_routes": [
                    {"location": "room_302", "method": "search"},
                ],
            },
            {
                "clue_id": "clue_basement_key_001",
                "name": "地下室钥匙",
                "description": "一把生锈的钥匙",
                "reveal_stage": 5,
                "discover_routes": [
                    {"location": "nurse_station", "method": "search"},
                    {"npc": "npc_witness_001", "method": "talk"},
                ],
            },
            {
                "clue_id": "clue_experiment_001",
                "name": "实验记录",
                "description": "关于非法实验的记录",
                "reveal_stage": 6,
                "discover_routes": [
                    {"location": "basement_corridor", "method": "search"},
                ],
            },
            {
                "clue_id": "clue_truth_001",
                "name": "真相",
                "description": "主角自己就是当年的实验对象",
                "reveal_stage": 7,
                "discover_routes": [
                    {"location": "hidden_room", "method": "inspect"},
                ],
            },
        ]

    def _generate_plot_arcs(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        """生成剧情弧"""
        return [
            {
                "arc_id": "main_arc_001",
                "name": "揭开真相",
                "description": "主角探索废弃医院，逐步揭开自己失去的记忆和十年前的真相",
                "stages": [
                    {
                        "stage_id": "setup",
                        "name": "铺垫",
                        "chapter_range": [1, 2],
                        "goal": "建立场景和角色动机",
                        "must_reveal_clues": ["clue_lock_001"],
                    },
                    {
                        "stage_id": "investigation",
                        "name": "调查",
                        "chapter_range": [3, 6],
                        "goal": "收集线索，逐步深入",
                        "must_reveal_clues": ["clue_logbook_001", "clue_medical_records_001", "clue_personal_item_001"],
                    },
                    {
                        "stage_id": "confrontation",
                        "name": "对峙",
                        "chapter_range": [7, 8],
                        "goal": "与阻碍者对峙，突破障碍",
                        "must_reveal_clues": ["clue_basement_key_001", "clue_experiment_001"],
                    },
                    {
                        "stage_id": "revelation",
                        "name": "真相",
                        "chapter_range": [9, 10],
                        "goal": "揭示最终真相，完成人物弧",
                        "must_reveal_clues": ["clue_truth_001"],
                    },
                ],
            },
        ]

    def _generate_character_arcs(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        """生成人物弧"""
        return [
            {
                "character_id": "protagonist_001",
                "arc_name": "自我发现之旅",
                "stages": [
                    {
                        "stage": "denial",
                        "description": "主角不愿承认自己与医院的联系",
                        "chapter_range": [1, 2],
                    },
                    {
                        "stage": "doubt",
                        "description": "主角开始怀疑自己的记忆",
                        "chapter_range": [3, 5],
                    },
                    {
                        "stage": "confrontation",
                        "description": "主角被迫面对过去",
                        "chapter_range": [6, 8],
                    },
                    {
                        "stage": "acceptance",
                        "description": "主角接受真相，完成转变",
                        "chapter_range": [9, 10],
                    },
                ],
            },
        ]

    def _generate_style_bible(self, request: TemplateGenerationRequest) -> Dict[str, Any]:
        """生成文风圣经"""
        return {
            "style_id": f"{request.genre}_style",
            "tone": request.tone,
            "sentence_style": "中短句为主，避免过度华丽",
            "description_level": "适度环境描写，避免堆砌形容词",
            "dialogue_style": "含蓄、留白、带潜台词",
            "pacing_style": "慢热，但每章必须有实质推进",
            "horror_style": "现实细节中透出异常，避免直接惊吓",
            "forbidden_styles": request.forbidden_elements,
            "preferred_devices": [
                "细节反常",
                "短暂停顿",
                "未说完的话",
                "旧物件带出的记忆",
            ],
            "reference_keywords": [
                "潮湿",
                "昏暗",
                "迟疑",
                "锈迹",
                "旧灯",
            ],
        }

    def _generate_voice_profiles(
        self,
        request: TemplateGenerationRequest,
        characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """生成角色声音档案"""
        return [
            {
                "character_id": char["character_id"],
                "speech_style": "克制、短句、不轻易暴露情绪",
                "inner_monologue": "怀疑自己，但习惯压下恐惧",
                "vocabulary": ["确认", "不对", "可能", "等等"],
                "forbidden": [
                    "突然热血宣言",
                    "过度自我解释",
                    "轻浮玩笑",
                ],
                "sample_lines": [
                    "我只是想确认一件事。",
                    "这把锁，不像是放了十年。",
                ],
            }
            for char in characters
        ]

    def _generate_chapter_seeds(
        self,
        request: TemplateGenerationRequest,
        plot_arcs: List[Dict[str, Any]],
    ) -> List[ChapterSeed]:
        """生成章节种子"""
        return [
            ChapterSeed(
                chapter_no=1,
                chapter_function="建立旧医院异常与主角噩梦",
                target_stage="setup",
                must_introduce=["protagonist_001", "old_hospital_gate"],
                suggested_threads=[
                    "旧医院是否真的废弃？",
                    "主角为什么梦见医院？",
                ],
                must_not_reveal=["十年前事故真相", "反派真实身份"],
            ),
            ChapterSeed(
                chapter_no=2,
                chapter_function="主角进入医院，发现门锁异常",
                target_stage="setup",
                must_introduce=["entrance_hall"],
                suggested_threads=[
                    "是谁在维护这把锁？",
                    "最近有人来过吗？",
                ],
                must_not_reveal=["十年前事故真相", "反派真实身份"],
            ),
            ChapterSeed(
                chapter_no=3,
                chapter_function="探索护士站，发现被撕掉的记录",
                target_stage="investigation",
                must_introduce=["nurse_station"],
                suggested_threads=[
                    "谁撕掉了访客记录？",
                    "最后一个访客是谁？",
                ],
                must_not_reveal=["十年前事故真相", "反派真实身份"],
            ),
            ChapterSeed(
                chapter_no=4,
                chapter_function="遇到看守人，第一次对峙",
                target_stage="investigation",
                must_introduce=["antagonist_001"],
                suggested_threads=[
                    "看守人在隐瞒什么？",
                    "他为什么不让主角深入？",
                ],
                must_not_reveal=["十年前事故真相", "反派真实身份"],
            ),
            ChapterSeed(
                chapter_no=5,
                chapter_function="发现主角的医疗记录",
                target_stage="investigation",
                must_introduce=["room_302"],
                suggested_threads=[
                    "主角真的在这里住过？",
                    "为什么病历被涂黑？",
                ],
                must_not_reveal=["十年前事故真相", "反派真实身份"],
            ),
            ChapterSeed(
                chapter_no=6,
                chapter_function="找到旧照片，记忆开始复苏",
                target_stage="investigation",
                must_introduce=[],
                suggested_threads=[
                    "照片上的另一个人是谁？",
                    "主角忘记了什么？",
                ],
                must_not_reveal=["十年前事故真相", "反派真实身份"],
            ),
            ChapterSeed(
                chapter_no=7,
                chapter_function="获得地下室钥匙",
                target_stage="confrontation",
                must_introduce=["basement_stairs"],
                suggested_threads=[
                    "地下室藏着什么？",
                    "看守人会阻止吗？",
                ],
                must_not_reveal=["十年前事故真相"],
            ),
            ChapterSeed(
                chapter_no=8,
                chapter_function="与看守人最终对峙，发现他的身份",
                target_stage="confrontation",
                must_introduce=["basement_corridor"],
                suggested_threads=[
                    "看守人的真实身份是什么？",
                    "他为什么要保护这个秘密？",
                ],
                must_not_reveal=["十年前事故真相"],
            ),
            ChapterSeed(
                chapter_no=9,
                chapter_function="进入密室，发现实验记录",
                target_stage="revelation",
                must_introduce=["hidden_room"],
                suggested_threads=[
                    "医院进行了什么实验？",
                    "主角是实验对象吗？",
                ],
                must_not_reveal=[],
            ),
            ChapterSeed(
                chapter_no=10,
                chapter_function="最终真相大白，主角完成自我接纳",
                target_stage="revelation",
                must_introduce=[],
                suggested_threads=[],
                must_not_reveal=[],
            ),
        ]

    def _validate_template(
        self,
        world_bible: Dict[str, Any],
        characters: List[Dict[str, Any]],
        map_data: Dict[str, Any],
        clues: List[Dict[str, Any]],
        plot_arcs: List[Dict[str, Any]],
        chapter_seeds: List[ChapterSeed],
    ) -> Dict[str, Any]:
        """验证模板完整性"""
        issues = []
        warnings = []

        location_ids = {loc["location_id"] for loc in map_data.get("locations", [])}
        for clue in clues:
            for route in clue.get("discover_routes", []):
                if "location" in route and route["location"] not in location_ids:
                    issues.append(f"线索 {clue['clue_id']} 引用了不存在的位置: {route['location']}")

        for arc in plot_arcs:
            for stage in arc.get("stages", []):
                for clue_id in stage.get("must_reveal_clues", []):
                    if not any(c["clue_id"] == clue_id for c in clues):
                        issues.append(f"剧情弧引用了不存在的线索: {clue_id}")

        clue_routes = {clue["clue_id"]: len(clue.get("discover_routes", [])) for clue in clues}
        for clue_id, routes in clue_routes.items():
            if routes < 3:
                warnings.append(f"线索 {clue_id} 只有 {routes} 条发现路径，建议至少3条")

        total_chapters = len(chapter_seeds)
        expected_chapters = 10
        if total_chapters != expected_chapters:
            warnings.append(f"章节种子数量为 {total_chapters}，预期为 {expected_chapters}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - len(issues) * 10 - len(warnings) * 2,
        }

    def _save_template(self, template: ProjectTemplate) -> None:
        """保存模板"""
        template_file = self.templates_dir / f"{template.template_id}.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

    def load_template(self, template_id: str) -> Optional[ProjectTemplate]:
        """加载模板"""
        template_file = self.templates_dir / f"{template_id}.json"
        if not template_file.exists():
            return None
        with open(template_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProjectTemplate(**data)

    def list_templates(self) -> List[str]:
        """列出所有模板"""
        return [f.stem for f in self.templates_dir.glob("*.json")]

    def create_project_from_template(self, template_id: str, project_name: str) -> Path:
        """从模板创建项目"""
        template = self.load_template(template_id)
        if not template:
            raise ValueError(f"模板 {template_id} 不存在")

        project_dir = self.project_dir / "worlds" / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        with open(project_dir / "world_bible.json", "w", encoding="utf-8") as f:
            json.dump(template.world_bible, f, ensure_ascii=False, indent=2)

        with open(project_dir / "characters.json", "w", encoding="utf-8") as f:
            json.dump(template.characters, f, ensure_ascii=False, indent=2)

        with open(project_dir / "npcs.json", "w", encoding="utf-8") as f:
            json.dump(template.npcs, f, ensure_ascii=False, indent=2)

        with open(project_dir / "map.json", "w", encoding="utf-8") as f:
            json.dump(template.map, f, ensure_ascii=False, indent=2)

        with open(project_dir / "clues.json", "w", encoding="utf-8") as f:
            json.dump(template.clues, f, ensure_ascii=False, indent=2)

        with open(project_dir / "plot_arcs.json", "w", encoding="utf-8") as f:
            json.dump(template.plot_arcs, f, ensure_ascii=False, indent=2)

        with open(project_dir / "character_arcs.json", "w", encoding="utf-8") as f:
            json.dump(template.character_arcs, f, ensure_ascii=False, indent=2)

        with open(project_dir / "style_bible.json", "w", encoding="utf-8") as f:
            json.dump(template.style_bible, f, ensure_ascii=False, indent=2)

        with open(project_dir / "character_voice_profiles.json", "w", encoding="utf-8") as f:
            json.dump(template.character_voice_profiles, f, ensure_ascii=False, indent=2)

        with open(project_dir / "chapter_seed_plan.json", "w", encoding="utf-8") as f:
            json.dump([c.to_dict() for c in template.chapter_seed_plan], f, ensure_ascii=False, indent=2)

        return project_dir
