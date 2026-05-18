from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class HorrorDevice:
    device_type: str
    description: str
    intensity_contribution: int
    typical_stage: str


class HorrorDeviceSelector:
    DEVICES = [
        HorrorDevice(
            device_type="sound_anomaly",
            description="声音异常，如不该有的脚步声、低语声、物品移动声",
            intensity_contribution=2,
            typical_stage="subtle_anomaly",
        ),
        HorrorDevice(
            device_type="object_displacement",
            description="物品位置变化，主角记得放在A处，实际在B处",
            intensity_contribution=2,
            typical_stage="subtle_anomaly",
        ),
        HorrorDevice(
            device_type="temperature_drop",
            description="温度骤降，突然感到寒意",
            intensity_contribution=1,
            typical_stage="subtle_anomaly",
        ),
        HorrorDevice(
            device_type="visual_illusion",
            description="视线错觉，眼角余光看到人影，转头却消失",
            intensity_contribution=2,
            typical_stage="subtle_anomaly",
        ),
        HorrorDevice(
            device_type="dream_fragment",
            description="梦境碎片，与现实重叠的模糊记忆",
            intensity_contribution=1,
            typical_stage="subtle_anomaly",
        ),
        HorrorDevice(
            device_type="space_mismatch",
            description="空间错位，房间比记忆中大或小，多了或少了门",
            intensity_contribution=4,
            typical_stage="clear_threat",
        ),
        HorrorDevice(
            device_type="repeating_sound",
            description="重复出现的声音，越来越清晰",
            intensity_contribution=3,
            typical_stage="clear_threat",
        ),
        HorrorDevice(
            device_type="recording_anomaly",
            description="录音或监控画面异常，拍到主角没看到的东西",
            intensity_contribution=4,
            typical_stage="clear_threat",
        ),
        HorrorDevice(
            device_type="brief_sighting",
            description="短暂目击不明存在，一闪而过",
            intensity_contribution=3,
            typical_stage="clear_threat",
        ),
        HorrorDevice(
            device_type="social_uncanny",
            description="熟人行为反常，像变了一个人",
            intensity_contribution=3,
            typical_stage="clear_threat",
        ),
        HorrorDevice(
            device_type="rule_validation",
            description="发现灵异规则的边界，主角尝试验证",
            intensity_contribution=5,
            typical_stage="rule_discovery",
        ),
        HorrorDevice(
            device_type="taboo_activation",
            description="禁忌触发，违反规则带来明显后果",
            intensity_contribution=6,
            typical_stage="rule_discovery",
        ),
        HorrorDevice(
            device_type="failed_attempt_consequence",
            description="错误尝试带来的代价，加深恐惧",
            intensity_contribution=5,
            typical_stage="rule_discovery",
        ),
        HorrorDevice(
            device_type="character_impact",
            description="重要角色受影响，增加主角压力",
            intensity_contribution=5,
            typical_stage="rule_discovery",
        ),
        HorrorDevice(
            device_type="past_echo",
            description="过去事件的回声，与当前情况重叠",
            intensity_contribution=4,
            typical_stage="rule_discovery",
        ),
        HorrorDevice(
            device_type="core_rule_reveal",
            description="核心规则揭示，主角明白真正的运作方式",
            intensity_contribution=7,
            typical_stage="truth_and_resolution",
        ),
        HorrorDevice(
            device_type="protagonist_past_confrontation",
            description="主角面对自己的过去，真相与个人相关",
            intensity_contribution=8,
            typical_stage="truth_and_resolution",
        ),
        HorrorDevice(
            device_type="final_taboo",
            description="终局禁忌，触及最根本的规则",
            intensity_contribution=9,
            typical_stage="truth_and_resolution",
        ),
        HorrorDevice(
            device_type="space_memory_overlap",
            description="空间与记忆重叠，现实和过去融合",
            intensity_contribution=8,
            typical_stage="truth_and_resolution",
        ),
        HorrorDevice(
            device_type="cost_choice",
            description="代价选择，主角必须做出牺牲",
            intensity_contribution=10,
            typical_stage="truth_and_resolution",
        ),
    ]

    def get_devices_for_stage(self, stage_id: str) -> List[HorrorDevice]:
        return [d for d in self.DEVICES if d.typical_stage == stage_id]

    def select_devices(
        self,
        stage_id: str,
        target_intensity: int,
        max_count: int = 3,
        exclude_used: Optional[List[str]] = None,
    ) -> List[HorrorDevice]:
        available = self.get_devices_for_stage(stage_id)

        if exclude_used:
            available = [d for d in available if d.device_type not in exclude_used]

        available.sort(key=lambda d: abs(d.intensity_contribution - (target_intensity / max_count)))
        return available[:max_count]

    def get_device_by_type(self, device_type: str) -> Optional[HorrorDevice]:
        for d in self.DEVICES:
            if d.device_type == device_type:
                return d
        return None

    def generate_scene_suggestion(
        self,
        devices: List[HorrorDevice],
        location: str = "",
        character: str = "主角",
    ) -> str:
        if not devices:
            return ""

        suggestions = []
        for device in devices:
            suggestions.append(f"{character}在{location}体验到: {device.description}")

        return "；".join(suggestions)
