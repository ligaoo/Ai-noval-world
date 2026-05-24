from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set

from app.models.world import WorldConfig


@dataclass
class RuntimeWorldValidationResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RuntimeWorldValidator:
    PLACEHOLDER_TEXT = {
        "protagonist",
        "starting point",
        "mysterious place",
        "first clue",
        "this is the first clue to start your story.",
        "the place where the story begins.",
        "a place full of mysteries.",
        "new world",
        "add your world rules here",
        "theme 1",
        "theme 2",
    }

    def validate_for_formal_run(self, world: WorldConfig, world_dir: Path | None = None) -> RuntimeWorldValidationResult:
        issues: list[str] = []
        warnings: list[str] = []

        self._validate_bootstrap_metadata(world_dir, issues, warnings)
        self._validate_cast(world, issues)
        self._validate_map(world, issues)
        self._validate_clues(world, issues)
        self._validate_chapter_goal(world, issues)
        self._validate_placeholders(world, issues)

        return RuntimeWorldValidationResult(
            passed=not issues,
            issues=issues,
            warnings=warnings,
        )

    def _validate_bootstrap_metadata(self, world_dir: Path | None, issues: list[str], warnings: list[str]) -> None:
        if not world_dir:
            issues.append("缺少 world_dir，无法确认该 world 是否来自完整 Bootstrap 补全流程。")
            return

        result_file = world_dir / "bootstrap_result.json"
        manifest_file = world_dir / "bootstrap_manifest.json"
        if not result_file.exists():
            issues.append("缺少 bootstrap_result.json：正式模拟必须先通过模型补全世界并确认写盘。")
            return

        try:
            data = json.loads(result_file.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"bootstrap_result.json 无法解析：{exc}")
            return

        status = data.get("status")
        if status not in {"confirmed", "validated"}:
            issues.append(f"Bootstrap 状态不是 confirmed/validated，当前为：{status or 'missing'}。")

        validation = data.get("validation") or {}
        if validation.get("passed") is not True:
            issues.append("Bootstrap validation 未通过，不能启动正式模拟。")

        if not manifest_file.exists():
            warnings.append("缺少 bootstrap_manifest.json；建议重新确认候选以补齐审计文件。")

    def _validate_cast(self, world: WorldConfig, issues: list[str]) -> None:
        characters = world.characters.characters
        protagonists = [c for c in characters if c.role == "protagonist" and c.active_agent]
        visible_active_npcs = [
            c for c in characters
            if c.role not in {"protagonist", "missing_person"}
            and c.active_agent
            and c.visibility == "visible"
        ]
        hidden_actors = [c for c in characters if c.active_agent and c.visibility == "hidden"]

        if not protagonists:
            issues.append("缺少 active protagonist。")
        if len(visible_active_npcs) < 2:
            issues.append(f"正式模拟至少需要 2 个 visible active NPC，当前只有 {len(visible_active_npcs)} 个。")
        if not hidden_actors:
            issues.append("正式模拟至少需要 1 个 hidden active actor。")

    def _validate_map(self, world: WorldConfig, issues: list[str]) -> None:
        locations = world.map.locations
        location_ids = {loc.id for loc in locations}
        if len(locations) < 5:
            issues.append(f"正式模拟至少需要 5 个地点，当前只有 {len(locations)} 个。")

        object_count = sum(len(loc.objects) for loc in locations)
        if object_count < 3:
            issues.append(f"正式模拟至少需要 3 个可交互地图对象，当前只有 {object_count} 个。")

        for loc in locations:
            for connected_id in loc.connected_to:
                if connected_id not in location_ids:
                    issues.append(f"地点 {loc.id} connected_to 指向不存在地点：{connected_id}。")

    def _validate_clues(self, world: WorldConfig, issues: list[str]) -> None:
        clues = world.clues.clues
        if len(clues) < 3:
            issues.append(f"正式模拟至少需要 3 个线索，当前只有 {len(clues)} 个。")

        location_ids = {loc.id for loc in world.map.locations}
        objects_by_location = {loc.id: {obj.id for obj in loc.objects} for loc in world.map.locations}
        all_object_ids = {obj_id for ids in objects_by_location.values() for obj_id in ids}
        character_ids = set(world.characters.ids())
        discoverable = 0

        for clue in clues:
            if not clue.discover_routes:
                issues.append(f"线索 {clue.id} 没有 discover_routes。")
                continue

            for route in clue.discover_routes:
                if not route.location_id:
                    issues.append(f"线索 {clue.id} 的 route {route.route_id} 缺少 location_id。")
                    continue
                if route.location_id not in location_ids:
                    issues.append(f"线索 {clue.id} 的 route {route.route_id} 指向不存在地点：{route.location_id}。")
                    continue

                if route.action_type in {"inspect", "search"}:
                    if route.target not in all_object_ids:
                        issues.append(f"线索 {clue.id} 的 route {route.route_id} target 不存在于地图对象：{route.target}。")
                    elif route.target not in objects_by_location.get(route.location_id, set()):
                        issues.append(f"线索 {clue.id} 的 route {route.route_id} target 不属于地点 {route.location_id}：{route.target}。")
                    else:
                        discoverable += 1
                elif route.action_type in {"ask", "talk"}:
                    if route.target not in character_ids:
                        issues.append(f"线索 {clue.id} 的 route {route.route_id} 询问目标角色不存在：{route.target}。")
                    else:
                        discoverable += 1
                else:
                    issues.append(f"线索 {clue.id} 的 route {route.route_id} 使用不支持的 action_type：{route.action_type}。")

        if discoverable < 3:
            issues.append(f"正式模拟至少需要 3 条可执行发现路线，当前只有 {discoverable} 条。")

    def _validate_chapter_goal(self, world: WorldConfig, issues: list[str]) -> None:
        if world.chapter_goal.pov not in set(world.characters.ids()):
            issues.append(f"chapter_goal.pov 不存在：{world.chapter_goal.pov}。")

        location_ids = {loc.id for loc in world.map.locations}
        for character in world.characters.characters:
            if character.active_agent and character.initial_location and character.initial_location not in location_ids:
                issues.append(f"角色 {character.id} 的 initial_location 不存在：{character.initial_location}。")

    def _validate_placeholders(self, world: WorldConfig, issues: list[str]) -> None:
        values: Set[str] = set()
        values.add(world.bible.world_id)
        values.add(world.bible.genre)
        values.add(world.bible.tone)
        values.add(world.bible.era)
        values.update(world.bible.rules)
        values.update(world.bible.themes)

        for character in world.characters.characters:
            self._add_placeholder_values(values, character.name)
            if isinstance(character.goals, dict):
                self._add_placeholder_values(values, character.goals.get("short_term", ""))
                self._add_placeholder_values(values, character.goals.get("long_term", ""))

        for loc in world.map.locations:
            values.add(loc.name)
            values.add(loc.public_description)
            for obj in loc.objects:
                values.add(obj.name)
                values.add(obj.description)

        for clue in world.clues.clues:
            values.add(clue.name)
            values.add(clue.content)

        placeholders = sorted(
            value for value in values
            if isinstance(value, str) and value.strip().lower() in self.PLACEHOLDER_TEXT
        )
        if placeholders:
            issues.append(f"检测到测试/占位内容，不能作为正式世界启动：{', '.join(placeholders)}。")

    def _add_placeholder_values(self, values: Set[str], value) -> None:
        if isinstance(value, str):
            values.add(value)
            return
        if isinstance(value, list):
            for item in value:
                self._add_placeholder_values(values, item)
            return
        if isinstance(value, dict):
            for item in value.values():
                self._add_placeholder_values(values, item)
