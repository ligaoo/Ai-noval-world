from __future__ import annotations

import json
import re
from typing import List, Optional

from .long_form_pacing import window_for_stage
from .models import BootstrapLocation, BootstrapLocationObject, ParsedSeed


class BootstrapMapGenerator:
    """
    第 8 章：自动生成最小地图
    必须保证 >= 5 个地点（DoD 第 3 条）
    """

    DEFAULT_CONNECTIONS = {
        "location_gate": ["location_frontdesk", "location_witness_point"],
        "location_frontdesk": ["location_gate", "location_hallway"],
        "location_hallway": ["location_frontdesk", "location_archive", "location_basement"],
        "location_archive": ["location_hallway"],
        "location_basement": ["location_hallway"],
        "location_witness_point": ["location_gate"],
        "location_inner": ["location_basement"],
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate(self, parsed: ParsedSeed, target_chapters: int = 30) -> List[BootstrapLocation]:
        if self.llm_client:
            locations = self._generate_with_llm(parsed)
            if locations:
                return locations

        core = parsed.core_location or "核心地点"
        spec = [
            ("location_gate", f"{core}入口", "entrance"),
            ("location_frontdesk", f"{core}前区", "interior"),
            ("location_hallway", f"{core}内部通道", "interior"),
            ("location_archive", f"{core}记录室", "archive"),
            ("location_basement", f"{core}深处入口", "danger_zone"),
            ("location_witness_point", f"{core}外围观察点", "external_witness_location"),
            ("location_inner", f"{core}隐藏隔间", "hidden"),
        ]

        return [
            BootstrapLocation(
                location_id=loc_id,
                name=name,
                type=loc_type,
                connected_to=self.DEFAULT_CONNECTIONS.get(loc_id, []),
                available_actions=self._actions_for(loc_type),
                public_description=self._description_for(name, loc_type),
                objects=self._objects_for(loc_id, core),
                danger_level=self._danger_for(loc_type),
                reveal_stage=self._stage_for(loc_type),
                recommended_chapter_range=window_for_stage(target_chapters, self._stage_for(loc_type)),
                narrative_function=self._narrative_function_for(loc_type),
                unlock_condition=self._unlock_condition_for(loc_type),
                associated_threads=self._threads_for(loc_type),
            )
            for loc_id, name, loc_type in spec
        ]

    def _generate_with_llm(self, parsed: ParsedSeed) -> Optional[List[BootstrapLocation]]:
        system = "你是可运行地图生成器，必须返回 JSON object，不要输出额外解释。"
        user = f"""
请基于 ParsedSeed 生成最小可运行地图。

ParsedSeed:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

硬性要求：
- 返回 JSON object，格式为 {{"locations": [...]}}，数组中每项字段：location_id, name, type, connected_to, available_actions, public_description, objects, danger_level。
- 必须包含这些 location_id：location_gate, location_frontdesk, location_hallway, location_archive, location_basement, location_witness_point, location_inner。
- 必须包含对象：obj_gate_lock 位于 location_gate；obj_frontdesk_drawer 位于 location_frontdesk；obj_fresh_footprints 位于 location_hallway；obj_missing_file 位于 location_archive。
- 名称和描述必须从 ParsedSeed 的 core_location、story_type、cast_mode 推导；不要固定成医院、病案室、小卖部、前台钥匙。
"""
        try:
            resp = self.llm_client.chat_json(system=system, user=user, temperature=0.45)
            data = resp.parsed_json
            if not data:
                text = resp.text.strip()
                if "```json" in text:
                    text = re.sub(r"```json\s*", "", text)
                    text = re.sub(r"\s*```", "", text)
                data = json.loads(text)
            if isinstance(data, dict):
                data = data.get("locations")
            if not isinstance(data, list):
                return None
            locations = [BootstrapLocation(**item) for item in data]
            expected = {
                "location_gate", "location_frontdesk", "location_hallway", "location_archive",
                "location_basement", "location_witness_point", "location_inner",
            }
            return locations if expected.issubset({loc.location_id for loc in locations}) else None
        except Exception:
            return None

    def _actions_for(self, loc_type: str) -> List[str]:
        if loc_type == "entrance":
            return ["observe", "inspect", "talk", "move"]
        if loc_type == "archive":
            return ["inspect", "search"]
        if loc_type == "external_witness_location":
            return ["talk", "ask", "observe"]
        if loc_type == "danger_zone":
            return ["observe", "inspect", "move"]
        return ["observe", "inspect", "search", "move"]

    def _description_for(self, name: str, loc_type: str) -> str:
        if loc_type == "entrance":
            return f"{name}：连接外部与核心区域的边界，状态与表面印象并不完全一致。"
        if loc_type == "archive":
            return f"{name}：保存着旧记录或遗留信息，部分痕迹显示近期有人接触过。"
        if loc_type == "external_witness_location":
            return f"{name}：位于核心区域外围，能提供不同角度的观察。"
        if loc_type == "danger_zone":
            return f"{name}：再往里风险明显升高，环境反馈也更不稳定。"
        if loc_type == "hidden":
            return f"{name}：不在普通路径上，只会通过痕迹和后果影响可见角色。"
        return f"{name}：可探索区域，细节里残留着尚未解释的变化。"

    def _objects_for(self, loc_id: str, core: str) -> List[BootstrapLocationObject]:
        objects: List[BootstrapLocationObject] = []
        if loc_id == "location_gate":
            objects.append(BootstrapLocationObject(
                object_id="obj_gate_lock",
                object_type="inspectable_trace",
                description=f"{core}入口处的边界痕迹，与长期无人接触的表象不一致。",
                allowed_actions=["inspect"],
            ))
        if loc_id == "location_frontdesk":
            objects.append(BootstrapLocationObject(
                object_id="obj_frontdesk_drawer",
                object_type="searchable_container",
                description="一个可搜索的遗留容器，里面可能压着推进下一步行动的线索物。",
                allowed_actions=["search", "inspect"],
            ))
        if loc_id == "location_hallway":
            objects.append(BootstrapLocationObject(
                object_id="obj_fresh_footprints",
                object_type="trace",
                description="一组近期留下的行动痕迹，方向避开了最直接的安全路径。",
                allowed_actions=["inspect"],
            ))
        if loc_id == "location_archive":
            objects.append(BootstrapLocationObject(
                object_id="obj_missing_file",
                object_type="searchable_container",
                description="保存记录的位置出现缺口，像是有信息被取走或替换。",
                allowed_actions=["search", "inspect"],
            ))
        return objects

    def _danger_for(self, loc_type: str) -> int:
        return {
            "entrance": 1,
            "interior": 1,
            "archive": 2,
            "danger_zone": 4,
            "external_witness_location": 0,
            "hidden": 3,
        }.get(loc_type, 1)

    @staticmethod
    def _stage_for(loc_type: str) -> str:
        return {
            "entrance": "surface",
            "interior": "surface",
            "external_witness_location": "partial",
            "archive": "partial",
            "danger_zone": "major",
            "hidden": "truth",
        }.get(loc_type, "surface")

    @staticmethod
    def _narrative_function_for(loc_type: str) -> str:
        return {
            "entrance": "建立异常边界与第一处可验证痕迹",
            "interior": "承接首章调查并制造行动选择",
            "external_witness_location": "提供外部证词或误导性解释",
            "archive": "承载中段证据链与规则矛盾",
            "danger_zone": "推进重大反转和代价确认",
            "hidden": "承载最终真相或源头证据",
        }.get(loc_type, "推进调查")

    @staticmethod
    def _unlock_condition_for(loc_type: str) -> str:
        return {
            "danger_zone": "至少确认一条 partial 阶段规则线索后才能实体进入",
            "hidden": "truth 阶段前只能提及或远观，不能实体进入",
        }.get(loc_type, "可在对应 reveal_stage 内进入")

    @staticmethod
    def _threads_for(loc_type: str) -> List[str]:
        return {
            "entrance": ["thread_recent_entry", "thread_shared_survival_rule"],
            "interior": ["thread_recent_entry"],
            "external_witness_location": ["thread_hidden_actor_trace"],
            "archive": ["thread_supernatural", "thread_core_motif"],
            "danger_zone": ["thread_hidden_actor_trace", "thread_supernatural"],
            "hidden": ["thread_supernatural"],
        }.get(loc_type, [])
