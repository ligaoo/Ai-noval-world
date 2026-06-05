from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from app.models.action import ActionCommand
from app.models.state import WorldState
from app.models.world import WorldConfig


@dataclass
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]


class ActionValidator:
    """
    V2.2 动作校验器。
    检查：枚举合法、target 存在、topic 合法、知识边界、move 联通性。
    """

    def __init__(self, world: WorldConfig):
        self.world = world
        self.allowed_actions = {"observe", "inspect", "search", "talk", "ask", "wait", "move"}
        self.environment_actions = {"observe", "inspect", "search", "wait"}

    def validate(
        self, action: ActionCommand, state: WorldState, agent_id: str
    ) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        # 1. 基础字段校验
        if action.action_type not in self.allowed_actions:
            errors.append(f"非法 action_type: {action.action_type}，允许：{self.allowed_actions}")

        agent_state = state.characters[agent_id]
        current_loc = self.world.map.get_location(agent_state.location_id)

        # 2. move / 非 move 动作目标校验
        if action.action_type == "move":
            self._validate_move(action, current_loc, errors, warnings)
        elif action.action_type in self.environment_actions:
            valid_targets = self._get_valid_targets(agent_state.location_id, state, agent_id)
            valid_targets.add(agent_state.location_id)
            if action.target and action.target not in valid_targets:
                errors.append(
                    f"target '{action.target}' 不在当前地点 '{agent_state.location_id}' 的合法目标列表：{valid_targets}"
                )
        else:
            # ask/talk 动作：target 必须是当前地点的 objects 或在场角色
            valid_targets = self._get_valid_targets(agent_state.location_id, state, agent_id)
            if action.target and action.target not in valid_targets:
                errors.append(
                    f"target '{action.target}' 不在当前地点 '{agent_state.location_id}' 的合法目标列表：{valid_targets}"
                )

        # 3. topic 合法性校验（仅 ask/talk）
        if action.action_type in {"ask", "talk"} and action.topic:
            topics_for_target = self.world.clues.all_topics_for_target(action.target)
            if action.topic not in topics_for_target:
                warnings.append(
                    f"topic '{action.topic}' 不在 target '{action.target}' 的可问列表，可能得不到有效信息"
                )

        # 4. 知识边界校验：不得引用未发现线索的具体内容
        discovered = {fact_id for fact_id, is_discovered in state.world.discovered_facts.items() if is_discovered}
        for clue in self.world.clues.clues:
            if clue.id not in discovered:
                clue_text = (clue.content or "").lower()
                action_text = (
                    f"{action.intent} {action.method} {action.dialogue or ''} {action.expected_gain or ''}"
                ).lower()
                if clue_text and clue_text in action_text:
                    errors.append(
                        f"Agent 引用了未发现的线索内容（知识边界违规）：{clue.id}"
                    )

        # 5. 私密披露兜底校验：低信任/高不确定关系下不得 exact match 暴露受保护私人信息
        self._validate_private_disclosure(action, state, agent_id, errors, warnings)

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    @staticmethod
    def _disclosure_policy(profile) -> Dict[str, Any]:
        policy = dict(getattr(profile, "disclosure_policy", {}) or {})
        return {
            "min_trust_for_secret_disclosure": policy.get("min_trust_for_secret_disclosure", 5),
            "max_suspicion_for_secret_disclosure": policy.get("max_suspicion_for_secret_disclosure", 2),
            "max_hostility_for_secret_disclosure": policy.get("max_hostility_for_secret_disclosure", 1),
            "require_relationship_evidence": policy.get("require_relationship_evidence", True),
            "private_fields": policy.get("private_fields", []),
        }

    @classmethod
    def _private_facts_for_profile(cls, profile) -> List[str]:
        policy = cls._disclosure_policy(profile)
        facts: List[str] = []
        facts.extend([secret for secret in getattr(profile, "secrets", []) if secret])
        for value in [
            getattr(profile, "private_motive", ""),
            getattr(profile, "withheld_information", ""),
        ]:
            if value:
                facts.append(value)
        if "background" in policy["private_fields"] and getattr(profile, "background", ""):
            facts.append(profile.background)
        return facts

    def _validate_private_disclosure(
        self,
        action: ActionCommand,
        state: WorldState,
        agent_id: str,
        errors: List[str],
        warnings: List[str],
    ) -> None:
        if action.action_type not in {"ask", "talk"}:
            return
        if not action.target or action.target not in state.characters:
            return
        if action.target == agent_id:
            return

        actor_profile = self.world.characters.get_character(agent_id)
        policy = self._disclosure_policy(actor_profile)
        rel = state.characters[agent_id].relationships.get(action.target)
        trust = rel.trust if rel else 0
        suspicion = rel.suspicion if rel else 0
        hostility = rel.hostility if rel else 0
        evidence = list(rel.evidence) if rel else []

        trust_ok = trust >= policy["min_trust_for_secret_disclosure"]
        suspicion_ok = suspicion <= policy["max_suspicion_for_secret_disclosure"]
        hostility_ok = hostility <= policy["max_hostility_for_secret_disclosure"]
        evidence_ok = (not policy["require_relationship_evidence"]) or bool(evidence) or trust_ok
        if trust_ok and suspicion_ok and hostility_ok and evidence_ok:
            return

        action_text = f"{action.intent} {action.method} {action.dialogue or ''} {action.expected_gain or ''}"
        for private_fact in self._private_facts_for_profile(actor_profile):
            if private_fact and private_fact in action_text:
                errors.append(
                    f"私人披露违规：{agent_id} 对低信任/高不确定目标 {action.target} 暴露了受保护私人信息"
                )
                return

    def _validate_move(
        self, action: ActionCommand, current_loc, errors: List[str], warnings: List[str]
    ) -> None:
        """校验 move 动作的合法性。"""
        target_location_id = action.target

        # 检查目标地点是否存在
        try:
            target_loc = self.world.map.get_location(target_location_id)
        except KeyError:
            errors.append(f"move 的目标地点不存在：{target_location_id}")
            return

        # 检查联通性
        if target_location_id not in current_loc.connected_to:
            errors.append(
                f"无法从 '{current_loc.id}' 移动到 '{target_location_id}'，两个地点不联通。"
                f"当前地点可移动到：{current_loc.connected_to}"
            )
            return

        # V2.2 暂不检查地点锁定状态，默认全解锁
        # if target_loc.locked:
        #     errors.append(f"目标地点 '{target_location_id}' 当前被锁定，无法进入")

        # 警告：移动到刚刚离开的地点（可能在原地打转）
        if hasattr(current_loc, "last_visited") and current_loc.last_visited == target_location_id:
            warnings.append(f"连续两次移动到同一地点 '{target_location_id}'，可能在原地打转")

    def _get_valid_targets(self, location_id: str, state: WorldState, exclude_agent_id: str) -> Set[str]:
        """获取指定地点的所有合法目标（objects + 在场角色）。"""
        loc = self.world.map.get_location(location_id)
        targets = {o.id for o in loc.objects}

        for obj_id, obj_data in state.world.objects.items():
            if obj_data.get("location_id") == location_id:
                targets.add(obj_id)

        # 在场角色
        for other_id, other_state in state.characters.items():
            if other_state.location_id == location_id and other_id != exclude_agent_id:
                targets.add(other_id)

        return targets
