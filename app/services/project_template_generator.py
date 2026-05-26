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
    用户输入简单想法，系统生成完整结构化项目模板。
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
        template_id = f"tpl_{request.genre[:2]}_{request.theme[:2]}_{abs(hash(request.protagonist_seed)) % 1000:03d}"

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
        return {
            "world_name": f"{request.core_location}边界",
            "genre": request.genre,
            "theme": request.theme,
            "time_period": "现代",
            "location": request.core_location,
            "atmosphere": request.tone,
            "core_concept": f"{request.protagonist_seed}在{request.core_location}中通过可验证线索理解异常规则与个人代价",
            "world_rules": [
                f"{request.core_location}中的异常只能通过行动和线索逐步验证",
                "隐藏行动者不会主动暴露完整目的，只会留下可追踪后果",
                "角色的选择会改变后续线索出现顺序",
                "最终真相必须由多条证据交叉支撑",
            ],
            "historical_events": [
                "核心异常首次留下可追踪痕迹",
                "近期出现与既有认知矛盾的新变化",
                "主角进入现场并触发第一组可验证线索",
            ],
            "preferred_elements": request.preferred_elements,
            "forbidden_elements": request.forbidden_elements,
        }

    def _generate_characters(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        return [
            {
                "character_id": "protagonist_001",
                "name": "林砚",
                "role": "主角",
                "description": request.protagonist_seed,
                "background": f"因个人目标被卷入{request.core_location}的异常处境",
                "motivation": f"在{request.core_location}中确认真相并承担相应代价",
                "personality_traits": ["警觉", "克制", "重视证据", "不轻信"],
                "relationships": {},
                "location_id": "location_gate",
            },
            {
                "character_id": "obstructor_001",
                "name": "沈伯衡",
                "role": "阻碍者",
                "description": f"与{request.core_location}存在利益或秘密关联的人物",
                "background": "知道部分规则，但不愿主动说明完整事实",
                "motivation": "阻止主角过早接触核心真相",
                "personality_traits": ["谨慎", "警惕", "回避关键问题"],
                "relationships": {},
                "location_id": "location_frontdesk",
            },
        ]

    def _generate_npcs(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        return [
            {
                "npc_id": "npc_witness_001",
                "name": "罗敏",
                "role": "目击者",
                "description": f"能从外围观察{request.core_location}变化的人",
                "background": "只掌握局部事实，担心卷入风险",
                "knowledge_level": "partial",
                "can_reveal_clues": ["clue_trace_001"],
                "location_id": "location_witness_point",
            },
            {
                "npc_id": "npc_hidden_actor_001",
                "name": "程疏影",
                "role": "隐藏行动者",
                "description": "通过痕迹和后果影响主线的人物或力量",
                "background": "与核心异常的运行机制存在关联",
                "knowledge_level": "fragmented",
                "can_reveal_clues": ["clue_hidden_actor_001"],
                "location_id": "location_inner",
            },
        ]

    def _generate_map(self, request: TemplateGenerationRequest) -> Dict[str, Any]:
        core = request.core_location
        return {
            "locations": [
                {
                    "location_id": "location_gate",
                    "name": f"{core}入口",
                    "description": "连接外部和核心区域的边界，状态与表面认知不完全一致",
                    "type": "entrance",
                    "connections": ["location_frontdesk"],
                    "clues": ["clue_boundary_001"],
                },
                {
                    "location_id": "location_frontdesk",
                    "name": f"{core}前区",
                    "description": "最先接触到规则异常和人物冲突的公共区域",
                    "type": "main_area",
                    "connections": ["location_gate", "location_hallway", "location_witness_point"],
                    "clues": ["clue_record_001"],
                },
                {
                    "location_id": "location_hallway",
                    "name": f"{core}内部通道",
                    "description": "通向更深区域的路径，残留近期行动痕迹",
                    "type": "corridor",
                    "connections": ["location_frontdesk", "location_archive", "location_deep"],
                    "clues": ["clue_trace_001"],
                },
                {
                    "location_id": "location_archive",
                    "name": f"{core}记录区",
                    "description": "保存旧记录或遗留信息的位置，部分内容出现缺口",
                    "type": "clue_room",
                    "connections": ["location_hallway"],
                    "clues": ["clue_record_gap_001"],
                },
                {
                    "location_id": "location_deep",
                    "name": f"{core}深处",
                    "description": "异常反馈更强的高风险区域",
                    "type": "danger_zone",
                    "connections": ["location_hallway", "location_inner"],
                    "clues": ["clue_rule_001"],
                },
                {
                    "location_id": "location_inner",
                    "name": f"{core}隐藏区域",
                    "description": "不在普通路径上，只通过线索和后果逐渐显现",
                    "type": "hidden_area",
                    "connections": ["location_deep"],
                    "clues": ["clue_hidden_actor_001"],
                },
                {
                    "location_id": "location_witness_point",
                    "name": f"{core}外围观察点",
                    "description": "能从外部角度验证核心区域变化的位置",
                    "type": "npc_room",
                    "connections": ["location_frontdesk"],
                    "clues": [],
                },
            ],
            "starting_location": "location_gate",
        }

    def _generate_clues(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        core = request.core_location
        return [
            {
                "clue_id": "clue_boundary_001",
                "name": "边界异常痕迹",
                "description": f"{core}入口附近出现与正常环境不符的近期改动",
                "reveal_stage": 1,
                "discover_routes": [
                    {"location": "location_gate", "method": "inspect"},
                    {"location": "location_frontdesk", "method": "observe"},
                    {"npc": "npc_witness_001", "method": "talk"},
                ],
            },
            {
                "clue_id": "clue_record_001",
                "name": "近期接触记录",
                "description": "现场存在近期被接触或整理过的记录痕迹",
                "reveal_stage": 2,
                "discover_routes": [
                    {"location": "location_frontdesk", "method": "search"},
                    {"location": "location_archive", "method": "inspect"},
                    {"npc": "obstructor_001", "method": "talk"},
                ],
            },
            {
                "clue_id": "clue_trace_001",
                "name": "未知行动痕迹",
                "description": "不属于当前可见角色的行动痕迹指向更深处",
                "reveal_stage": 2,
                "discover_routes": [
                    {"location": "location_hallway", "method": "observe"},
                    {"location": "location_hallway", "method": "inspect"},
                    {"npc": "npc_witness_001", "method": "talk"},
                ],
            },
            {
                "clue_id": "clue_record_gap_001",
                "name": "记录缺口",
                "description": "关键记录被移动、替换或隐藏，说明有人干预线索顺序",
                "reveal_stage": 3,
                "discover_routes": [
                    {"location": "location_archive", "method": "search"},
                    {"location": "location_frontdesk", "method": "search"},
                    {"npc": "obstructor_001", "method": "talk"},
                ],
            },
            {
                "clue_id": "clue_rule_001",
                "name": "异常规则证据",
                "description": "多个细节共同指向同一套可验证的异常规则",
                "reveal_stage": 5,
                "discover_routes": [
                    {"location": "location_deep", "method": "inspect"},
                    {"location": "location_archive", "method": "search"},
                    {"npc": "npc_hidden_actor_001", "method": "trace"},
                ],
            },
            {
                "clue_id": "clue_hidden_actor_001",
                "name": "隐藏行动者痕迹",
                "description": "线索出现顺序被人为或异常力量改变过",
                "reveal_stage": 6,
                "discover_routes": [
                    {"location": "location_inner", "method": "inspect"},
                    {"location": "location_deep", "method": "observe"},
                    {"npc": "npc_hidden_actor_001", "method": "trace"},
                ],
            },
            {
                "clue_id": "clue_truth_001",
                "name": "核心真相证据",
                "description": "足以解释核心异常来源和角色代价的最终证据",
                "reveal_stage": 8,
                "discover_routes": [
                    {"location": "location_inner", "method": "inspect"},
                    {"location": "location_deep", "method": "search"},
                    {"location": "location_archive", "method": "synthesize"},
                ],
            },
        ]

    def _generate_plot_arcs(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        return [
            {
                "arc_id": "main_arc_001",
                "name": "主线真相",
                "description": f"{request.protagonist_seed}在{request.core_location}中逐步验证异常规则、识别隐藏阻力并面对最终代价",
                "stages": [
                    {
                        "stage_id": "setup",
                        "name": "铺垫",
                        "chapter_range": [1, 2],
                        "goal": "建立地点、角色目标和第一组可验证异常",
                        "must_reveal_clues": ["clue_boundary_001"],
                    },
                    {
                        "stage_id": "investigation",
                        "name": "调查",
                        "chapter_range": [3, 6],
                        "goal": "收集线索并确认隐藏行动痕迹",
                        "must_reveal_clues": ["clue_record_001", "clue_trace_001", "clue_record_gap_001"],
                    },
                    {
                        "stage_id": "confrontation",
                        "name": "对峙",
                        "chapter_range": [7, 8],
                        "goal": "让角色目标与隐藏阻力发生正面冲突",
                        "must_reveal_clues": ["clue_rule_001", "clue_hidden_actor_001"],
                    },
                    {
                        "stage_id": "revelation",
                        "name": "真相",
                        "chapter_range": [9, 10],
                        "goal": "揭示最终真相并完成选择",
                        "must_reveal_clues": ["clue_truth_001"],
                    },
                ],
            },
        ]

    def _generate_character_arcs(self, request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        return [
            {
                "character_id": "protagonist_001",
                "arc_name": "选择与代价",
                "stages": [
                    {
                        "stage": "denial",
                        "description": "主角倾向用原有经验解释异常处境",
                        "chapter_range": [1, 2],
                    },
                    {
                        "stage": "doubt",
                        "description": "主角开始怀疑自己掌握的信息并不完整",
                        "chapter_range": [3, 5],
                    },
                    {
                        "stage": "confrontation",
                        "description": "主角被迫面对目标背后的真实代价",
                        "chapter_range": [6, 8],
                    },
                    {
                        "stage": "choice",
                        "description": "主角在真相与代价之间做出主动选择",
                        "chapter_range": [9, 10],
                    },
                ],
            },
        ]

    def _generate_style_bible(self, request: TemplateGenerationRequest) -> Dict[str, Any]:
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
                "物件状态变化带出线索",
            ],
            "reference_keywords": [
                request.core_location,
                request.theme,
                "边界",
                "痕迹",
                "代价",
            ],
        }

    def _generate_voice_profiles(
        self,
        request: TemplateGenerationRequest,
        characters: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return [
            {
                "character_id": char["character_id"],
                "speech_style": "克制、短句、不轻易暴露情绪",
                "inner_monologue": "在行动前反复确认可验证事实",
                "vocabulary": ["确认", "不对", "可能", "等等"],
                "forbidden": [
                    "突然热血宣言",
                    "过度自我解释",
                    "轻浮玩笑",
                ],
                "sample_lines": [
                    "我只想先确认一件事。",
                    "这个细节不像是自然留下的。",
                ],
            }
            for char in characters
        ]

    def _generate_chapter_seeds(
        self,
        request: TemplateGenerationRequest,
        plot_arcs: List[Dict[str, Any]],
    ) -> List[ChapterSeed]:
        plan = [
            (1, "建立核心地点、主角目标和第一处异常边界", "setup", ["protagonist_001", "location_gate"], ["边界为什么发生变化？", "谁最近接触过现场？"]),
            (2, "进入前区并发现近期接触记录", "setup", ["location_frontdesk"], ["现场为何不像长期无人接触？", "阻碍者知道什么？"]),
            (3, "追踪未知行动痕迹", "investigation", ["location_hallway"], ["痕迹属于谁？", "它为什么通向深处？"]),
            (4, "与阻碍者第一次正面冲突", "investigation", ["obstructor_001"], ["阻碍者在保护什么？", "哪些信息被刻意回避？"]),
            (5, "发现记录缺口并扩大怀疑范围", "investigation", ["location_archive"], ["缺失记录去了哪里？", "谁能改动线索顺序？"]),
            (6, "整合已有证据并确认异常不是孤立事件", "investigation", [], ["多条线索如何互相印证？", "主角是否误判了目标？"]),
            (7, "进入高风险区域并验证异常规则", "confrontation", ["location_deep"], ["规则如何运行？", "继续深入会付出什么代价？"]),
            (8, "隐藏行动者造成新的阻碍", "confrontation", ["npc_hidden_actor_001"], ["隐藏行动者为什么干预？", "谁从线索错位中获益？"]),
            (9, "进入隐藏区域并接近核心真相", "revelation", ["location_inner"], ["核心异常的来源是什么？", "主角必须承担什么选择？"]),
            (10, "揭示最终真相并完成角色选择", "revelation", [], []),
        ]
        return [
            ChapterSeed(
                chapter_no=chapter_no,
                chapter_function=function,
                target_stage=stage,
                must_introduce=must_introduce,
                suggested_threads=threads,
                must_not_reveal=["最终真相", "隐藏行动者真实目的"] if chapter_no < 9 else [],
            )
            for chapter_no, function, stage, must_introduce, threads in plan
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
            if routes < 2:
                warnings.append(f"线索 {clue_id} 只有 {routes} 条发现路径，建议至少2条")

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
        template_file = self.templates_dir / f"{template.template_id}.json"
        with open(template_file, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, ensure_ascii=False, indent=2)

    def load_template(self, template_id: str) -> Optional[ProjectTemplate]:
        template_file = self.templates_dir / f"{template_id}.json"
        if not template_file.exists():
            return None
        with open(template_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ProjectTemplate(**data)

    def list_templates(self) -> List[str]:
        return [f.stem for f in self.templates_dir.glob("*.json")]

    def create_project_from_template(self, template_id: str, project_name: str) -> Path:
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
