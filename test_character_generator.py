#!/usr/bin/env python
"""测试角色生成器"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.services.llm_character_generator import (
    LLMCharacterGenerator,
    CharacterGenerationRequest,
)


def test_fallback_generation():
    """测试回退生成模式（不依赖 LLM）"""
    print("=" * 60)
    print("测试角色生成器（回退模式）")
    print("=" * 60)

    generator = LLMCharacterGenerator(project_root)
    request = CharacterGenerationRequest(
        world_id="dark_city_001",
        count=3,
        genre="horror",
    )

    candidates = generator.generate(request)

    print(f"\n生成了 {len(candidates)} 个角色：\n")

    for i, c in enumerate(candidates, 1):
        print(f"--- 角色 {i} ---")
        print(f"  ID: {c.character_id}")
        print(f"  姓名: {c.name}")
        print(f"  角色定位: {c.role}")
        print(f"  代理类型: {c.agent_type}")
        print(f"  性格: {', '.join(c.traits)}")
        print(f"  技能: {c.skills}")
        print(f"  短期目标: {c.goals.get('short_term')}")
        print(f"  长期目标: {c.goals.get('long_term')}")
        print(f"  背景: {c.backstory[:50]}...")
        print()

    print("=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_fallback_generation()
