from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LLMTrace:
    trace_id: str
    simulation_id: str
    tick: int
    agent_id: str
    purpose: str  # agent_decision / consistency_check / revise
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    success: bool
    retry_count: int
    from_cache: bool
    error: str = ""


class TraceService:
    """
    V2.1：LLM 调用 Trace 记录与成本统计。
    本地文件存储：outputs/{sim_id}/llm_traces.jsonl
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.trace_file = os.path.join(output_dir, "llm_traces.jsonl")
        self.traces: List[LLMTrace] = []
        self._total_cost = 0.0

    def record(self, trace: LLMTrace) -> None:
        self.traces.append(trace)
        self._total_cost += trace.cost_usd

        # 追加写入文件
        with open(self.trace_file, "a", encoding="utf-8") as f:
            line = json.dumps(
                {
                    "trace_id": trace.trace_id,
                    "simulation_id": trace.simulation_id,
                    "tick": trace.tick,
                    "agent_id": trace.agent_id,
                    "purpose": trace.purpose,
                    "model": trace.model,
                    "input_tokens": trace.input_tokens,
                    "output_tokens": trace.output_tokens,
                    "total_tokens": trace.total_tokens,
                    "cost_usd": trace.cost_usd,
                    "success": trace.success,
                    "retry_count": trace.retry_count,
                    "from_cache": trace.from_cache,
                    "error": trace.error,
                },
                ensure_ascii=False,
            )
            f.write(line + "\n")

    def get_summary(self) -> Dict[str, Any]:
        """返回本次模拟的 LLM 调用汇总。"""
        total_calls = len(self.traces)
        cached_calls = sum(1 for t in self.traces if t.from_cache)
        failed_calls = sum(1 for t in self.traces if not t.success)
        total_tokens = sum(t.total_tokens for t in self.traces)
        total_retries = sum(t.retry_count for t in self.traces)
        agent_decision_failures = sum(
            1 for t in self.traces if t.purpose == "agent_decision" and not t.success
        )
        max_retry_count = max((t.retry_count for t in self.traces), default=0)

        return {
            "total_calls": total_calls,
            "cached_calls": cached_calls,
            "failed_calls": failed_calls,
            "total_tokens": total_tokens,
            "cost_usd": round(self._total_cost, 6),
            "total_cost_usd": round(self._total_cost, 6),
            "total_retries": total_retries,
            "agent_decision_failures": agent_decision_failures,
            "max_retry_count": max_retry_count,
        }

    def save_summary(self) -> None:
        """保存汇总到 summary.json。"""
        summary = self.get_summary()
        summary_file = os.path.join(self.output_dir, "llm_summary.json")
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
