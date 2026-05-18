#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5.1 角色专属 temperature 测试脚本
验证不同角色是否按照性格获得不同的 temperature 值
"""

import sys
import os
import io

# 修复 Windows 控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from pathlib import Path

project_root = Path(__file__).parent

# 导入模块
sys.path.insert(0, str(project_root))

from app.models.world import TraitTemperatureMapper, WorldConfig


def test_trait_mapper():
    """测试性格到温度的映射"""
    print("=" * 60)
    print("测试 1: 性格特征到 temperature 的映射")
    print("=" * 60)

    test_cases = [
        {"name": "冷静侦探", "personality": {"traits": ["冷静", "理智", "严谨"]}},
        {"name": "冲动凶手", "personality": {"traits": ["冲动", "疯狂", "暴躁"]}},
        {"name": "焦虑证人", "personality": {"traits": ["焦虑", "紧张", "犹豫"]}},
        {"name": "神秘老者", "personality": {"traits": ["神秘", "古怪", "深沉"]}},
        {"name": "普通人", "personality": {"traits": ["普通", "正常"]}},
    ]

    for case in test_cases:
        temp = TraitTemperatureMapper.infer_from_traits(case["personality"])
        print(f"  {case['name']:15s} -> temperature = {temp:.2f}")

    print()


def test_world_config():
    """测试世界配置中的角色 temperature 读取"""
    print("=" * 60)
    print("测试 2: 读取角色配置中的 temperature 字段")
    print("=" * 60)

    worlds_dir = project_root / "worlds" / "dark_city_001"
    chars_file = worlds_dir / "characters.json"

    if chars_file.exists():
        import json
        with open(chars_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        world_config = WorldConfig(
            bible={"world_id": "test", "title": "test"},
            map={"locations": []},
            characters=data,
            clues={"clues": []},
            chapter_goal={"goal": "test", "pov": "char_linzho"},
        )

        for char in world_config.characters.characters:
            temp = world_config.characters.get_llm_temperature(char.id)
            print(f"  {char.name} ({char.id}): temperature = {temp:.2f}")
            if char.llm_temperature is not None:
                print(f"    -> 手动设置值: {char.llm_temperature}")
            else:
                print(f"    -> 自动推导自性格: {char.personality.get('traits', [])}")

    print()


def test_preset_lookup():
    """测试预设角色类型的 temperature"""
    print("=" * 60)
    print("测试 3: 恐怖题材角色预设 temperature")
    print("=" * 60)

    for preset_name, temp in sorted(TraitTemperatureMapper.HORROR_CHARACTER_PRESETS.items()):
        bar_length = int(temp * 30)
        bar = "*" * bar_length
        print(f"  {preset_name:15s} | {temp:.2f} {bar}")

    print()


def main():
    print()
    print("Novel Simulator V5.1 - 角色专属 temperature 测试")
    print()

    test_trait_mapper()
    test_world_config()
    test_preset_lookup()

    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)
    print()
    print("提示:")
    print("  - temperature 越低 (0.1~0.3), 角色行为更稳定、理智")
    print("  - temperature 中等 (0.4~0.6), 角色行为平衡、自然")
    print("  - temperature 越高 (0.7~0.9), 角色行为更情绪化、不可预测")
    print()


if __name__ == "__main__":
    main()
