from __future__ import annotations

from .models import BootstrapResult, ValidationIssue, ValidationResult


class BootstrapValidator:
    """
    第 21 章：bootstrap 校验
    覆盖 21.2 中的 12 条规则
    """

    def validate(self, result: BootstrapResult) -> ValidationResult:
        issues = []
        warnings = []

        # 1. 至少 1 个主角 active_agent
        protagonists = [c for c in result.characters if c.role == "protagonist" and c.active_agent]
        if not protagonists:
            issues.append(ValidationIssue(
                type="missing_protagonist",
                message="必须有至少 1 个 active_agent=true 的主角。",
            ))

        # 2. 至少 2 个 NPC active_agent
        npc_active = [
            c for c in result.characters
            if c.role not in ("protagonist", "missing_person") and c.active_agent
        ]
        if len(npc_active) < 2:
            issues.append(ValidationIssue(
                type="not_enough_active_agents",
                message=f"当前只有 {len(npc_active)} 个 NPC active_agent，至少需要 2 个。",
            ))

        # 3. 至少 1 个 hidden_actor
        hidden = [c for c in result.characters if c.visibility == "hidden" and c.active_agent]
        if not hidden:
            issues.append(ValidationIssue(
                type="missing_hidden_actor",
                message="至少需要 1 个 visibility=hidden 的隐藏行动者。",
            ))

        if result.parsed_seed and result.parsed_seed.cast_mode == "ensemble_survival":
            visible_active = [
                c for c in result.characters
                if c.active_agent and c.visibility == "visible"
            ]
            opening_visible = [
                c for c in visible_active
                if c.location_id == "location_gate"
            ]
            if len(visible_active) < 3:
                issues.append(ValidationIssue(
                    type="not_enough_visible_survivors",
                    message=f"群像生存故事至少需要 3 个可见 active 角色，当前只有 {len(visible_active)} 个。",
                ))
            if len(opening_visible) < 3:
                issues.append(ValidationIssue(
                    type="not_enough_opening_survivors",
                    message=f"群像生存故事开场至少需要 3 个可见 active 角色同场，当前 location_gate 只有 {len(opening_visible)} 个。",
                ))

        # 4. 至少 5 个 location
        if len(result.map) < 5:
            issues.append(ValidationIssue(
                type="not_enough_locations",
                message=f"当前只有 {len(result.map)} 个地点，至少需要 5 个。",
            ))

        # 5. 至少 3 个第一章可发现 clue
        if len(result.clues) < 3:
            issues.append(ValidationIssue(
                type="not_enough_clues",
                message=f"当前只有 {len(result.clues)} 个 clue，至少需要 3 个。",
            ))

        # 6. 每个 clue 必须有 discover_route
        for clue in result.clues:
            if not clue.discover_routes:
                issues.append(ValidationIssue(
                    type="missing_discover_route",
                    message=f"clue {clue.clue_id} 没有 discover_route。",
                ))

        # 7. 每个 discover_route 必须对应真实 location 和 object
        location_ids = {loc.location_id for loc in result.map}
        objects_by_location = {
            loc.location_id: {obj.object_id for obj in loc.objects}
            for loc in result.map
        }
        object_ids = {obj_id for ids in objects_by_location.values() for obj_id in ids}
        for loc in result.map:
            for connected_id in loc.connected_to:
                if connected_id not in location_ids:
                    issues.append(ValidationIssue(
                        type="invalid_map_connection",
                        message=f"location {loc.location_id} connected_to 不存在的 location: {connected_id}",
                    ))

        for clue in result.clues:
            for route in clue.discover_routes:
                if route.location_id not in location_ids:
                    issues.append(ValidationIssue(
                        type="invalid_route_location",
                        message=f"clue {clue.clue_id} 的 discover_route 指向不存在的 location: {route.location_id}",
                    ))
                if route.object_id and route.object_id not in object_ids:
                    issues.append(ValidationIssue(
                        type="invalid_route_object",
                        message=f"clue {clue.clue_id} 的 object_id {route.object_id} 不在地图对象列表中。",
                    ))
                if route.object_id and route.location_id in objects_by_location and route.object_id not in objects_by_location[route.location_id]:
                    issues.append(ValidationIssue(
                        type="route_object_location_mismatch",
                        message=f"clue {clue.clue_id} 的 object_id {route.object_id} 不属于 location {route.location_id}。",
                    ))

        character_ids = {c.character_id for c in result.characters}
        if result.chapter_goal.get("pov") not in character_ids:
            issues.append(ValidationIssue(
                type="invalid_chapter_goal_pov",
                message=f"chapter_goal.pov 不存在: {result.chapter_goal.get('pov')}",
            ))

        for c in result.characters:
            if c.active_agent and c.location_id and c.location_id not in location_ids:
                issues.append(ValidationIssue(
                    type="invalid_character_location",
                    message=f"角色 {c.character_id} 的初始地点不存在: {c.location_id}",
                ))

        # 8. ChapterGoal must_events 至少 1 条
        clue_ids = {clue.clue_id for clue in result.clues}
        if result.opening_chapter_plan:
            if not result.opening_chapter_plan.must_events:
                issues.append(ValidationIssue(
                    type="missing_must_events",
                    message="opening_chapter_plan 必须包含 must_events。",
                ))
            for clue_id in result.opening_chapter_plan.selected_clues:
                if clue_id not in clue_ids:
                    issues.append(ValidationIssue(
                        type="invalid_selected_clue",
                        message=f"opening_chapter_plan.selected_clues 引用了不存在的 clue: {clue_id}",
                    ))
            discoverable_selected = [
                clue_id for clue_id in result.opening_chapter_plan.selected_clues
                if any(c.clue_id == clue_id and c.discover_routes for c in result.clues)
            ]
            if len(discoverable_selected) < 3:
                issues.append(ValidationIssue(
                    type="not_enough_opening_discoverable_clues",
                    message=f"第一章 selected_clues 中可发现线索只有 {len(discoverable_selected)} 个，至少需要 3 个。",
                ))

        # 9. NarrativeWriter story_anchors 必须存在
        if not result.writer_story_anchors:
            issues.append(ValidationIssue(
                type="missing_story_anchors",
                message="必须生成 writer_story_anchors。",
            ))
        else:
            for field_name in ["title", "protagonist_name", "protagonist_goal", "main_question"]:
                if not getattr(result.writer_story_anchors, field_name, ""):
                    issues.append(ValidationIssue(
                        type="incomplete_story_anchors",
                        message=f"writer_story_anchors.{field_name} 不能为空。",
                    ))

        # 10. TruthChain 必须存在
        if not result.truth_chain:
            issues.append(ValidationIssue(
                type="missing_truth_chain",
                message="必须生成 truth_chain。",
            ))

        # 11. EvidenceGraph 必须存在
        if not result.evidence_graph:
            issues.append(ValidationIssue(
                type="missing_evidence_graph",
                message="必须生成 evidence_graph。",
            ))

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )
