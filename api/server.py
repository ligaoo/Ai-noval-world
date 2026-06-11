from __future__ import annotations

import json
import os
import re
import sys
import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# Windows 编码修复：强制使用 UTF-8，避免替换 stdout/stderr 导致 uvicorn logging 持有已关闭 stream
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.models.quality_controls import QualityControls, RewriteRequest

sys.path.append(str(Path(__file__).parent.parent))

app = FastAPI(title="Novel Simulator API", version="正式版V1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).parent.parent
WORLDS_DIR = PROJECT_ROOT / "worlds"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
LONG_RUNS_DIR = OUTPUTS_DIR / "long_runs"

# 模拟状态存储
running_simulations: Dict[str, Dict] = {}
BOOTSTRAPS_DIR = OUTPUTS_DIR / "bootstraps"
WORLD_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
LONG_RUN_ID_PATTERN = re.compile(r"^long_[A-Za-z0-9_-]+$")


def _safe_world_dir(world_id: str, must_exist: bool = True) -> Path:
    if not world_id or not WORLD_ID_PATTERN.fullmatch(world_id):
        raise HTTPException(status_code=400, detail="World ID 只能包含字母、数字、下划线和连字符")
    world_dir = WORLDS_DIR / world_id
    if must_exist and not world_dir.exists():
        raise HTTPException(status_code=404, detail="World not found")
    return world_dir


def _safe_long_run_dir(long_run_id: str, must_exist: bool = True) -> Path:
    if not long_run_id or not LONG_RUN_ID_PATTERN.fullmatch(long_run_id):
        raise HTTPException(status_code=400, detail="Long run ID 非法")
    long_run_dir = LONG_RUNS_DIR / long_run_id
    if must_exist and not long_run_dir.exists():
        raise HTTPException(status_code=404, detail="Long run not found")
    return long_run_dir


def _chapter_dir(long_run_dir: Path, chapter_no: int) -> Path:
    if chapter_no < 1:
        raise HTTPException(status_code=400, detail="chapter_no must be >= 1")
    return long_run_dir / f"ch_{chapter_no:03d}"


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_jsonl(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:]


def _read_long_run(long_run_id: str) -> Dict[str, Any]:
    long_run_dir = _safe_long_run_dir(long_run_id)
    data = _read_json(long_run_dir / "run.json")
    if not isinstance(data, dict):
        raise HTTPException(status_code=404, detail="Long run metadata not found")
    return data


def _write_long_run(long_run_dir: Path, data: Dict[str, Any]) -> None:
    data["updated_at"] = time.time()
    _write_json(long_run_dir / "run.json", data)


RUNTIME_ARTIFACTS = {
    "novel_plan": "novel_plan.json",
    "novel_state": "novel_state.json",
    "clue_ledger": "clue_ledger.json",
    "truth_state": "truth_state.json",
    "open_threads_state": "open_threads_state.json",
}


def _read_long_run_artifact(long_run_dir: Path, key: str, default: Any = None) -> Any:
    filename = RUNTIME_ARTIFACTS.get(key, key)
    return _read_json(long_run_dir / filename, default)


def _write_long_run_artifact(long_run_dir: Path, key: str, data: Any) -> None:
    filename = RUNTIME_ARTIFACTS.get(key, key)
    _write_json(long_run_dir / filename, data)


def _ensure_list(value: Any, wrapper_key: str = "") -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if wrapper_key and isinstance(value.get(wrapper_key), list):
            return value[wrapper_key]
        for key in ["items", "threads", "evidence", "truth_chain", "truth_chains", "truth_stages", "clues"]:
            if isinstance(value.get(key), list):
                return value[key]
    return []


def _unique_strings(values: List[Any]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def _as_list(value: Any, key: str) -> List[Dict]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        inner = value.get(key)
        return inner if isinstance(inner, list) else []
    return []


def _stable_id(prefix: str, value: str, index: int = 0) -> str:
    raw = re.sub(r"[^A-Za-z0-9_一-鿿-]+", "_", value or "item").strip("_")
    if not raw:
        raw = f"item_{index + 1}"
    return f"{prefix}_{raw[:32]}_{index + 1}"


def _normalize_character(character: Dict, index: int = 0) -> Dict:
    char_id = character.get("character_id") or character.get("id") or _stable_id("char", character.get("name", ""), index)
    traits = character.get("traits") or character.get("personality_traits") or character.get("personality", {}).get("traits") or []
    goals = character.get("goals") or {}
    if isinstance(character.get("goal"), str) and not goals:
        goals = {"short_term": character.get("goal", ""), "long_term": character.get("goal", "")}
    return {
        **character,
        "character_id": char_id,
        "id": character.get("id") or char_id,
        "traits": traits,
        "goals": goals,
        "initial_location": character.get("initial_location") or character.get("location_id") or "",
    }


def _normalize_location(location: Dict, index: int = 0) -> Dict:
    loc_id = location.get("location_id") or location.get("id") or _stable_id("loc", location.get("name", ""), index)
    return {**location, "location_id": loc_id, "id": location.get("id") or loc_id}


def _normalize_clue(clue: Dict, index: int = 0) -> Dict:
    clue_id = clue.get("clue_id") or clue.get("id") or _stable_id("clue", clue.get("name") or clue.get("title", ""), index)
    return {
        **clue,
        "clue_id": clue_id,
        "id": clue.get("id") or clue_id,
        "name": clue.get("name") or clue.get("title") or clue_id,
        "level": clue.get("level") or clue.get("truth_level") or "minor",
    }


def _load_world_payload(world_id: str) -> Dict:
    world_dir = _safe_world_dir(world_id)
    data = {"id": world_id}
    for name in [
        "world_bible",
        "characters",
        "map",
        "clues",
        "chapter_goal",
        "quality_policy",
        "plot_arcs",
        "character_arcs",
        "truth_chain",
        "evidence_graph",
        "open_threads",
        "writer_story_anchors",
        "opening_chapter_plan",
        "bootstrap_manifest",
        "bootstrap_result",
    ]:
        value = _read_json(world_dir / f"{name}.json")
        if value is not None:
            data[name] = value
    return data


def _world_summary(payload: Dict) -> Dict:
    return {
        "characters": len(_as_list(payload.get("characters"), "characters")),
        "locations": len(_as_list(payload.get("map"), "locations")),
        "clues": len(_as_list(payload.get("clues"), "clues")),
        "plot_arcs": len(_as_list(payload.get("plot_arcs"), "arcs")),
    }


def _extract_world_title(payload: Dict, world_id: str) -> str:
    bible = payload.get("world_bible") if isinstance(payload.get("world_bible"), dict) else {}
    return bible.get("title") or bible.get("name") or world_id


def _extract_world_theme(payload: Dict) -> str:
    bible = payload.get("world_bible") if isinstance(payload.get("world_bible"), dict) else {}
    themes = bible.get("themes") or []
    if isinstance(themes, list) and themes:
        return " / ".join(str(theme) for theme in themes[:3])
    return bible.get("theme") or bible.get("core_motif") or ""


def _build_act_plans(target_chapters: int) -> List[Dict[str, Any]]:
    first_end = max(1, round(target_chapters * 0.25))
    second_end = max(first_end + 1, round(target_chapters * 0.75)) if target_chapters > 2 else target_chapters
    second_end = min(second_end, target_chapters)
    acts = [
        {
            "act_id": "act_1_setup",
            "title": "开端与承诺",
            "chapter_range": [1, first_end],
            "function": "建立世界规则、主问题、核心人物压力和第一批可验证线索",
            "goals": ["打开主悬念", "建立读者承诺", "限定早期可揭示信息"],
            "must_not_reveal": ["最终真相", "幕后完整动机"],
        }
    ]
    if second_end > first_end:
        acts.append({
            "act_id": "act_2_complication",
            "title": "推进、误导与反转",
            "chapter_range": [first_end + 1, second_end],
            "function": "推进调查与关系冲突，制造误导，逐步确认局部真相",
            "goals": ["推进线索链", "积累悬念债", "制造阶段性反转"],
            "must_not_reveal": ["最终解释闭环"],
        })
    if second_end < target_chapters:
        acts.append({
            "act_id": "act_3_payoff",
            "title": "真相回收与收束",
            "chapter_range": [second_end + 1, target_chapters],
            "function": "回收核心线索、解释真相链、完成角色选择与结局承诺",
            "goals": ["回收关键悬念", "确认最终真相", "完成情感落点"],
            "must_not_reveal": [],
        })
    return acts


def _act_for_chapter(acts: List[Dict[str, Any]], chapter_no: int) -> Dict[str, Any]:
    for act in acts:
        start, end = act.get("chapter_range", [1, 1])
        if int(start) <= chapter_no <= int(end):
            return act
    return acts[-1] if acts else {}


def _chapter_function_for(chapter_no: int, target_chapters: int, act: Dict[str, Any]) -> str:
    if chapter_no == 1:
        return "开场章：建立世界规则、主角目标、第一条关键异常和结尾钩子"
    if chapter_no == target_chapters:
        return "收束章：回收主悬念、确认核心真相、完成角色选择和情感落点"
    if "setup" in act.get("act_id", ""):
        return "铺垫章：扩展世界规则、增加可验证线索、保持最终真相隐藏"
    if "complication" in act.get("act_id", ""):
        return "推进章：推进调查、制造误导或阶段反转、让角色关系产生变化"
    return "回收章：解释已铺垫线索、推进真相确认、准备或完成悬念回收"


def _chapter_function_for(chapter_no: int, target_chapters: int, act: Dict[str, Any]) -> str:
    if chapter_no == 1:
        return "开场章：建立世界规则、主角目标、第一条关键异常和结尾钩子"
    if chapter_no == target_chapters:
        return "收束章：回收主悬念、确认核心真相、完成角色选择和情感落点"
    if "setup" in act.get("act_id", ""):
        return "铺垫章：扩展世界规则、增加可验证线索、保持最终真相隐藏"
    if "complication" in act.get("act_id", ""):
        return "推进章：推进调查、制造误导或阶段反转、让角色关系产生变化"
    return "回收章：解释已铺垫线索、推进真相确认、准备或完成悬念回收"


def _truth_stage_for_chapter(truth_chain: Dict[str, Any], chapter_no: int, target_chapters: int) -> str:
    for step in (truth_chain or {}).get("reveal_steps", []) or []:
        start, end = step.get("chapter_range", [1, target_chapters])
        if int(start) <= chapter_no <= int(end):
            return step.get("stage") or "surface"
    ratio = chapter_no / max(target_chapters, 1)
    if ratio <= 0.18:
        return "surface"
    if ratio <= 0.5:
        return "partial"
    if ratio <= 0.82:
        return "major"
    return "truth"


def _items_for_chapter(items: List[Dict[str, Any]], chapter_no: int, stage: str, chapter_key: str = "planned_chapters", stage_key: str = "truth_relevance") -> List[Dict[str, Any]]:
    result = []
    for item in items or []:
        chapters = item.get(chapter_key) or item.get("allowed_reveal_chapters") or []
        item_stage = item.get(stage_key) or item.get("related_truth") or item.get("level")
        if chapter_no in [int(ch) for ch in chapters if str(ch).isdigit()] or item_stage == stage:
            result.append(item)
    return result


def _thread_id(item: Dict[str, Any]) -> str:
    return str(item.get("thread_id") or item.get("related_thread") or "").strip()


def _first_text(values: List[str]) -> str:
    return next((str(value) for value in values if str(value or "").strip()), "")


def _location_ids_for_stage(world_payload: Dict[str, Any], stage: str) -> List[str]:
    locations = (world_payload.get("map") or {}).get("locations") or []
    ids = [loc.get("id") or loc.get("location_id") for loc in locations if (loc.get("reveal_stage") or "surface") == stage]
    if ids:
        return [str(item) for item in ids if item]
    fallback = [loc.get("id") or loc.get("location_id") for loc in locations[:2]]
    return [str(item) for item in fallback if item]


def _forbidden_location_ids_for_stage(world_payload: Dict[str, Any], stage: str) -> List[str]:
    order = {"surface": 0, "partial": 1, "major": 2, "truth": 3}
    current = order.get(stage, 0)
    result = []
    for loc in (world_payload.get("map") or {}).get("locations") or []:
        loc_stage = loc.get("reveal_stage") or "surface"
        if order.get(loc_stage, 0) > current:
            loc_id = loc.get("id") or loc.get("location_id")
            if loc_id:
                result.append(str(loc_id))
    return result


def _character_arc_beats_for_stage(world_payload: Dict[str, Any], stage: str) -> List[str]:
    arcs = (world_payload.get("character_arcs") or {}).get("characters") or (world_payload.get("character_arcs") or {}).get("arcs") or []
    stage_map = {
        "surface": "avoidance",
        "partial": "doubt",
        "major": "confrontation",
        "truth": "acceptance",
    }
    target_stage = stage_map.get(stage, "avoidance")
    beats = []
    for arc in arcs[:3]:
        character_id = arc.get("character_id") or ""
        stages = arc.get("stages") or []
        match = next((item for item in stages if item.get("stage_id") == target_stage), None)
        if match:
            beats.append(f"{character_id}: {match.get('description') or match.get('name')}")
    return beats


def _forbidden_truths_for_stage(truth_chain: Dict[str, Any], current_stage: str) -> List[str]:
    order = {"surface": 0, "partial": 1, "major": 2, "truth": 3}
    current = order.get(current_stage, 0)
    result: List[str] = []
    for step in (truth_chain or {}).get("reveal_steps", []) or []:
        stage = step.get("stage") or "surface"
        if order.get(stage, 0) > current:
            result.extend(str(item) for item in step.get("allowed_information", []) or [])
            result.extend(str(item) for item in step.get("forbidden_information", []) or [])
    return list(dict.fromkeys(item for item in result if item))


def _build_novel_plan(long_run_id: str, run: Dict[str, Any], world_payload: Dict[str, Any]) -> Dict[str, Any]:
    target_chapters = int(run.get("target_chapters") or 1)
    target_words = int((world_payload.get("bootstrap_result") or {}).get("target_words") or 100000)
    acts = _build_act_plans(target_chapters)
    per_chapter_words = max(1000, round(target_words / max(1, target_chapters)))
    chapter_functions = []
    truth_chain = world_payload.get("truth_chain") or {}
    evidence_graph = world_payload.get("evidence_graph") or []
    clues = (world_payload.get("clues") or {}).get("clues") or []
    open_threads = world_payload.get("open_threads") or []
    if isinstance(open_threads, dict):
        open_threads = open_threads.get("threads") or open_threads.get("open_threads") or []
    all_thread_ids = [_thread_id(thread) for thread in open_threads if _thread_id(thread)]
    for chapter_no in range(1, target_chapters + 1):
        act = _act_for_chapter(acts, chapter_no)
        truth_stage = _truth_stage_for_chapter(truth_chain, chapter_no, target_chapters)
        planned_evidence_items = _items_for_chapter(evidence_graph, chapter_no, truth_stage)
        planned_clue_items = _items_for_chapter(clues, chapter_no, truth_stage, chapter_key="planned_chapters", stage_key="related_truth")
        if not planned_clue_items:
            planned_clue_items = [clue for clue in clues if clue.get("level") in {truth_stage, "surface"}][:2]
        planned_evidence = [item.get("evidence_id") for item in planned_evidence_items if item.get("evidence_id")][:3]
        planned_clues = [item.get("id") or item.get("clue_id") for item in planned_clue_items if item.get("id") or item.get("clue_id")][:3]
        related_threads = [
            thread for thread in [*[_thread_id(item) for item in planned_evidence_items], *[_thread_id(item) for item in planned_clue_items]]
            if thread
        ]
        if not related_threads:
            related_threads = all_thread_ids[:2]
        primary_thread = related_threads[0] if related_threads else ""
        secondary_threads = [thread for thread in related_threads[1:3] if thread != primary_thread]
        planned_locations = _location_ids_for_stage(world_payload, truth_stage)[:2]
        thread_payoffs = []
        if truth_stage == "truth" or chapter_no == target_chapters:
            thread_payoffs = related_threads[:2]
        allowed_reveals = [
            _first_text([item.get("real_meaning"), item.get("purpose"), item.get("title")])
            for item in planned_evidence_items[:3]
        ]
        chapter_functions.append({
            "chapter_id": f"ch_{chapter_no:03d}",
            "chapter_no": chapter_no,
            "target_words": per_chapter_words,
            "act_id": act.get("act_id", ""),
            "truth_stage": truth_stage,
            "chapter_function": _chapter_function_for(chapter_no, target_chapters, act),
            "primary_thread": primary_thread,
            "secondary_threads": secondary_threads,
            "required_events": [f"推进 {primary_thread}" if primary_thread else "推进本章主问题", *[f"发现线索 {clue}" for clue in planned_clues[:2]]],
            "planned_clues": planned_clues,
            "planned_evidence": planned_evidence,
            "planned_locations": planned_locations,
            "allowed_reveals": [text for text in allowed_reveals if text],
            "must_not_reveal": [*act.get("must_not_reveal", []), *_forbidden_truths_for_stage(truth_chain, truth_stage)],
            "thread_payoffs": thread_payoffs,
            "character_arc_beats": _character_arc_beats_for_stage(world_payload, truth_stage),
            "clue_budget": 2 if chapter_no == 1 else 3,
            "allowed_location_ids": planned_locations,
            "preferred_location_ids": planned_locations[:1],
            "forbidden_location_ids": _forbidden_location_ids_for_stage(world_payload, truth_stage),
        })
    return {
        "schema_version": 1,
        "long_run_id": long_run_id,
        "world_id": run.get("world_id"),
        "target_chapters": target_chapters,
        "target_words": target_words,
        "blueprint": {
            "novel_id": long_run_id,
            "title": _extract_world_title(world_payload, run.get("world_id", "")),
            "target_words": target_words,
            "target_chapters": target_chapters,
            "genre_id": run.get("genre_id") or "horror",
            "sub_genre": "",
            "theme": _extract_world_theme(world_payload),
            "acts": acts,
        },
        "chapter_functions": chapter_functions,
        "source": {
            "created_from": "world",
            "world_files": ["world_bible.json", "truth_chain.json", "evidence_graph.json", "open_threads.json", "clues.json"],
        },
    }


def _build_initial_novel_state(long_run_id: str, run: Dict[str, Any], novel_plan: Dict[str, Any]) -> Dict[str, Any]:
    target_chapters = int(run.get("target_chapters") or 1)
    target_words = int(novel_plan.get("target_words") or 100000)
    return {
        "schema_version": 1,
        "long_run_id": long_run_id,
        "world_id": run.get("world_id"),
        "status": run.get("status", "created"),
        "current_chapter": 0,
        "target_chapters": target_chapters,
        "current_words": 0,
        "target_words": target_words,
        "current_act": "",
        "progress_ratio": 0.0,
        "chapter_summaries": [],
        "active_reader_promises": [],
        "open_questions": [],
        "known_facts": [],
        "last_updated_at": time.time(),
    }


def _build_clue_ledger(long_run_id: str, world_payload: Dict[str, Any]) -> Dict[str, Any]:
    clues = []
    for index, clue in enumerate(_as_list(world_payload.get("clues"), "clues")):
        normalized = _normalize_clue(clue, index)
        clues.append({
            "clue_id": normalized.get("clue_id"),
            "name": normalized.get("name"),
            "level": normalized.get("level", "minor"),
            "truth_level": normalized.get("truth_level", normalized.get("level", "")),
            "status": "planned",
            "source": "world.clues",
            "planned_chapters": normalized.get("planned_chapters", []),
            "introduced_at_chapter": None,
            "confirmed_at_chapter": None,
            "related_thread": normalized.get("related_thread") or normalized.get("thread_id") or "",
            "related_truth": normalized.get("related_truth") or normalized.get("truth_id") or "",
            "evidence_ids": normalized.get("evidence_ids", []),
        })
    return {"schema_version": 1, "long_run_id": long_run_id, "clues": clues, "events": []}


def _normalize_evidence_item(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    evidence_id = item.get("evidence_id") or item.get("id") or _stable_id("ev", item.get("title") or item.get("label") or item.get("clue_id", ""), index)
    supports = item.get("supports_threads") or item.get("related_evidence_ids") or []
    if item.get("related_thread") and item.get("related_thread") not in supports:
        supports = [*supports, item.get("related_thread")]
    return {
        "evidence_id": evidence_id,
        "clue_id": item.get("clue_id", ""),
        "title": item.get("title") or item.get("label") or evidence_id,
        "type": item.get("type") or "clue",
        "supports_threads": supports,
        "proves": item.get("proves") or item.get("truth_relevance") or "",
        "opens": item.get("opens") or item.get("purpose") or "",
        "allowed_reveal_chapters": item.get("allowed_reveal_chapters", []),
        "can_mislead": bool(item.get("can_mislead", False)),
        "real_meaning": item.get("real_meaning", ""),
    }


def _build_truth_state(long_run_id: str, world_payload: Dict[str, Any]) -> Dict[str, Any]:
    truth_source = world_payload.get("truth_chain") or {}
    evidence_source = world_payload.get("evidence_graph") or {}
    truth_chains = []
    if isinstance(truth_source, dict) and truth_source.get("truth_id"):
        truth_chains.append({
            "truth_id": truth_source.get("truth_id"),
            "final_truth": truth_source.get("final_truth", ""),
            "reveal_stages": truth_source.get("reveal_steps", []),
        })
    else:
        for index, item in enumerate(_ensure_list(truth_source)):
            if isinstance(item, dict):
                truth_chains.append({
                    "truth_id": item.get("truth_id") or item.get("id") or item.get("stage") or _stable_id("truth", item.get("summary") or item.get("allowed_truth", ""), index),
                    "final_truth": item.get("final_truth") or item.get("summary") or item.get("allowed_truth") or "",
                    "reveal_stages": item.get("reveal_steps") or item.get("stages") or [item],
                })
    evidence = []
    for index, item in enumerate(_ensure_list(evidence_source, "evidence")):
        if isinstance(item, dict):
            evidence.append(_normalize_evidence_item(item, index))
    if isinstance(evidence_source, dict) and isinstance(evidence_source.get("nodes"), list):
        for index, node in enumerate(evidence_source.get("nodes") or []):
            if isinstance(node, dict):
                evidence.append(_normalize_evidence_item(node, len(evidence) + index))
    return {
        "schema_version": 1,
        "long_run_id": long_run_id,
        "truth_chains": truth_chains,
        "evidence": evidence,
        "revealed_truths": [],
        "forbidden_reveals": [],
        "events": [],
        "last_updated_at": time.time(),
    }


def _normalize_thread(item: Dict[str, Any], index: int) -> Dict[str, Any]:
    thread_id = item.get("thread_id") or item.get("id") or _stable_id("thread", item.get("question") or item.get("title", ""), index)
    return {
        "thread_id": thread_id,
        "question": item.get("question") or item.get("title") or thread_id,
        "status": item.get("status") or "open",
        "priority": item.get("priority") or item.get("importance") or 5,
        "opened_at_chapter": item.get("opened_at_chapter") or item.get("introduced_chapter"),
        "last_progress_chapter": None,
        "resolved_at_chapter": None,
        "related_clues": item.get("related_clues", []),
        "related_evidence": item.get("related_evidence_ids", []),
        "thread_type": item.get("thread_type", "mystery"),
        "payoff_hint": item.get("payoff_hint", ""),
    }


def _build_open_threads_state(long_run_id: str, world_payload: Dict[str, Any]) -> Dict[str, Any]:
    threads = []
    seen = set()
    for index, item in enumerate(_ensure_list(world_payload.get("open_threads"), "threads")):
        if isinstance(item, dict):
            thread = _normalize_thread(item, index)
            seen.add(thread["thread_id"])
            threads.append(thread)
    for clue in _as_list(world_payload.get("clues"), "clues"):
        thread_id = clue.get("related_thread") or clue.get("thread_id")
        if thread_id and thread_id not in seen:
            seen.add(thread_id)
            threads.append({
                "thread_id": thread_id,
                "question": str(thread_id),
                "status": "open",
                "priority": 4,
                "opened_at_chapter": None,
                "last_progress_chapter": None,
                "resolved_at_chapter": None,
                "related_clues": [clue.get("clue_id") or clue.get("id")],
                "related_evidence": [],
                "thread_type": "clue_thread",
                "payoff_hint": "",
            })
    return {"schema_version": 1, "long_run_id": long_run_id, "threads": threads, "events": [], "last_updated_at": time.time()}


def _initialize_novel_runtime_artifacts(long_run_dir: Path, run: Dict[str, Any]) -> Dict[str, bool]:
    world_payload = _load_world_payload(run["world_id"])
    novel_plan = _build_novel_plan(run["long_run_id"], run, world_payload)
    artifacts = {
        "novel_plan": novel_plan,
        "novel_state": _build_initial_novel_state(run["long_run_id"], run, novel_plan),
        "clue_ledger": _build_clue_ledger(run["long_run_id"], world_payload),
        "truth_state": _build_truth_state(run["long_run_id"], world_payload),
        "open_threads_state": _build_open_threads_state(run["long_run_id"], world_payload),
    }
    for key, value in artifacts.items():
        _write_long_run_artifact(long_run_dir, key, value)
    return {key: True for key in artifacts}


def _merge_unique(existing: List[Any], additions: List[Any]) -> List[str]:
    return _unique_strings([*(existing or []), *(additions or [])])


def _extract_text_length(chapter_dir: Path) -> int:
    draft = chapter_dir / "chapter_draft.md"
    if not draft.exists():
        return 0
    return len(draft.read_text(encoding="utf-8"))


def _update_novel_runtime_from_chapter(long_run_dir: Path, chapter_no: int, chapter_dir: Path, run: Dict[str, Any]) -> None:
    now = time.time()
    continuity = _read_json(chapter_dir / "chapter_continuity.json", {}) or {}
    novel_state = _read_long_run_artifact(long_run_dir, "novel_state", {}) or {}
    target_chapters = int(run.get("target_chapters") or novel_state.get("target_chapters") or 1)
    chapter_summary = continuity.get("chapter_delta_summary") or ""
    summaries = list(novel_state.get("chapter_summaries") or [])
    if chapter_summary:
        summaries = [item for item in summaries if item.get("chapter_no") != chapter_no]
        summaries.append({"chapter_no": chapter_no, "summary": chapter_summary})
    novel_state.update({
        "status": run.get("status", "idle"),
        "current_chapter": chapter_no,
        "target_chapters": target_chapters,
        "current_words": int(novel_state.get("current_words") or 0) + _extract_text_length(chapter_dir),
        "progress_ratio": round(chapter_no / max(1, target_chapters), 4),
        "chapter_summaries": sorted(summaries, key=lambda item: item.get("chapter_no", 0)),
        "active_reader_promises": _merge_unique(novel_state.get("active_reader_promises") or [], continuity.get("active_reader_promises") or []),
        "open_questions": _merge_unique(novel_state.get("open_questions") or [], continuity.get("new_questions") or []),
        "known_facts": _merge_unique(novel_state.get("known_facts") or [], continuity.get("new_facts") or []),
        "last_updated_at": now,
    })
    _write_long_run_artifact(long_run_dir, "novel_state", novel_state)

    threads_state = _read_long_run_artifact(long_run_dir, "open_threads_state", {"threads": [], "events": []}) or {"threads": [], "events": []}
    threads = list(threads_state.get("threads") or [])
    by_id = {thread.get("thread_id"): thread for thread in threads if thread.get("thread_id")}
    for index, text in enumerate(_unique_strings([*(continuity.get("open_threads") or []), *(continuity.get("active_reader_promises") or [])])):
        thread_id = _stable_id("thread", text, index)
        thread = by_id.get(thread_id)
        if not thread:
            thread = {
                "thread_id": thread_id,
                "question": text,
                "status": "open",
                "priority": 5,
                "opened_at_chapter": chapter_no,
                "last_progress_chapter": chapter_no,
                "resolved_at_chapter": None,
                "related_clues": [],
                "related_evidence": [],
                "thread_type": "runtime",
                "payoff_hint": "",
            }
            by_id[thread_id] = thread
            threads.append(thread)
        else:
            thread["last_progress_chapter"] = chapter_no
    events = list(threads_state.get("events") or [])
    for question in continuity.get("new_questions") or []:
        events.append({"chapter_no": chapter_no, "type": "new_question", "content": question, "created_at": now})
    threads_state.update({"threads": threads, "events": events, "last_updated_at": now})
    _write_long_run_artifact(long_run_dir, "open_threads_state", threads_state)

    clue_ledger = _read_long_run_artifact(long_run_dir, "clue_ledger", {"clues": [], "events": []}) or {"clues": [], "events": []}
    clue_events = list(clue_ledger.get("events") or [])
    for fact in continuity.get("new_facts") or []:
        clue_events.append({"chapter_no": chapter_no, "type": "fact_observed", "content": fact, "created_at": now})
    clue_ledger["events"] = clue_events
    clue_ledger["last_updated_at"] = now
    _write_long_run_artifact(long_run_dir, "clue_ledger", clue_ledger)

    truth_state = _read_long_run_artifact(long_run_dir, "truth_state", {"events": []}) or {"events": []}
    truth_events = list(truth_state.get("events") or [])
    for fact in continuity.get("new_facts") or []:
        truth_events.append({"chapter_no": chapter_no, "type": "revealed_or_suspected_fact", "content": fact, "created_at": now})
    truth_state["events"] = truth_events
    truth_state["last_updated_at"] = now
    _write_long_run_artifact(long_run_dir, "truth_state", truth_state)


def _save_world_payload(world_id: str, payload: Dict) -> Dict:
    world_dir = _safe_world_dir(world_id, must_exist=False)
    world_dir.mkdir(parents=True, exist_ok=True)

    if "world_bible" in payload:
        bible = dict(payload.get("world_bible") or {})
        bible["world_id"] = bible.get("world_id") or world_id
        _write_json(world_dir / "world_bible.json", bible)
    if "characters" in payload:
        chars = [_normalize_character(c, i) for i, c in enumerate(_as_list(payload.get("characters"), "characters"))]
        _write_json(world_dir / "characters.json", {"characters": chars})
    if "map" in payload:
        locations = [_normalize_location(l, i) for i, l in enumerate(_as_list(payload.get("map"), "locations"))]
        _write_json(world_dir / "map.json", {"locations": locations})
    if "clues" in payload:
        clues = [_normalize_clue(c, i) for i, c in enumerate(_as_list(payload.get("clues"), "clues"))]
        _write_json(world_dir / "clues.json", {"clues": clues})
    if "plot_arcs" in payload:
        _write_json(world_dir / "plot_arcs.json", {"arcs": _as_list(payload.get("plot_arcs"), "arcs")})
    if "character_arcs" in payload:
        _write_json(world_dir / "character_arcs.json", {"arcs": _as_list(payload.get("character_arcs"), "arcs")})
    for name in ["chapter_goal", "quality_policy", "truth_chain", "evidence_graph", "open_threads", "writer_story_anchors", "opening_chapter_plan", "bootstrap_manifest", "bootstrap_result"]:
        if name in payload:
            _write_json(world_dir / f"{name}.json", payload.get(name) or {})

    return _load_world_payload(world_id)


def _bootstrap_path(bootstrap_id: str) -> Path:
    if not re.fullmatch(r"boot_[A-Za-z0-9_-]+", bootstrap_id or ""):
        raise HTTPException(status_code=400, detail="Invalid bootstrap ID")
    return BOOTSTRAPS_DIR / f"{bootstrap_id}.json"


def _build_generated_character(world: Dict, index: int, role: str = "supporting") -> Dict:
    bible = world.get("world_bible") or {}
    locations = [_normalize_location(l, i) for i, l in enumerate(_as_list(world.get("map"), "locations"))]
    location = locations[index % len(locations)] if locations else {}
    genre = bible.get("genre") or bible.get("genre_id") or "通用题材"
    title = bible.get("title") or world.get("id") or "当前世界"
    name = f"{title}角色{index + 1}"
    return {
        "character_id": f"char_generated_{int(time.time() * 1000)}_{index}",
        "name": name,
        "role": role,
        "agent_type": "semi_agent_npc" if role == "npc" else "core_agent",
        "traits": ["与世界规则相关", "可推动剧情"],
        "goals": {
            "short_term": f"围绕《{title}》寻找新的行动线索",
            "long_term": f"在{genre}故事中形成稳定动机",
        },
        "skills": {"observation": 60 + index * 3, "social": 50, "logic": 55, "courage": 50},
        "initial_location": location.get("location_id", ""),
        "location_id": location.get("location_id", ""),
        "backstory": f"与{location.get('name', title)}有关的候选角色。",
    }


def _build_generated_clue(world: Dict, index: int, arc_id: str = "", level: str = "minor") -> Dict:
    bible = world.get("world_bible") or {}
    locations = [_normalize_location(l, i) for i, l in enumerate(_as_list(world.get("map"), "locations"))]
    location = locations[index % len(locations)] if locations else {}
    target = (location.get("objects") or [location.get("name") or "关键场景"])[0]
    if isinstance(target, dict):
        target = target.get("object_id") or target.get("name") or "关键物件"
    name = f"{location.get('name') or bible.get('title') or '世界'}线索{index + 1}"
    return {
        "clue_id": f"clue_generated_{int(time.time() * 1000)}_{index}",
        "name": name,
        "content": f"这个线索指向《{bible.get('title', '当前世界')}》中的未解问题，需要结合地点和角色动机继续验证。",
        "level": level,
        "arc_id": arc_id,
        "importance": 50 + index * 5,
        "discover_routes": [
            {
                "route_id": f"route_generated_{index}_0",
                "action_type": "investigate",
                "target": target,
                "location_id": location.get("location_id", ""),
                "difficulty": 45 + index * 5,
                "result": "发现与当前世界规则一致的异常细节。",
            }
        ],
    }


def _create_bootstrapper():
    from app.bootstrap.story_bootstrapper import StoryBootstrapper

    llm_client = None
    try:
        from app.config import Config
        from app.llm_client import OpenAICompatibleClient

        cfg = Config(PROJECT_ROOT)
        if cfg.is_llm_available():
            llm_client = OpenAICompatibleClient.from_config(PROJECT_ROOT)
    except Exception:
        llm_client = None
    return StoryBootstrapper(PROJECT_ROOT, llm_client=llm_client)


def _model_to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {k: _model_to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_model_to_jsonable(v) for v in value]
    return value


def _build_story_blueprint(result: Dict[str, Any]) -> Dict[str, Any]:
    bible = result.get("world_bible") or {}
    clues = result.get("clues") or []
    opening = result.get("opening_chapter_plan") or {}
    return {
        "world_rules": {
            "title": result.get("title") or bible.get("title"),
            "genre": bible.get("genre") or bible.get("genre_id"),
            "tone": bible.get("tone"),
            "rules": bible.get("rules") or [],
            "themes": bible.get("themes") or [],
            "timeline": bible.get("timeline") or [],
            "narrative_constraints": bible.get("narrative_constraints") or bible.get("forbidden_early_reveals") or [],
        },
        "truth_chain": result.get("truth_chain") or {},
        "evidence_graph": result.get("evidence_graph") or [],
        "clue_routes": [
            {
                "clue_id": clue.get("clue_id") or clue.get("id"),
                "title": clue.get("title") or clue.get("name"),
                "content": clue.get("content"),
                "level": clue.get("level") or clue.get("truth_level"),
                "related_thread": clue.get("related_thread"),
                "routes": clue.get("discover_routes") or [],
                "on_discovered": clue.get("on_discovered") or {},
            }
            for clue in clues
            if isinstance(clue, dict)
        ],
        "open_threads": result.get("open_threads") or [],
        "opening_chapter": {
            "chapter_goal": result.get("chapter_goal") or {},
            "plan": opening,
            "selected_clues": opening.get("selected_clues") or [],
            "must_events": opening.get("must_events") or [],
            "forbidden_reveals": opening.get("forbidden_reveals") or [],
            "ending_hook": opening.get("ending_hook") or result.get("chapter_goal", {}).get("ending_hook"),
        },
    }


def _persist_bootstrap_result(result: Dict[str, Any]) -> Dict[str, Any]:
    result.setdefault("summary", _bootstrap_summary(result))
    result["story_blueprint"] = _build_story_blueprint(result)
    _write_json(_bootstrap_path(result["bootstrap_id"]), result)
    return result


def _bootstrap_summary(result: Dict[str, Any]) -> Dict[str, int]:
    return {
        "characters": len(result.get("characters") or []),
        "locations": len(result.get("map") or []),
        "clues": len(result.get("clues") or []),
        "open_threads": len(result.get("open_threads") or []),
    }


def _build_bootstrap_result(request: Dict) -> Dict:
    from app.bootstrap.models import BootstrapSeed

    seed = (request.get("user_seed") or "").strip()
    if not seed:
        raise HTTPException(status_code=400, detail="请先输入故事种子")
    bootstrapper = _create_bootstrapper()
    result_model = bootstrapper.bootstrap(
        BootstrapSeed(
            user_seed=seed,
            target_genre=request.get("target_genre") or "generic",
            target_words=request.get("target_words") or 100000,
            target_chapters=request.get("target_chapters") or 30,
            auto_confirm=bool(request.get("auto_confirm")),
        ),
        world_id=request.get("world_id"),
    )
    result = _model_to_jsonable(result_model)
    result["status"] = "validated" if (result.get("validation") or {}).get("passed") else result.get("status", "validation_failed")
    result["user_seed"] = seed
    result["target_words"] = request.get("target_words")
    result["target_chapters"] = request.get("target_chapters") or 30
    return _persist_bootstrap_result(result)


class SimulationRequest(BaseModel):
    world_id: str = "dark_city_001"
    mode: str = "llm"
    version: str = "正式版V1"
    ticks: Optional[int] = None
    seed: int = 12345
    genre_id: str = "horror"
    target_chapters: int = 30
    chapter_no: int = 1
    quality_controls: QualityControls = Field(default_factory=QualityControls)


class NovelRunRequest(BaseModel):
    world_id: str
    mode: str = "llm"
    version: str = "正式版V1"
    ticks: Optional[int] = None
    seed: int = 12345
    genre_id: str = "horror"
    target_chapters: int = 30
    quality_controls: QualityControls = Field(default_factory=QualityControls)


@app.get("/")
async def root():
    return {
        "message": "Novel Simulator API 正式版V1",
        "features": [
            "Genre Abstraction Layer",
            "Horror Genre Pack",
            "Story Quality Evaluation",
        ]
    }


@app.get("/api/worlds")
async def get_worlds():
    worlds = []
    if WORLDS_DIR.exists():
        for world_dir in WORLDS_DIR.iterdir():
            if world_dir.is_dir():
                world_info = {"id": world_dir.name}
                bible = _read_json(world_dir / "world_bible.json", {})
                world_info["title"] = bible.get("title", world_dir.name)
                world_info["genre"] = bible.get("genre") or bible.get("genre_id", "generic")
                worlds.append(world_info)
    return {"worlds": worlds}


@app.get("/api/worlds/{world_id}")
async def get_world(world_id: str):
    return _load_world_payload(world_id)


@app.get("/api/simulations")
async def get_simulations():
    simulations = []
    if OUTPUTS_DIR.exists():
        for sim_dir in sorted(OUTPUTS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if sim_dir.is_dir() and sim_dir.name.startswith("sim_"):
                sim_info = {
                    "id": sim_dir.name,
                    "created_at": sim_dir.stat().st_ctime,
                }

                quality_dir = sim_dir / "quality_reports"
                if quality_dir.exists():
                    reports = list(quality_dir.glob("ch_*_quality.json"))
                    if reports:
                        with open(reports[0], "r", encoding="utf-8") as f:
                            quality = json.load(f)
                            sim_info["quality_score"] = quality.get("overall_score")
                            sim_info["grade"] = quality.get("grade")

                simulations.append(sim_info)
    return {"simulations": simulations}


@app.get("/api/simulations/{sim_id}")
async def get_simulation(sim_id: str):
    sim_dir = OUTPUTS_DIR / sim_id
    if not sim_dir.exists():
        raise HTTPException(status_code=404, detail="Simulation not found")

    sim_data = {"id": sim_id}

    state_file = sim_dir / "state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            sim_data["state"] = json.load(f)

    draft_file = sim_dir / "chapter_draft.md"
    if draft_file.exists():
        with open(draft_file, "r", encoding="utf-8") as f:
            sim_data["chapter_draft"] = f.read()

    plan_file = sim_dir / "chapter_plan.json"
    if plan_file.exists():
        with open(plan_file, "r", encoding="utf-8") as f:
            sim_data["chapter_plan"] = json.load(f)

    return sim_data


@app.get("/api/simulations/{sim_id}/quality")
async def get_simulation_quality(sim_id: str):
    sim_dir = OUTPUTS_DIR / sim_id
    quality_dir = sim_dir / "quality_reports"

    if not quality_dir.exists():
        return {"reports": []}

    reports = []
    for report_file in sorted(quality_dir.glob("ch_*_quality.json")):
        with open(report_file, "r", encoding="utf-8") as f:
            reports.append(json.load(f))

    return {"reports": reports}


def _run_simulation_sync(sim_id: str, request: SimulationRequest):
    """同步运行模拟（在后台线程中调用）"""
    try:
        from app.config import Config
        from app.models.world import WorldConfig
        from app.runner.simulation_runner import SimulationRunner

        cfg = Config(PROJECT_ROOT)
        if not cfg.is_llm_available():
            running_simulations[sim_id]["status"] = "failed"
            running_simulations[sim_id]["error"] = "LLM 未配置"
            return

        world_dir = WORLDS_DIR / request.world_id
        world = WorldConfig.from_directory(world_dir)

        # 正式版V1 统一使用：move+memory+LLM叙事+一致性修订
        forced_mode = "llm"
        forced_version = "正式版V1"

        runner = SimulationRunner(PROJECT_ROOT)
        result = runner.run(
            world=world,
            mode=forced_mode,
            ticks=request.ticks,
            seed=request.seed,
            genre_id=request.genre_id,
            target_chapters=request.target_chapters,
            chapter_no=request.chapter_no,
            version=forced_version,
            quality_controls=request.quality_controls,
        )

        running_simulations[sim_id]["status"] = "completed"
        running_simulations[sim_id]["simulation_id"] = result.simulation_id
        running_simulations[sim_id]["runtime_mode"] = forced_mode
        running_simulations[sim_id]["runtime_version"] = forced_version
        running_simulations[sim_id]["runtime_phase"] = forced_version
    except Exception as e:
        import traceback
        traceback.print_exc()
        running_simulations[sim_id]["status"] = "failed"
        running_simulations[sim_id]["error"] = str(e)


@app.post("/api/simulations/run")
async def run_simulation(request: SimulationRequest):
    try:
        from app.config import Config

        cfg = Config(PROJECT_ROOT)
        if not cfg.is_llm_available():
            raise HTTPException(
                status_code=400,
                detail="LLM 未配置。最终版本要求启用 LLM 叙事，请先配置 OPENAI_API_KEY。",
            )

        # 生成模拟 ID
        import time
        sim_id = f"sim_{int(time.time() * 1000)}"
        
        # 初始化模拟状态
        running_simulations[sim_id] = {
            "status": "running",
            "request": request.model_dump(),
            "error": None,
        }

        # 在后台线程中运行模拟
        thread = threading.Thread(target=_run_simulation_sync, args=(sim_id, request))
        thread.daemon = True
        thread.start()

        return {
            "success": True,
            "sim_id": sim_id,
            "message": "模拟已启动，请等待完成",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulations/{sim_id}/status")
async def get_simulation_status(sim_id: str):
    if sim_id not in running_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return running_simulations[sim_id]


@app.get("/api/simulations/{sim_id}/quality-controls")
async def get_simulation_quality_controls(sim_id: str):
    sim_dir = OUTPUTS_DIR / sim_id
    return _read_simulation_artifact(sim_dir, "quality_controls.json")


@app.get("/api/simulations/{sim_id}/reveal-budget")
async def get_simulation_reveal_budget(sim_id: str):
    sim_dir = OUTPUTS_DIR / sim_id
    return _read_simulation_artifact(sim_dir, "reveal_budget.json")


@app.get("/api/simulations/{sim_id}/continuity")
async def get_simulation_continuity(sim_id: str):
    sim_dir = OUTPUTS_DIR / sim_id
    return _read_simulation_artifact(sim_dir, "chapter_continuity.json")


@app.post("/api/simulations/{sim_id}/rewrite")
async def rewrite_simulation_draft(sim_id: str, request: RewriteRequest):
    sim_dir = OUTPUTS_DIR / sim_id
    if not sim_dir.exists():
        raise HTTPException(status_code=404, detail="Simulation not found")
    try:
        from app.config import Config
        from app.llm_client import OpenAICompatibleClient
        from app.models.world import WorldConfig
        from app.services.manual_rewrite_service import ManualRewriteService

        world_id = ""
        state_file = sim_dir / "state.json"
        if state_file.exists():
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            world_id = state_data.get("world_id") or state_data.get("world", {}).get("world_id", "")
        if not world_id:
            worlds = await get_worlds()
            world_id = (worlds.get("worlds") or [{}])[0].get("id", "dark_city_001")
        world = WorldConfig.from_directory(WORLDS_DIR / world_id)
        cfg = Config(PROJECT_ROOT)
        llm_client = OpenAICompatibleClient.from_config(PROJECT_ROOT) if cfg.is_llm_available() else None
        report = ManualRewriteService(world, sim_dir, llm_client).rewrite(request)
        return {"success": True, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _read_simulation_artifact(sim_dir: Path, filename: str):
    if not sim_dir.exists():
        raise HTTPException(status_code=404, detail="Simulation not found")
    path = sim_dir / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _quality_reports_for_dir(chapter_dir: Path) -> List[Dict[str, Any]]:
    quality_dir = chapter_dir / "quality_reports"
    if not quality_dir.exists():
        return []
    reports = []
    for report_file in sorted(quality_dir.glob("ch_*_quality.json")):
        reports.append(_read_json(report_file, {}))
    return reports


def _derive_chapter_status(chapter_dir: Path, fallback_status: str = "completed") -> Dict[str, Any]:
    run_status = _read_json(chapter_dir / "run_status.json", {})
    validation_status = run_status.get("validation_status")
    status = run_status.get("status") or fallback_status
    if validation_status == "failed":
        status = "completed_with_validation_errors"
    return {
        "status": status,
        "generation_status": run_status.get("generation_status"),
        "validation_status": validation_status,
        "validation_error_count": len(run_status.get("validation_errors") or []),
        "last_error": run_status.get("last_error"),
    }


def _attach_derived_chapter_statuses(long_run_dir: Path, data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(data)
    chapters = []
    has_validation_errors = False
    for chapter in data.get("chapters") or []:
        chapter_record = dict(chapter)
        chapter_no = int(chapter_record.get("chapter_no") or len(chapters) + 1)
        status_info = _derive_chapter_status(
            _chapter_dir(long_run_dir, chapter_no),
            str(chapter_record.get("status") or "completed"),
        )
        chapter_record.update(status_info)
        has_validation_errors = has_validation_errors or status_info.get("validation_status") == "failed"
        chapters.append(chapter_record)
    normalized["chapters"] = chapters
    if has_validation_errors and normalized.get("status") in {"idle", "completed"}:
        normalized["status"] = "completed_with_validation_errors" if normalized.get("status") == "completed" else "idle_with_validation_errors"
    return normalized


@app.get("/api/novel-runs")
async def list_novel_runs():
    runs = []
    if LONG_RUNS_DIR.exists():
        for long_run_dir in LONG_RUNS_DIR.iterdir():
            if not long_run_dir.is_dir():
                continue
            data = _read_json(long_run_dir / "run.json")
            if isinstance(data, dict):
                runs.append(_attach_derived_chapter_statuses(long_run_dir, data))
    runs.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or 0, reverse=True)
    return {"runs": runs}


@app.post("/api/novel-runs")
async def create_novel_run(request: NovelRunRequest):
    _safe_world_dir(request.world_id)
    if request.target_chapters < 1:
        raise HTTPException(status_code=400, detail="target_chapters must be >= 1")
    long_run_id = f"long_{int(time.time() * 1000)}"
    long_run_dir = _safe_long_run_dir(long_run_id, must_exist=False)
    long_run_dir.mkdir(parents=True, exist_ok=False)
    now = time.time()
    data = {
        "long_run_id": long_run_id,
        "world_id": request.world_id,
        "mode": request.mode,
        "version": request.version,
        "ticks": request.ticks,
        "seed": request.seed,
        "genre_id": request.genre_id,
        "target_chapters": request.target_chapters,
        "quality_controls": request.quality_controls.model_dump(),
        "status": "created",
        "created_at": now,
        "updated_at": now,
        "current_chapter": 0,
        "chapters": [],
        "error": None,
    }
    _write_json(long_run_dir / "run.json", data)
    artifacts = _initialize_novel_runtime_artifacts(long_run_dir, data)
    return {"success": True, "long_run_id": long_run_id, "run": data, "artifacts": artifacts}


@app.get("/api/novel-runs/{long_run_id}")
async def get_novel_run(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return _attach_derived_chapter_statuses(long_run_dir, _read_long_run(long_run_id))


@app.get("/api/novel-runs/{long_run_id}/plan")
async def get_novel_run_plan(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return _read_long_run_artifact(long_run_dir, "novel_plan", {})


@app.get("/api/novel-runs/{long_run_id}/state")
async def get_novel_run_state(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return _read_long_run_artifact(long_run_dir, "novel_state", {})


@app.get("/api/novel-runs/{long_run_id}/clue-ledger")
async def get_novel_run_clue_ledger(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return _read_long_run_artifact(long_run_dir, "clue_ledger", {})


@app.get("/api/novel-runs/{long_run_id}/truth-state")
async def get_novel_run_truth_state(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return _read_long_run_artifact(long_run_dir, "truth_state", {})


@app.get("/api/novel-runs/{long_run_id}/open-threads-state")
async def get_novel_run_open_threads_state(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return _read_long_run_artifact(long_run_dir, "open_threads_state", {})


@app.get("/api/novel-runs/{long_run_id}/runtime")
async def get_novel_run_runtime(long_run_id: str):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return {
        "run": _read_long_run(long_run_id),
        "novel_plan": _read_long_run_artifact(long_run_dir, "novel_plan", {}),
        "novel_state": _read_long_run_artifact(long_run_dir, "novel_state", {}),
        "clue_ledger": _read_long_run_artifact(long_run_dir, "clue_ledger", {}),
        "truth_state": _read_long_run_artifact(long_run_dir, "truth_state", {}),
        "open_threads_state": _read_long_run_artifact(long_run_dir, "open_threads_state", {}),
    }


@app.post("/api/novel-runs/{long_run_id}/chapters/next")
async def generate_next_novel_chapter(long_run_id: str):
    from app.config import Config
    from app.models.world import WorldConfig
    from app.runner.simulation_runner import SimulationRunner

    long_run_dir = _safe_long_run_dir(long_run_id)
    data = _read_long_run(long_run_id)
    chapters = list(data.get("chapters") or [])
    for existing_chapter in chapters:
        existing_chapter_no = int(existing_chapter.get("chapter_no") or 0)
        if existing_chapter_no and _derive_chapter_status(_chapter_dir(long_run_dir, existing_chapter_no), str(existing_chapter.get("status") or "completed")).get("validation_status") == "failed":
            raise HTTPException(status_code=409, detail=f"Chapter ch_{existing_chapter_no:03d} has validation errors; fix or regenerate it before continuing")
    target_chapters = int(data.get("target_chapters") or 1)
    if len(chapters) >= target_chapters:
        raise HTTPException(status_code=400, detail="Long run already reached target chapters")
    cfg = Config(PROJECT_ROOT)
    if not cfg.is_llm_available():
        raise HTTPException(status_code=400, detail="LLM 未配置。长篇 MVP 需要启用 LLM。")

    chapter_no = len(chapters) + 1
    chapter_dir = _chapter_dir(long_run_dir, chapter_no)
    if chapter_dir.exists() and any(chapter_dir.iterdir()):
        raise HTTPException(status_code=409, detail=f"Chapter directory already exists: ch_{chapter_no:03d}")
    previous_dir = _chapter_dir(long_run_dir, chapter_no - 1) if chapter_no > 1 else None
    data["status"] = "running"
    data["error"] = None
    _write_long_run(long_run_dir, data)

    try:
        world = WorldConfig.from_directory(WORLDS_DIR / data["world_id"])
        runner = SimulationRunner(PROJECT_ROOT)
        result = runner.run(
            world=world,
            mode="llm",
            ticks=data.get("ticks"),
            seed=int(data.get("seed") or 12345) + chapter_no - 1,
            genre_id=data.get("genre_id") or "horror",
            target_chapters=target_chapters,
            chapter_no=chapter_no,
            version="正式版V1",
            quality_controls=QualityControls.model_validate(data.get("quality_controls") or {}),
            sim_dir=chapter_dir,
            novel_run_dir=long_run_dir,
            previous_chapter_dir=previous_dir,
            memory_file=long_run_dir / "memories.jsonl",
        )
        chapter_status = _derive_chapter_status(chapter_dir)
        chapter_record = {
            "chapter_no": chapter_no,
            "simulation_id": result.simulation_id,
            "chapter_dir": str(chapter_dir.relative_to(PROJECT_ROOT)),
            "created_at": time.time(),
            **chapter_status,
        }
        chapters.append(chapter_record)
        data["chapters"] = chapters
        data["current_chapter"] = chapter_no
        data["last_simulation_id"] = result.simulation_id
        if chapter_status.get("validation_status") == "failed":
            data["status"] = "completed_with_validation_errors" if chapter_no >= target_chapters else "idle_with_validation_errors"
        else:
            data["status"] = "completed" if chapter_no >= target_chapters else "idle"
        try:
            _update_novel_runtime_from_chapter(long_run_dir, chapter_no, chapter_dir, data)
            data.pop("runtime_update_error", None)
        except Exception as runtime_exc:
            data["runtime_update_error"] = str(runtime_exc)
        _write_long_run(long_run_dir, data)
        return {"success": True, "long_run_id": long_run_id, "chapter": chapter_record, "run": data}
    except Exception as exc:
        data["status"] = "failed"
        data["error"] = str(exc)
        _write_long_run(long_run_dir, data)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/novel-runs/{long_run_id}/chapters/{chapter_no}")
async def get_novel_run_chapter(long_run_id: str, chapter_no: int):
    long_run_dir = _safe_long_run_dir(long_run_id)
    chapter_dir = _chapter_dir(long_run_dir, chapter_no)
    if not chapter_dir.exists():
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {
        "chapter_no": chapter_no,
        "chapter_draft": (chapter_dir / "chapter_draft.md").read_text(encoding="utf-8") if (chapter_dir / "chapter_draft.md").exists() else "",
        "chapter_plan": _read_json(chapter_dir / "chapter_plan.json", {}),
        "chapter_continuity": _read_json(chapter_dir / "chapter_continuity.json", {}),
        "quality_reports": _quality_reports_for_dir(chapter_dir),
        "run_status": _read_json(chapter_dir / "run_status.json", {}),
    }


@app.get("/api/novel-runs/{long_run_id}/memory")
async def get_novel_run_memory(long_run_id: str, limit: int = 200):
    long_run_dir = _safe_long_run_dir(long_run_id)
    return {"memories": _read_jsonl(long_run_dir / "memories.jsonl", limit=max(1, min(limit, 1000)))}


@app.get("/api/genres")
async def get_genres():
    from app.genre import GenreRegistry

    registry = GenreRegistry(PROJECT_ROOT / "app" / "genre_packs")
    available_genres = registry.list_available_genres()

    return {"genres": available_genres}


@app.get("/api/genres/{genre_id}/profile")
async def get_genre_profile(genre_id: str):
    from app.genre import GenreRegistry

    registry = GenreRegistry(PROJECT_ROOT / "app" / "genre_packs")
    profile = registry.get_genre_profile(genre_id)

    if not profile:
        raise HTTPException(status_code=404, detail="Genre not found")

    return {"profile": profile.__dict__}


class WorldUpdateRequest(BaseModel):
    world_bible: Optional[Dict[str, Any]] = None
    characters: Optional[Any] = None
    map: Optional[Any] = None
    clues: Optional[Any] = None
    plot_arcs: Optional[Any] = None
    character_arcs: Optional[Any] = None
    chapter_goal: Optional[Dict[str, Any]] = None
    quality_policy: Optional[Dict[str, Any]] = None


class CharactersUpdateRequest(BaseModel):
    characters: List[Dict[str, Any]] = Field(default_factory=list)


class GenerateCharactersRequest(BaseModel):
    world_id: str
    count: int = 3
    genre: str = ""
    character_type: str = "supporting"
    arc_id: str = ""


class GenerateNPCsRequest(BaseModel):
    world_id: str
    count: int = 3
    npc_type: str = "witness_npc"
    location_id: str = ""
    narrative_function: str = "information_source"


class GenerateCluesRequest(BaseModel):
    world_id: str
    count: int = 3
    arc_id: str = ""
    stage: str = ""
    clue_level: str = "minor"
    must_have_routes: int = 1
    allowed_route_types: List[str] = Field(default_factory=list)


class BootstrapRequest(BaseModel):
    user_seed: str = ""
    target_genre: str = "generic"
    target_words: Optional[int] = None
    target_chapters: Optional[int] = None
    world_id: Optional[str] = None
    auto_confirm: bool = False


@app.put("/api/worlds/{world_id}")
async def update_world(world_id: str, request: WorldUpdateRequest):
    payload = request.model_dump(exclude_none=True)
    saved = _save_world_payload(world_id, payload)
    return {"success": True, "world_id": world_id, "summary": _world_summary(saved)}


@app.put("/api/worlds/{world_id}/characters")
async def update_world_characters(world_id: str, request: CharactersUpdateRequest):
    saved = _save_world_payload(world_id, {"characters": request.characters})
    return {"success": True, "world_id": world_id, "summary": _world_summary(saved)}


@app.post("/api/generate/characters")
async def generate_characters(request: GenerateCharactersRequest):
    world = _load_world_payload(request.world_id)
    count = max(1, min(request.count, 10))
    candidates = [_build_generated_character(world, i, request.character_type) for i in range(count)]
    return {"success": True, "candidates": candidates, "generator": "RuleCharacterGenerator"}


@app.post("/api/generate/npcs")
async def generate_npcs(request: GenerateNPCsRequest):
    world = _load_world_payload(request.world_id)
    count = max(1, min(request.count, 10))
    candidates = []
    for i in range(count):
        npc = _build_generated_character(world, i, "npc")
        npc.update({
            "candidate_type": "npc",
            "type": request.npc_type,
            "persistence": "recurring_npc",
            "narrative_function": request.narrative_function,
            "location_id": request.location_id or npc.get("location_id", ""),
            "personality": "基于当前世界配置生成，可继续编辑",
            "knows": [],
            "forbidden_knowledge": [],
            "first_available_topics": [],
            "generator": "RuleNPCGenerator",
        })
        candidates.append(npc)
    return {"success": True, "candidates": candidates, "generator": "RuleNPCGenerator"}


@app.post("/api/generate/clues")
async def generate_clues(request: GenerateCluesRequest):
    world = _load_world_payload(request.world_id)
    count = max(1, min(request.count, 10))
    candidates = [_build_generated_clue(world, i, request.arc_id, request.clue_level) for i in range(count)]
    for clue in candidates:
        clue["allowed_stages"] = [request.stage] if request.stage else []
        clue["generator"] = "RuleClueGenerator"
    return {"success": True, "candidates": candidates, "generator": "RuleClueGenerator"}


@app.post("/api/story/bootstrap")
async def create_story_bootstrap(request: BootstrapRequest):
    if not request.user_seed.strip():
        raise HTTPException(status_code=400, detail="请先输入故事种子")
    result = _build_bootstrap_result(request.model_dump())
    if request.auto_confirm:
        return await confirm_story_bootstrap(result["bootstrap_id"])
    return result


@app.get("/api/story/bootstrap/{bootstrap_id}")
async def get_story_bootstrap(bootstrap_id: str):
    path = _bootstrap_path(bootstrap_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Bootstrap not found")
    return _read_json(path, {})


@app.post("/api/story/bootstrap/{bootstrap_id}/confirm")
async def confirm_story_bootstrap(bootstrap_id: str):
    result = await get_story_bootstrap(bootstrap_id)
    world_id = result.get("world_id")
    if not world_id:
        raise HTTPException(status_code=400, detail="Bootstrap 缺少 world_id")
    validation = result.get("validation") or {}
    if validation and not validation.get("passed", False):
        raise HTTPException(status_code=400, detail={
            "message": "Bootstrap 校验未通过，不能确认写盘",
            "issues": validation.get("issues") or [],
            "warnings": validation.get("warnings") or [],
        })
    payload = {
        "world_bible": result.get("world_bible", {}),
        "characters": result.get("characters", []),
        "map": result.get("map", []),
        "clues": result.get("clues", []),
        "plot_arcs": result.get("plot_arcs", []),
        "character_arcs": result.get("character_arcs", []),
        "chapter_goal": result.get("chapter_goal", {}),
        "quality_policy": result.get("quality_policy", {}),
        "truth_chain": result.get("truth_chain", []),
        "evidence_graph": result.get("evidence_graph", {}),
        "open_threads": result.get("open_threads", []),
        "writer_story_anchors": result.get("writer_story_anchors", {}),
        "opening_chapter_plan": result.get("opening_chapter_plan", {}),
        "bootstrap_result": {**result, "status": "confirmed"},
        "bootstrap_manifest": {"bootstrap_id": bootstrap_id, "status": "confirmed"},
    }
    saved = _save_world_payload(world_id, payload)
    result["status"] = "confirmed"
    result["story_blueprint"] = _build_story_blueprint(result)
    _write_json(_bootstrap_path(bootstrap_id), result)
    return {"success": True, "bootstrap_id": bootstrap_id, "world_id": world_id, "summary": _world_summary(saved)}


@app.post("/api/story/bootstrap/{bootstrap_id}/start")
async def start_story_bootstrap(bootstrap_id: str):
    confirmed = await confirm_story_bootstrap(bootstrap_id)
    request = SimulationRequest(world_id=confirmed["world_id"])
    sim = await run_simulation(request)
    return sim


@app.post("/api/worlds/{world_id}/complete")
async def complete_world(world_id: str, request: BootstrapRequest):
    existing = _load_world_payload(world_id)
    bible = existing.get("world_bible") or {}
    seed = request.user_seed or bible.get("title") or world_id
    bootstrapper = _create_bootstrapper()
    from app.bootstrap.world_completion_service import WorldCompletionService

    completion_service = WorldCompletionService(PROJECT_ROOT, bootstrapper)
    result_model = completion_service.preview_completion(
        world_id=world_id,
        user_seed=seed,
        manual_world_payload=existing,
        target_genre=request.target_genre or bible.get("genre") or bible.get("genre_id") or "generic",
        target_words=request.target_words or 100000,
    )
    result = _persist_bootstrap_result(_model_to_jsonable(result_model))
    if request.auto_confirm:
        await confirm_story_bootstrap(result["bootstrap_id"])
        result = await get_story_bootstrap(result["bootstrap_id"])
    return result


class CreateWorldRequest(BaseModel):
    world_id: str
    title: str = "New World"
    genre: str = "horror"
    tone: str = ""
    era: str = "Modern"


@app.post("/api/worlds/create")
async def create_world(request: CreateWorldRequest):
    try:
        world_dir = _safe_world_dir(request.world_id, must_exist=False)

        if world_dir.exists():
            raise HTTPException(status_code=400, detail="World ID already exists")

        world_dir.mkdir(parents=True, exist_ok=True)

        default_world_bible = {
            "world_id": request.world_id,
            "title": request.title,
            "genre": request.genre,
            "tone": request.tone,
            "era": request.era,
            "rules": [],
            "themes": [],
        }

        files = {
            "world_bible.json": default_world_bible,
            "characters.json": {"characters": []},
            "map.json": {"locations": []},
            "clues.json": {"clues": []},
            "plot_arcs.json": {"arcs": []},
            "character_arcs.json": {"arcs": []},
            "chapter_goal.json": {},
            "quality_policy.json": {
                "min_characters": 2,
                "min_locations": 2,
                "min_clues": 3,
                "quality_threshold": 70,
            },
        }

        for filename, data in files.items():
            _write_json(world_dir / filename, data)
        
        return {
            "success": True,
            "world_id": request.world_id,
            "message": f"World '{request.title}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Novel Simulator API 正式版V1")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Worlds Dir: {WORLDS_DIR}")
    print(f"Outputs Dir: {OUTPUTS_DIR}")
    print("=" * 60)

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8421,
        reload=True,
    )
