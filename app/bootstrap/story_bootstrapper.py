from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .bootstrap_map_generator import BootstrapMapGenerator
from .bootstrap_validator import BootstrapValidator
from .clue_route_generator import ClueRouteGenerator
from .evidence_graph_generator import EvidenceGraphGenerator
from .minimum_cast_generator import MinimumCastGenerator
from .models import (
    BootstrapClue,
    BootstrapResult,
    BootstrapSeed,
    CharacterWithAgent,
    OpeningChapterPlan,
)
from .open_thread_seed_generator import OpenThreadSeedGenerator
from .opening_chapter_goal_generator import OpeningChapterGoalGenerator
from .seed_interpreter import SeedInterpreter
from .truth_chain_generator import TruthChainGenerator
from .world_bible_generator import WorldBibleGenerator
from .writer_anchor_generator import WriterStoryAnchorGenerator


class StoryBootstrapper:
    """
    StoryBootstrapper：编排所有子生成器，把一句模糊设定补全为可运行世界
    使命：把生成结果以「现有 WorldConfig.from_directory 兼容的格式」写到 worlds/<world_id>/
    这样不需要改 SimulationRunner 就能直接跑起来。
    """

    def __init__(self, project_root: Path, llm_client=None):
        self.project_root = project_root
        self.llm_client = llm_client

        self.seed_interpreter = SeedInterpreter(llm_client)
        self.world_bible_gen = WorldBibleGenerator(llm_client)
        self.cast_gen = MinimumCastGenerator(llm_client)
        self.map_gen = BootstrapMapGenerator(llm_client)
        self.truth_gen = TruthChainGenerator(llm_client)
        self.evidence_gen = EvidenceGraphGenerator(llm_client)
        self.clue_gen = ClueRouteGenerator(llm_client)
        self.thread_gen = OpenThreadSeedGenerator(llm_client)
        self.opening_gen = OpeningChapterGoalGenerator(llm_client)
        self.anchor_gen = WriterStoryAnchorGenerator(llm_client)
        self.validator = BootstrapValidator()

    # ============================================================
    # 主入口
    # ============================================================
    def bootstrap(self, seed: BootstrapSeed, world_id: Optional[str] = None) -> BootstrapResult:
        bootstrap_id = f"boot_{int(time.time() * 1000)}"
        if not world_id:
            world_id = f"world_auto_{int(time.time())}"

        parsed = self.seed_interpreter.interpret(seed.user_seed)
        bible = self.world_bible_gen.generate(parsed, world_id)
        cast = self.cast_gen.generate(parsed)
        map_locs = self.map_gen.generate(parsed)
        truth = self.truth_gen.generate(parsed)
        evidence = self.evidence_gen.generate(parsed)
        clues = self.clue_gen.generate(parsed)
        threads = self.thread_gen.generate(parsed)
        protagonist_name = next((c.name for c in cast if c.role == "protagonist"), "主角")
        opening = self.opening_gen.generate(parsed, protagonist_name=protagonist_name)
        self._ensure_opening_selected_clues(opening, clues)
        anchors = self.anchor_gen.generate(
            title=bible.get("title", world_id),
            parsed=parsed,
            opening=opening,
            protagonist_name=protagonist_name,
        )

        result = BootstrapResult(
            bootstrap_id=bootstrap_id,
            world_id=world_id,
            status="candidate_generated",
            title=bible.get("title", world_id),
            world_bible=bible,
            characters=cast,
            map=map_locs,
            clues=clues,
            truth_chain=truth,
            evidence_graph=evidence,
            open_threads=threads,
            opening_chapter_plan=opening,
            writer_story_anchors=anchors,
            chapter_goal=self._build_chapter_goal(opening, cast),
            parsed_seed=parsed,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        result.validation = self.validator.validate(result)
        if result.validation.passed:
            result.status = "validated"
        else:
            result.status = "validation_failed"

        return result

    def _ensure_opening_selected_clues(
        self,
        opening: OpeningChapterPlan,
        clues: List[BootstrapClue],
    ) -> None:
        clue_ids = {clue.clue_id for clue in clues}
        selected = [clue_id for clue_id in opening.selected_clues if clue_id in clue_ids]
        discoverable = [clue.clue_id for clue in clues if clue.discover_routes]
        for clue_id in discoverable:
            if len(selected) >= 3:
                break
            if clue_id not in selected:
                selected.append(clue_id)
        opening.selected_clues = selected

    def _build_chapter_goal(self, opening: OpeningChapterPlan, cast: List[CharacterWithAgent]) -> Dict[str, Any]:
        pov = next((c.character_id for c in cast if c.role == "protagonist"), "char_protagonist")
        return {
            "goal": opening.chapter_function or opening.protagonist_goal or "Setup the story",
            "pov": pov,
            "start_time": "day1_14:00",
            "target_progress": 100,
            "tick_limit": 30,
            "no_progress_limit": 4,
        }

    # ============================================================
    # 写盘：转换为现有 WorldConfig.from_directory 兼容的格式
    # ============================================================
    def write_to_worlds_dir(self, result: BootstrapResult) -> Path:
        world_dir = self.project_root / "worlds" / result.world_id
        world_dir.mkdir(parents=True, exist_ok=True)

        # 1. world_bible.json（兼容 WorldBible 模型）
        bible = dict(result.world_bible)
        bible.setdefault("world_id", result.world_id)
        bible.setdefault("rules", [])
        bible.setdefault("themes", [])
        bible.setdefault("core_motif", bible.get("core_motif") or (bible.get("themes") or [""])[0] if bible.get("themes") else "异常")
        bible.setdefault("main_question", bible.get("main_question") or result.chapter_goal.get("goal", "本章需要确认什么异常正在发生？"))
        bible.setdefault("hidden_truth", bible.get("hidden_truth") or "隐藏真相不能在第一章直接确认。")
        bible.setdefault("first_volume_goal", bible.get("first_volume_goal") or result.chapter_goal.get("goal", "逐步推进主线。"))
        bible.setdefault("ending_direction", bible.get("ending_direction") or "通过多章线索逐步逼近真相。")
        bible.setdefault("forbidden_early_reveals", bible.get("forbidden_early_reveals") or ["隐藏行动者身份", "最终真相"])
        bible.pop("draft", None)
        bible.pop("draft_reason", None)
        with open(world_dir / "world_bible.json", "w", encoding="utf-8") as f:
            json.dump(bible, f, ensure_ascii=False, indent=2)

        # 2. characters.json（兼容 CharactersConfig）
        char_json = {
            "characters": [
                {
                    "id": c.character_id,
                    "name": c.name,
                    "role": c.role,
                    "personality": {"traits": c.personality_traits},
                    "goals": {
                        "short_term": c.goal,
                        "long_term": c.goal,
                    },
                    "fears": c.fears,
                    "secrets": c.secrets,
                    "skills": c.skills or {"observation": 70, "logic": 65},
                    "initial_location": c.location_id or "location_gate",
                    "background": c.background,
                    "active_agent": c.active_agent,
                    "visibility": c.visibility,
                    "narrative_function": c.narrative_function,
                    "personal_stakes": c.personal_stakes,
                    "public_motive": c.public_motive,
                    "private_motive": c.private_motive,
                    "withheld_information": c.withheld_information,
                    "suspicious_micro_actions": c.suspicious_micro_actions,
                    "private_hook": c.private_hook,
                    "emotional_core": c.emotional_core,
                    "known_facts": c.known_facts,
                    "suspicions": c.suspicions,
                    "inventory": c.inventory,
                    "disclosure_policy": c.disclosure_policy.model_dump() if c.disclosure_policy else {},
                    "llm_temperature": c.llm_temperature,
                }
                for c in result.characters
            ]
        }
        with open(world_dir / "characters.json", "w", encoding="utf-8") as f:
            json.dump(char_json, f, ensure_ascii=False, indent=2)

        # 3. map.json（兼容 MapConfig）
        map_json = {
            "locations": [
                {
                    "id": loc.location_id,
                    "name": loc.name,
                    "public_description": loc.public_description or loc.name,
                    "objects": [
                        {
                            "id": obj.object_id,
                            "name": obj.object_id,
                            "visible": True,
                            "state": "",
                            "description": obj.description,
                        }
                        for obj in loc.objects
                    ],
                    "connected_to": loc.connected_to,
                    "danger_level": loc.danger_level,
                    "narrative_function": loc.type,
                    "information_gap": f"{loc.name}保留了需要通过行动验证的信息差。",
                    "suitable_conflicts": ["观察误判", "线索解释分歧"],
                    "forbidden_events": ["直接揭示最终真相"],
                }
                for loc in result.map
            ]
        }
        with open(world_dir / "map.json", "w", encoding="utf-8") as f:
            json.dump(map_json, f, ensure_ascii=False, indent=2)

        # 4. clues.json（兼容 CluesConfig，含 discover_routes / on_discovered）
        clues_json = {
            "clues": [
                {
                    "id": c.clue_id,
                    "name": c.title,
                    "content": c.content or c.title,
                    "truth_level": "hidden_fact",
                    "importance": c.on_discovered.plot_progress or 10,
                    "discover_routes": [
                        {
                            "route_id": f"{c.clue_id}_route_{i}",
                            "action_type": r.action,
                            "target": r.target or r.object_id or r.location_id,
                            "location_id": r.location_id,
                            "topic": r.topic,
                            "required_skill": r.required_skill,
                            "difficulty": r.difficulty,
                            "result_text": c.on_discovered.add_known_fact or c.content,
                        }
                        for i, r in enumerate(c.discover_routes)
                    ],
                    "on_discovered": {
                        "add_known_fact_to": "discoverer",
                        "plot_value": {
                            "mystery": 5,
                            "progress": c.on_discovered.plot_progress or 10,
                            "conflict": 3,
                        },
                    },
                    # bootstrap 扩展字段（供 ClueDiscoveryResolver 使用）
                    "bootstrap_fact": c.on_discovered.add_known_fact,
                    "bootstrap_inventory": c.on_discovered.add_inventory_item,
                    "bootstrap_event": c.on_discovered.trigger_event,
                    "related_thread": c.related_thread,
                }
                for c in result.clues
            ]
        }
        with open(world_dir / "clues.json", "w", encoding="utf-8") as f:
            json.dump(clues_json, f, ensure_ascii=False, indent=2)

        # 5. chapter_goal.json（兼容 ChapterGoal）
        with open(world_dir / "chapter_goal.json", "w", encoding="utf-8") as f:
            json.dump(result.chapter_goal, f, ensure_ascii=False, indent=2)

        # 6. writer_story_anchors.json（NarrativeService 会加载）
        if result.writer_story_anchors:
            with open(world_dir / "writer_story_anchors.json", "w", encoding="utf-8") as f:
                json.dump(result.writer_story_anchors.model_dump(), f, ensure_ascii=False, indent=2)

        # 7. truth_chain.json / evidence_graph.json / open_threads.json / opening_chapter_plan.json
        if result.truth_chain:
            with open(world_dir / "truth_chain.json", "w", encoding="utf-8") as f:
                json.dump(result.truth_chain.model_dump(), f, ensure_ascii=False, indent=2)

        with open(world_dir / "evidence_graph.json", "w", encoding="utf-8") as f:
            json.dump([e.model_dump() for e in result.evidence_graph], f, ensure_ascii=False, indent=2)

        with open(world_dir / "open_threads.json", "w", encoding="utf-8") as f:
            json.dump([t.model_dump() for t in result.open_threads], f, ensure_ascii=False, indent=2)

        if result.opening_chapter_plan:
            with open(world_dir / "opening_chapter_plan.json", "w", encoding="utf-8") as f:
                json.dump(result.opening_chapter_plan.model_dump(), f, ensure_ascii=False, indent=2)

        with open(world_dir / "bootstrap_result.json", "w", encoding="utf-8") as f:
            json.dump(result.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

        # 8. bootstrap_manifest.json（用于审计 + GET /bootstrap/{id}）
        with open(world_dir / "bootstrap_manifest.json", "w", encoding="utf-8") as f:
            json.dump({
                "bootstrap_id": result.bootstrap_id,
                "world_id": result.world_id,
                "status": result.status,
                "title": result.title,
                "created_at": result.created_at,
                "summary": result.summary_dict(),
                "parsed_seed": result.parsed_seed.model_dump() if result.parsed_seed else None,
                "validation": result.validation.model_dump() if result.validation else None,
                "fusion_report": result.fusion_report,
            }, f, ensure_ascii=False, indent=2)

        return world_dir
