from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any, Dict


class PromptTemplateService:
    def __init__(self, project_root: Path, world_id: str):
        self.project_root = project_root
        self.world_id = world_id
        self.template_dir = project_root / "app" / "templates" / "agent_sandbox"
        self.world_policy_file = project_root / "worlds" / world_id / "agent_sandbox_policy.json"

    def load_policy(self) -> Dict[str, Any]:
        policy = self._read_json(self.template_dir / "default_policy.json")
        world_policy = self._read_json(self.world_policy_file)
        return self._merge(policy, world_policy)

    def render(self, template_name: str, variables: Dict[str, Any]) -> str:
        path = self.template_dir / template_name
        text = path.read_text(encoding="utf-8")
        rendered_vars = {
            key: json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
            for key, value in variables.items()
        }
        return Template(text).safe_substitute(rendered_vars)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def _merge(cls, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = cls._merge(merged[key], value)
            else:
                merged[key] = value
        return merged
