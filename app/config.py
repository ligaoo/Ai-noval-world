from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None):
        """如果没有 python-dotenv，则尝试手动解析简单的 .env"""
        if not dotenv_path or not os.path.exists(dotenv_path):
            return
        try:
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
        except Exception:
            pass


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str


@dataclass
class RunConfig:
    mode: str
    ticks: int
    temperature: float


class Config:
    """配置管理器：优先从 .env 文件读取，其次环境变量"""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent

        # 加载 .env 文件
        env_file = project_root / ".env"
        load_dotenv(env_file)

        self.project_root = project_root

    def get_llm_config(self) -> Optional[LLMConfig]:
        """获取 LLM 配置，如果没有 API Key 返回 None"""
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            return None

        return LLMConfig(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        )

    def get_run_config(self) -> RunConfig:
        """获取运行配置"""
        return RunConfig(
            mode=os.getenv("DEFAULT_MODE", "scripted"),
            ticks=int(os.getenv("DEFAULT_TICKS", "15")),
            temperature=float(os.getenv("DEFAULT_TEMPERATURE", "0.2")),
        )

    def is_llm_available(self) -> bool:
        """检查 LLM 配置是否可用"""
        return self.get_llm_config() is not None
