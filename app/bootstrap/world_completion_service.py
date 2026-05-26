from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.world_runtime_validator import RuntimeWorldValidator

from .models import (
    BootstrapClue,
    BootstrapLocation,
    BootstrapLocationObject,
    BootstrapResult,
    BootstrapSeed,
    CharacterWithAgent,
    DiscoverRoute,
    OnDiscovered,
)
from .story_bootstrapper import StoryBootstrapper


class WorldCompletionService:
    def __init__(self, project_root: Path, bootstrapper: StoryBootstrapper):
        self.project_root = project_root
        self.bootstrapper = bootstrapper
        self.worlds_dir = project_root / "worlds"
        self.placeholders = RuntimeWorldValidator.PLACEHOLDER_TEXT

    def preview_completion(
        self,
        world_id: str,
        user_seed: Optional[str] = None,
        manual_world_payload: Optional[Dict[str, Any]] = None,
        target_genre: str = "horror_suspense",
        target_words: int = 100000,
    ) -> BootstrapResult:
        manual_world = self.normalize_manual_world(
            manual_world_payload if manual_world_payload is not None else self.load_manual_world(world_id),
            world_id,
        )
        seed_text = self.manual_world_to_seed(manual_world, user_seed)
        result = self.bootstrapper.bootstrap(
            BootstrapSeed(
                user_seed=seed_text,
                target_genre=target_genre,
                target_words=target_words,
            ),
            world_id=world_id,
        )
        self.merge_bootstrap_with_manual(result, manual_world)
        result.validation = self.bootstrapper.validator.validate(result)
        result.status = "validated" if result.validation.passed else "validation_failed"
        return result

    def load_manual_world(self, world_id: str) -> Dict[str, Any]:
        world_dir = self.worlds_dir / world_id
        if not world_dir.exists():
            raise FileNotFoundError(f"World not found: {world_id}")

        data: Dict[str, Any] = {}
        for name in ["world_bible", "characters", "map", "clues", "plot_arcs", "character_arcs", "chapter_goal"]:
            path = world_dir / f"{name}.json"
            if path.exists():
                data[name] = json.loads(path.read_text(encoding="utf-8"))
        return data

    def normalize_manual_world(self, payload: Dict[str, Any], world_id: str) -> Dict[str, Any]:
        bible = dict(payload.get("world_bible") or {})
        bible["world_id"] = world_id
        bible.setdefault("rules", [])
        bible.setdefault("themes", [])

        characters_payload = payload.get("characters") or []
        if isinstance(characters_payload, dict):
            characters_payload = characters_payload.get("characters") or []

        map_payload = payload.get("map") or []
        if isinstance(map_payload, dict):
            locations_payload = map_payload.get("locations") or []
        else:
            locations_payload = map_payload

        clues_payload = payload.get("clues") or []
        if isinstance(clues_payload, dict):
            clues_payload = clues_payload.get("clues") or []

        return {
            "world_bible": bible,
            "characters": [self._normalize_character(c) for c in characters_payload if isinstance(c, dict)],
            "map": [self._normalize_location(loc) for loc in locations_payload if isinstance(loc, dict)],
            "clues": [self._normalize_clue(c) for c in clues_payload if isinstance(c, dict)],
            "plot_arcs": payload.get("plot_arcs") or [],
            "character_arcs": payload.get("character_arcs") or [],
            "chapter_goal": dict(payload.get("chapter_goal") or {}),
        }

    def manual_world_to_seed(self, manual_world: Dict[str, Any], user_seed: Optional[str]) -> str:
        bible = manual_world["world_bible"]
        lines = ["请基于以下用户已填写的世界设定补全为可正式运行的小说模拟世界。"]
        if self._meaningful(bible.get("title")):
            lines.append(f"标题：{bible.get('title')}")
        if self._meaningful(bible.get("genre")):
            lines.append(f"题材：{bible.get('genre')}")
        if self._meaningful(bible.get("era")):
            lines.append(f"时代：{bible.get('era')}")
        if self._meaningful(bible.get("tone")):
            lines.append(f"基调：{bible.get('tone')}")
        if self._meaningful(bible.get("rules")):
            lines.append("世界规则：" + "；".join(str(x) for x in bible.get("rules", []) if self._meaningful(x)))
        if self._meaningful(bible.get("themes")):
            lines.append("主题：" + "；".join(str(x) for x in bible.get("themes", []) if self._meaningful(x)))

        if manual_world["characters"]:
            lines.append("用户已有角色/NPC：")
            for c in manual_world["characters"]:
                parts = [c.get("id", ""), c.get("name", ""), c.get("role", "")]
                goals = c.get("goals") or {}
                if isinstance(goals, dict):
                    parts.extend([goals.get("short_term", ""), goals.get("long_term", "")])
                parts.append(c.get("background", ""))
                lines.append("- " + " / ".join(str(p) for p in parts if self._meaningful(p)))

        if manual_world["map"]:
            lines.append("用户已有地点：")
            for loc in manual_world["map"]:
                lines.append(f"- {loc.get('id')}: {loc.get('name')} / {loc.get('public_description')}")

        if manual_world["clues"]:
            lines.append("用户已有线索：")
            for clue in manual_world["clues"]:
                lines.append(f"- {clue.get('id')}: {clue.get('name')} / {clue.get('content')}")

        if self._meaningful(user_seed):
            lines.append(f"用户补充方向：{user_seed}")

        lines.append("请保留用户已给出的有效姓名、身份、目标、地点和线索含义，只补齐缺失的 NPC 设定、隐藏行动者、地图对象、发现路线、真相链和开场章节目标。")
        return "\n".join(lines)

    def merge_bootstrap_with_manual(self, result: BootstrapResult, manual_world: Dict[str, Any]) -> None:
        report = {
            "preserved": {"world_bible_fields": [], "characters": [], "locations": [], "clues": []},
            "generated": {"characters": [], "locations": [], "clues": []},
            "repaired": [],
        }

        self._merge_bible(result, manual_world["world_bible"], report)
        self._merge_locations(result, manual_world["map"], report)
        self._merge_characters(result, manual_world["characters"], report)
        self._merge_clues(result, manual_world["clues"], report)
        self._ensure_required_cast(result, report)
        self._repair_references(result, report)

        result.title = result.world_bible.get("title", result.title or result.world_id)
        result.chapter_goal = self.bootstrapper._build_chapter_goal(result.opening_chapter_plan, result.characters) if result.opening_chapter_plan else result.chapter_goal
        result.fusion_report = report

    def _merge_bible(self, result: BootstrapResult, manual_bible: Dict[str, Any], report: Dict[str, Any]) -> None:
        result.world_bible["world_id"] = result.world_id
        for key in ["title", "genre", "tone", "era"]:
            if self._meaningful(manual_bible.get(key)):
                result.world_bible[key] = manual_bible[key]
                report["preserved"]["world_bible_fields"].append(key)

        for key in ["rules", "themes"]:
            merged = []
            for value in manual_bible.get(key, []):
                if self._meaningful(value) and value not in merged:
                    merged.append(value)
            for value in result.world_bible.get(key, []):
                if self._meaningful(value) and value not in merged:
                    merged.append(value)
            result.world_bible[key] = merged
            if merged:
                report["preserved"]["world_bible_fields"].append(key)

        result.world_bible.pop("draft", None)
        result.world_bible.pop("draft_reason", None)

    def _merge_locations(self, result: BootstrapResult, manual_locations: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        by_id = {loc.location_id: loc for loc in result.map}
        merged: List[BootstrapLocation] = []
        used = set()

        for manual in manual_locations:
            loc_id = manual.get("id")
            if not self._meaningful(loc_id):
                continue
            if self._is_placeholder_location(manual):
                report["repaired"].append(f"dropped_placeholder_location:{loc_id}")
                continue
            generated = by_id.get(loc_id)
            loc = generated.model_copy(deep=True) if generated else BootstrapLocation(
                location_id=loc_id,
                name=manual.get("name") or loc_id,
                public_description=manual.get("public_description") or manual.get("description") or "",
            )
            if self._meaningful(manual.get("name")):
                loc.name = manual["name"]
            if self._meaningful(manual.get("public_description")):
                loc.public_description = manual["public_description"]
            if isinstance(manual.get("connected_to"), list) and manual["connected_to"]:
                loc.connected_to = [x for x in manual["connected_to"] if self._meaningful(x)]
            if isinstance(manual.get("danger_level"), int):
                loc.danger_level = manual["danger_level"]
            if manual.get("objects"):
                loc.objects = [self._object_to_bootstrap(obj, loc.location_id) for obj in manual["objects"]]
            merged.append(loc)
            used.add(loc.location_id)
            report["preserved"]["locations"].append(loc.location_id)

        for loc in result.map:
            if loc.location_id not in used:
                merged.append(loc)
                report["generated"]["locations"].append(loc.location_id)

        result.map = merged

    def _merge_characters(self, result: BootstrapResult, manual_characters: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        by_id = {c.character_id: c for c in result.characters}
        by_name_role = {(c.name, c.role): c for c in result.characters}
        merged: List[CharacterWithAgent] = []
        used = set()

        for manual in manual_characters:
            char_id = manual.get("id")
            if not self._meaningful(char_id) or char_id in used:
                if self._meaningful(char_id):
                    report["repaired"].append(f"deduplicated_character:{char_id}")
                continue
            generated = by_id.get(char_id) or by_name_role.get((manual.get("name"), manual.get("role")))
            character = generated.model_copy(deep=True) if generated else CharacterWithAgent(
                character_id=char_id,
                name=manual.get("name") or char_id,
                role=manual.get("role") or "npc",
            )
            self._apply_manual_character(character, manual)
            merged.append(character)
            used.add(character.character_id)
            report["preserved"]["characters"].append(character.character_id)

        for character in result.characters:
            if character.character_id not in used:
                merged.append(character)
                report["generated"]["characters"].append(character.character_id)

        result.characters = merged

    def _merge_clues(self, result: BootstrapResult, manual_clues: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        by_id = {c.clue_id: c for c in result.clues}
        merged: List[BootstrapClue] = []
        used = set()

        for manual in manual_clues:
            clue_id = manual.get("id")
            if not self._meaningful(clue_id):
                continue
            generated = by_id.get(clue_id)
            routes = [self._route_to_bootstrap(route) for route in manual.get("discover_routes", []) if isinstance(route, dict)]
            if not generated and not self._meaningful(manual.get("content")) and not routes:
                report["repaired"].append(f"dropped_empty_clue:{clue_id}")
                continue
            clue = generated.model_copy(deep=True) if generated else BootstrapClue(
                clue_id=clue_id,
                title=manual.get("name") or clue_id,
                content=manual.get("content") or "",
            )
            if self._meaningful(manual.get("name")):
                clue.title = manual["name"]
            if self._meaningful(manual.get("content")):
                clue.content = manual["content"]
            if self._meaningful(manual.get("truth_level")):
                clue.level = manual["truth_level"]
            if routes:
                clue.discover_routes = routes
            elif generated and not clue.discover_routes:
                report["repaired"].append(f"kept_generated_route_required:{clue_id}")
            elif not generated:
                report["repaired"].append(f"dropped_clue_without_route:{clue_id}")
                continue
            merged.append(clue)
            used.add(clue.clue_id)
            report["preserved"]["clues"].append(clue.clue_id)

        for clue in result.clues:
            if clue.clue_id not in used:
                merged.append(clue)
                report["generated"]["clues"].append(clue.clue_id)

        result.clues = merged

    def _ensure_required_cast(self, result: BootstrapResult, report: Dict[str, Any]) -> None:
        protagonists = [c for c in result.characters if c.role == "protagonist"]
        if not protagonists and result.characters:
            first_visible = next((c for c in result.characters if c.visibility == "visible"), result.characters[0])
            first_visible.role = "protagonist"
            first_visible.active_agent = True
            first_visible.visibility = "visible"
            report["repaired"].append(f"promoted_protagonist:{first_visible.character_id}")
        for protagonist in [c for c in result.characters if c.role == "protagonist"]:
            if not protagonist.active_agent:
                protagonist.active_agent = True
                report["repaired"].append(f"activated_protagonist:{protagonist.character_id}")
            if protagonist.visibility != "visible":
                protagonist.visibility = "visible"
                report["repaired"].append(f"made_protagonist_visible:{protagonist.character_id}")

    def _repair_references(self, result: BootstrapResult, report: Dict[str, Any]) -> None:
        if not result.map:
            return

        location_ids = {loc.location_id for loc in result.map}
        first_location = result.map[0].location_id
        object_ids_by_location = {loc.location_id: {obj.object_id for obj in loc.objects} for loc in result.map}
        first_object_by_location = {loc.location_id: (loc.objects[0].object_id if loc.objects else None) for loc in result.map}
        character_ids = {c.character_id for c in result.characters}

        for loc in result.map:
            before = list(loc.connected_to)
            loc.connected_to = [target for target in loc.connected_to if target in location_ids and target != loc.location_id]
            if before != loc.connected_to:
                report["repaired"].append(f"filtered_invalid_connections:{loc.location_id}")

        for character in result.characters:
            if character.active_agent and character.location_id not in location_ids:
                character.location_id = first_location
                report["repaired"].append(f"fixed_character_location:{character.character_id}")

        if result.parsed_seed and result.parsed_seed.cast_mode == "ensemble_survival" and "location_gate" in location_ids:
            opening_visible = [c for c in result.characters if c.active_agent and c.visibility == "visible" and c.location_id == "location_gate"]
            if len(opening_visible) < 3:
                candidates = [c for c in result.characters if c.active_agent and c.visibility == "visible" and c.location_id != "location_gate"]
                for character in candidates[:3 - len(opening_visible)]:
                    character.location_id = "location_gate"
                    report["repaired"].append(f"moved_opening_survivor_to_gate:{character.character_id}")

        for clue in result.clues:
            for route in clue.discover_routes:
                if route.location_id not in location_ids:
                    route.location_id = first_location
                    report["repaired"].append(f"fixed_route_location:{clue.clue_id}")
                if route.action in {"inspect", "search"}:
                    valid_objects = object_ids_by_location.get(route.location_id, set())
                    target = route.target or route.object_id
                    if target not in valid_objects:
                        fallback = first_object_by_location.get(route.location_id)
                        if fallback:
                            route.object_id = fallback
                            route.target = fallback
                            report["repaired"].append(f"fixed_route_object:{clue.clue_id}")
                    else:
                        route.object_id = target
                        route.target = target
                elif route.action in {"ask", "talk"} and route.target not in character_ids:
                    npc = next((c.character_id for c in result.characters if c.role not in {"protagonist", "missing_person"}), None)
                    if npc:
                        route.target = npc
                        report["repaired"].append(f"fixed_route_character:{clue.clue_id}")

    def _is_placeholder_location(self, location: Dict[str, Any]) -> bool:
        name = str(location.get("name") or "").strip().lower()
        description = str(location.get("public_description") or location.get("description") or "").strip().lower()
        has_meaningful_objects = any(self._meaningful(obj) for obj in location.get("objects") or [])
        return not has_meaningful_objects and (
            name in self.placeholders or description in self.placeholders
        )

    def _normalize_character(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        character = dict(raw)
        character["id"] = character.get("id") or character.get("character_id") or character.get("name")
        if character.get("id") == "char_protagonist" and not self._normalize_role(character.get("role")) == "protagonist":
            character["role"] = "protagonist"
        if character.get("traits") and not character.get("personality"):
            character["personality"] = {"traits": character.get("traits")}
        if character.get("backstory") and not character.get("background"):
            character["background"] = character.get("backstory")
        if character.get("location_id") and not character.get("initial_location"):
            character["initial_location"] = character.get("location_id")
        character.setdefault("role", "npc")
        return character

    def _normalize_location(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        location = dict(raw)
        location["id"] = location.get("id") or location.get("location_id") or location.get("name")
        location.setdefault("objects", [])
        return location

    def _normalize_clue(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        clue = dict(raw)
        clue["id"] = clue.get("id") or clue.get("clue_id") or clue.get("name")
        clue["truth_level"] = clue.get("truth_level") or clue.get("level") or "hidden_fact"
        return clue

    def _apply_manual_character(self, character: CharacterWithAgent, manual: Dict[str, Any]) -> None:
        if self._meaningful(manual.get("name")):
            manual_name = str(manual["name"])
            character.name = self._safe_character_name(manual_name, character)
        if self._meaningful(manual.get("role")):
            character.role = self._normalize_role(manual["role"])
        goals = manual.get("goals") or {}
        if isinstance(goals, dict):
            goal = goals.get("short_term") or goals.get("long_term")
            if self._meaningful(goal):
                character.goal = goal
        if self._meaningful(manual.get("background")):
            character.background = manual["background"]
        personality = manual.get("personality") or {}
        if isinstance(personality, dict) and self._meaningful(personality.get("traits")):
            character.personality_traits = personality["traits"]
        for key in ["fears", "secrets", "known_facts", "suspicions", "inventory", "narrative_function"]:
            if self._meaningful(manual.get(key)):
                setattr(character, key, manual[key])
        if self._meaningful(manual.get("personal_stakes")):
            character.personal_stakes = manual["personal_stakes"]
        if self._meaningful(manual.get("initial_location")):
            character.location_id = manual["initial_location"]
        if isinstance(manual.get("active_agent"), bool):
            character.active_agent = manual["active_agent"]
        if self._meaningful(manual.get("visibility")):
            character.visibility = manual["visibility"]
        if isinstance(manual.get("skills"), dict) and manual["skills"]:
            character.skills = manual["skills"]
        if isinstance(manual.get("llm_temperature"), (int, float)):
            character.llm_temperature = float(manual["llm_temperature"])

    def _safe_character_name(self, name: str, character: CharacterWithAgent) -> str:
        if not self._is_placeholder_name(name):
            return name
        mapping = {
            "protagonist": "林砚",
            "missing_person": "顾行舟",
            "hidden_actor": "程疏影",
            "gatekeeper": "沈伯衡",
            "witness": "罗敏",
            "survivor": "许照",
        }
        return mapping.get(character.role, "梁既白")

    @staticmethod
    def _is_placeholder_name(name: str) -> bool:
        text = (name or "").strip()
        if not text:
            return True
        exact = {
            "主角", "阻碍者", "目击者", "隐藏行动者", "未露面的行动者", "神秘人", "NPC", "NPC1", "NPC2",
            "同行者甲", "同行者乙", "同行者丙", "知情者甲", "知情者乙", "目击者甲", "目击者乙",
            "被卷入的同行者", "持异议的同行者",
        }
        if text in exact:
            return True
        patterns = [r"^NPC\d*$", r"^同行者[甲乙丙丁]$", r"^知情者[甲乙丙丁]$", r"^目击者[甲乙丙丁]$", r".*同行者$", r".*行动者$", r".*目击者$", r".*知情人$"]
        return any(re.fullmatch(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _object_to_bootstrap(self, obj: Any, location_id: str) -> BootstrapLocationObject:
        if isinstance(obj, str):
            return BootstrapLocationObject(object_id=obj, object_type="inspectable_trace", description=obj, allowed_actions=["inspect"])
        object_id = obj.get("id") or obj.get("object_id") or obj.get("name") or f"{location_id}_object"
        return BootstrapLocationObject(
            object_id=object_id,
            object_type=obj.get("object_type") or obj.get("type") or "inspectable_trace",
            description=obj.get("description") or obj.get("name") or object_id,
            allowed_actions=obj.get("allowed_actions") or ["inspect"],
        )

    def _route_to_bootstrap(self, route: Dict[str, Any]) -> DiscoverRoute:
        action = self._normalize_action(route.get("action") or route.get("action_type"))
        target = route.get("target") or route.get("object_id")
        return DiscoverRoute(
            location_id=route.get("location_id") or "",
            object_id=target if action in {"inspect", "search"} else route.get("object_id"),
            target=target,
            action=action,
            difficulty=route.get("difficulty") or 1,
            required_skill=route.get("required_skill"),
            topic=route.get("topic"),
        )

    def _normalize_action(self, action: Any) -> str:
        mapping = {
            "调查": "inspect",
            "检查": "inspect",
            "搜查": "search",
            "搜索": "search",
            "询问": "ask",
            "对话": "talk",
            "交谈": "talk",
            "观察": "inspect",
        }
        return mapping.get(str(action or "").strip(), str(action or "inspect").strip() or "inspect")

    def _normalize_role(self, role: str) -> str:
        mapping = {
            "主角": "protagonist",
            "主人公": "protagonist",
            "失踪者": "missing_person",
            "隐藏反派": "hidden_actor",
            "NPC": "npc",
        }
        return mapping.get(role, role)

    def _meaningful(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            text = value.strip()
            return bool(text) and text.lower() not in self.placeholders
        if isinstance(value, list):
            return any(self._meaningful(item) for item in value)
        if isinstance(value, dict):
            return any(self._meaningful(item) for item in value.values())
        return True
