from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests


@dataclass
class LLMCost:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class LLMResponse:
    text: str
    parsed_json: Optional[Dict[str, Any]] = None
    cost: LLMCost = field(default_factory=LLMCost)
    from_cache: bool = False
    trace_id: str = ""


class OpenAICompatibleClient:
    """
    V2.1 强化版 OpenAI 兼容 Client。
    增加：调用缓存、trace、成本统计。
    """

    # 粗略成本表（单位 USD / 1M tokens）
    MODEL_PRICING = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._cache: Dict[str, LLMResponse] = {}  # 简单内存缓存

    @classmethod
    def from_env(cls) -> Optional["OpenAICompatibleClient"]:
        """从环境变量创建（兼容旧代码）"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return cls(api_key=api_key, base_url=base_url, model=model)

    @classmethod
    def from_config(cls, project_root=None) -> Optional["OpenAICompatibleClient"]:
        """从配置文件创建（V2.3 推荐）"""
        from app.config import Config
        cfg = Config(project_root)
        llm_cfg = cfg.get_llm_config()
        if not llm_cfg:
            return None
        return cls(api_key=llm_cfg.api_key, base_url=llm_cfg.base_url, model=llm_cfg.model)

    def _calc_cost(self, usage: Dict[str, int]) -> LLMCost:
        """根据 usage 计算成本。"""
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        pricing = self.MODEL_PRICING.get(self.model, {"input": 0.0, "output": 0.0})
        cost_usd = (input_tokens / 1_000_000 * pricing["input"]) + (
            output_tokens / 1_000_000 * pricing["output"]
        )

        return LLMCost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
        )

    def _make_cache_key(self, system: str, user: str, temperature: float) -> str:
        """生成缓存 key（只有 temperature=0 才缓存）。"""
        if temperature > 0.01:
            return ""
        raw = f"{self.model}:{system}:{user}:{temperature}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def chat(
        self, system: str, user: str, temperature: float = 0.2, use_cache: bool = True,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """
        调用 Chat Completions，返回纯文本。
        V2.3：支持普通文本模式，不强制 JSON。
        """
        cache_key = self._make_cache_key(system, user, temperature)
        if use_cache and cache_key and cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.from_cache = True
            return cached

        url = f"{self.base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format:
            payload["response_format"] = {"type": response_format}

        start_time = time.time()
        r = requests.post(url, headers=headers, json=payload, timeout=120)

        if r.status_code >= 400:
            try:
                error_detail = r.json()
            except:
                error_detail = r.text
            error_msg = (
                f"API 请求失败 (HTTP {r.status_code}):\n"
                f"  URL: {url}\n"
                f"  Model: {self.model}\n"
                f"  Prompt 长度: system={len(system)} chars, user={len(user)} chars\n"
                f"  错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}"
            )
            raise RuntimeError(error_msg)

        data = r.json()
        text = data["choices"][0]["message"]["content"]
        parsed = _try_parse_json(text)
        usage = data.get("usage", {})
        cost = self._calc_cost(usage)

        trace_id = f"llm_{int(start_time)}_{os.urandom(4).hex()}"
        resp = LLMResponse(
            text=text, parsed_json=parsed, cost=cost, from_cache=False, trace_id=trace_id
        )

        if cache_key and use_cache:
            self._cache[cache_key] = resp

        return resp

    def chat_json(
        self, system: str, user: str, temperature: float = 0.2, use_cache: bool = True
    ) -> LLMResponse:
        """
        调用 Chat Completions，要求模型返回 JSON。
        V2.3：注意！Deepseek API 要求 prompt 中必须包含 'json' 字样！
        """
        if "json" not in system.lower() and "json" not in user.lower():
            system = system + "\n⚠️ 请以 JSON 格式返回结果。"

        return self.chat(system, user, temperature, use_cache, response_format="json_object")


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    # 常见情况：模型用 ```json 包裹
    if text.startswith("```"):
        text = text.strip("`")
        lines = text.splitlines()
        if lines and lines[0].strip().lower() == "json":
            text = "\n".join(lines[1:])
    try:
        return json.loads(text)
    except Exception:
        return None
