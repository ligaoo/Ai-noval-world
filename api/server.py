from __future__ import annotations

import io
import json
import os
import sys
import asyncio
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

# Windows 编码修复：强制使用 UTF-8
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.append(str(Path(__file__).parent.parent))

app = FastAPI(title="Novel Simulator API", version="5.2.0")

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

# 模拟状态存储
running_simulations: Dict[str, Dict] = {}


class SimulationRequest(BaseModel):
    world_id: str = "dark_city_001"
    mode: str = "llm"
    v2_phase: str = "v2.4"
    ticks: Optional[int] = None
    seed: int = 12345
    genre_id: str = "horror"
    target_chapters: int = 10
    chapter_no: int = 1
    allow_incomplete_world: bool = False


class BootstrapRequest(BaseModel):
    user_seed: str
    target_genre: str = "horror_suspense"
    target_words: int = 100000
    auto_confirm: bool = False
    world_id: Optional[str] = None


# Bootstrap 候选存储（内存级；写盘后可重建）
bootstrap_candidates: Dict[str, Dict] = {}


@app.get("/")
async def root():
    return {
        "message": "Novel Simulator API v5.2.0",
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
                bible_file = world_dir / "world_bible.json"
                if bible_file.exists():
                    with open(bible_file, "r", encoding="utf-8") as f:
                        bible = json.load(f)
                        world_info["title"] = bible.get("title", world_dir.name)
                        world_info["genre"] = bible.get("genre_id", "generic")
                try:
                    from app.models.world import WorldConfig
                    from app.services.world_runtime_validator import RuntimeWorldValidator
                    world = WorldConfig.from_directory(world_dir)
                    validation = RuntimeWorldValidator().validate_for_formal_run(world, world_dir)
                    world_info["formal_run_ready"] = validation.passed
                    world_info["formal_run_issues"] = validation.issues[:5]
                except Exception as exc:
                    world_info["formal_run_ready"] = False
                    world_info["formal_run_issues"] = [str(exc)]
                worlds.append(world_info)
    return {"worlds": worlds}


@app.get("/api/worlds/{world_id}")
async def get_world(world_id: str):
    world_dir = WORLDS_DIR / world_id
    if not world_dir.exists():
        raise HTTPException(status_code=404, detail="World not found")

    world_data = {"id": world_id}
    for json_file in ["world_bible", "characters", "map", "clues", "quality_policy", "bootstrap_manifest"]:
        file_path = world_dir / f"{json_file}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                world_data[json_file] = json.load(f)

    try:
        from app.models.world import WorldConfig
        from app.services.world_runtime_validator import RuntimeWorldValidator
        world = WorldConfig.from_directory(world_dir)
        world_data["display"] = {
            "characters": {char.id: char.name for char in world.characters.characters},
            "locations": {loc.id: loc.name for loc in world.map.locations},
        }
        validation = RuntimeWorldValidator().validate_for_formal_run(world, world_dir)
        world_data["formal_run_validation"] = {
            "passed": validation.passed,
            "issues": validation.issues,
            "warnings": validation.warnings,
        }
    except Exception as exc:
        world_data["formal_run_validation"] = {
            "passed": False,
            "issues": [str(exc)],
            "warnings": [],
        }

    return world_data


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
        if not request.allow_incomplete_world:
            from app.services.world_runtime_validator import RuntimeWorldValidator
            validation = RuntimeWorldValidator().validate_for_formal_run(world, world_dir)
            if not validation.passed:
                running_simulations[sim_id]["status"] = "failed"
                running_simulations[sim_id]["error"] = "当前 world 未完成模型补全或不可正式运行。"
                running_simulations[sim_id]["validation"] = {
                    "issues": validation.issues,
                    "warnings": validation.warnings,
                }
                return

        # 最新 v2.4 Agent Sandbox 统一使用：move+memory+LLM叙事+一致性修订
        forced_mode = "llm"
        forced_phase = "v2.4"

        runner = SimulationRunner(PROJECT_ROOT)
        result = runner.run(
            world=world,
            mode=forced_mode,
            ticks=request.ticks,
            seed=request.seed,
            genre_id=request.genre_id,
            target_chapters=request.target_chapters,
            chapter_no=request.chapter_no,
            v2_phase=forced_phase,
            allow_incomplete_world=request.allow_incomplete_world,
        )

        running_simulations[sim_id]["status"] = "completed"
        running_simulations[sim_id]["simulation_id"] = result.simulation_id
        running_simulations[sim_id]["runtime_mode"] = forced_mode
        running_simulations[sim_id]["runtime_phase"] = forced_phase
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

        from app.models.world import WorldConfig
        from app.services.world_runtime_validator import RuntimeWorldValidator

        world_dir = WORLDS_DIR / request.world_id
        if not world_dir.exists():
            raise HTTPException(status_code=404, detail="World not found")

        world = WorldConfig.from_directory(world_dir)
        if not request.allow_incomplete_world:
            validation = RuntimeWorldValidator().validate_for_formal_run(world, world_dir)
            if not validation.passed:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": "当前 world 未完成模型补全或不可正式运行，请先通过 Story Bootstrap 生成并确认完整世界。",
                        "issues": validation.issues,
                        "warnings": validation.warnings,
                    },
                )

        request.mode = "llm"
        request.v2_phase = "v2.4"

        # 生成模拟 ID
        import time
        sim_id = f"sim_{int(time.time() * 1000)}"

        # 初始化模拟状态
        running_simulations[sim_id] = {
            "status": "running",
            "request": request.model_dump(),
            "error": None,
            "runtime_mode": "llm",
            "runtime_phase": "v2.4",
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


class GenerateCharactersRequest(BaseModel):
    world_id: str
    count: int = 3
    genre: str = "horror"


class CreateWorldRequest(BaseModel):
    world_id: str
    title: str = "New World"
    genre: str = "horror"
    tone: str = ""
    era: str = "Modern"


class SaveWorldRequest(BaseModel):
    world_bible: Dict[str, Any] = {}
    characters: List[Dict[str, Any]] = []
    map: Any = []
    clues: Any = []
    plot_arcs: List[Dict[str, Any]] = []
    character_arcs: List[Dict[str, Any]] = []
    chapter_goal: Dict[str, Any] = {}


class SaveCharactersRequest(BaseModel):
    characters: List[Dict[str, Any]] = []


class CompleteWorldRequest(BaseModel):
    user_seed: Optional[str] = None
    target_genre: str = "horror_suspense"
    target_words: int = 100000
    auto_confirm: bool = False
    manual_world: Optional[Dict[str, Any]] = None


@app.post("/api/generate/characters")
async def generate_characters(request: GenerateCharactersRequest):
    """基于世界观背景使用 LLM 生成角色候选"""
    try:
        from app.services.llm_character_generator import (
            LLMCharacterGenerator,
            CharacterGenerationRequest,
        )

        generator = LLMCharacterGenerator(PROJECT_ROOT)

        gen_request = CharacterGenerationRequest(
            world_id=request.world_id,
            count=request.count,
            genre=request.genre,
        )

        candidates = generator.generate(gen_request)

        # 转换为字典返回
        result = []
        for c in candidates:
            result.append({
                "character_id": c.character_id,
                "name": c.name,
                "role": c.role,
                "agent_type": c.agent_type,
                "traits": c.traits,
                "goals": c.goals,
                "skills": c.skills,
                "backstory": c.backstory,
                "emotional_core": c.emotional_core,
            })

        return {
            "success": True,
            "candidates": result,
            "message": f"成功生成 {len(result)} 个角色候选",
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def _slug(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    if not text:
        text = fallback
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in text)


def _normalize_action_type(action: Any) -> str:
    mapping = {
        "调查": "inspect",
        "检查": "inspect",
        "观察": "inspect",
        "搜查": "search",
        "搜索": "search",
        "询问": "ask",
        "对话": "talk",
        "交谈": "talk",
    }
    text = str(action or "inspect").strip()
    return mapping.get(text, text or "inspect")


def _normalize_role(role: Any) -> str:
    mapping = {
        "主角": "protagonist",
        "主人公": "protagonist",
        "失踪者": "missing_person",
        "隐藏反派": "hidden_actor",
        "NPC": "npc",
    }
    text = str(role or "npc").strip()
    return mapping.get(text, text or "npc")


def _normalize_character(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    char_id = raw.get("id") or raw.get("character_id") or _slug(raw.get("name"), f"char_{index + 1}")
    personality = raw.get("personality") if isinstance(raw.get("personality"), dict) else {}
    if raw.get("traits") and not personality.get("traits"):
        personality["traits"] = raw.get("traits")
    goals = raw.get("goals") if isinstance(raw.get("goals"), dict) else {}
    return {
        "id": char_id,
        "name": raw.get("name") or char_id,
        "role": _normalize_role(raw.get("role")),
        "personality": personality,
        "goals": goals,
        "fears": raw.get("fears") or [],
        "secrets": raw.get("secrets") or [],
        "skills": raw.get("skills") or {"observation": 50, "logic": 50},
        "initial_location": raw.get("initial_location") or raw.get("location_id") or "location_001",
        "active_agent": raw.get("active_agent", True),
        "visibility": raw.get("visibility") or "visible",
        "narrative_function": raw.get("narrative_function") or [],
        "personal_stakes": raw.get("personal_stakes") or "",
        "background": raw.get("background") or raw.get("backstory") or "",
        "known_facts": raw.get("known_facts") or raw.get("knows") or [],
        "suspicions": raw.get("suspicions") or [],
        "inventory": raw.get("inventory") or [],
        "disclosure_policy": raw.get("disclosure_policy") or {},
        "llm_temperature": raw.get("llm_temperature"),
    }


def _normalize_location_object(raw: Any, location_id: str, index: int) -> Dict[str, Any]:
    if isinstance(raw, str):
        object_id = _slug(raw, f"{location_id}_object_{index + 1}")
        return {"id": object_id, "name": raw, "visible": True, "state": "", "description": raw}
    object_id = raw.get("id") or raw.get("object_id") or _slug(raw.get("name"), f"{location_id}_object_{index + 1}")
    return {
        "id": object_id,
        "name": raw.get("name") or object_id,
        "visible": raw.get("visible", True),
        "state": raw.get("state") or "",
        "description": raw.get("description") or raw.get("name") or object_id,
    }


def _normalize_location(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    location_id = raw.get("id") or raw.get("location_id") or _slug(raw.get("name"), f"location_{index + 1:03d}")
    objects = raw.get("objects") or []
    return {
        "id": location_id,
        "name": raw.get("name") or location_id,
        "public_description": raw.get("public_description") or raw.get("description") or raw.get("name") or location_id,
        "objects": [_normalize_location_object(obj, location_id, i) for i, obj in enumerate(objects)],
        "connected_to": raw.get("connected_to") or [],
        "danger_level": raw.get("danger_level") or 0,
        "time_effects": raw.get("time_effects") or {},
    }


def _normalize_clue_route(raw: Dict[str, Any], clue_id: str, index: int) -> Dict[str, Any]:
    action_type = _normalize_action_type(raw.get("action_type") or raw.get("action"))
    return {
        "route_id": raw.get("route_id") or f"{clue_id}_route_{index + 1}",
        "action_type": action_type,
        "target": raw.get("target") or raw.get("object_id") or "",
        "location_id": raw.get("location_id") or "",
        "topic": raw.get("topic"),
        "required_skill": raw.get("required_skill"),
        "difficulty": raw.get("difficulty") or 50,
        "min_attitude": raw.get("min_attitude", 0),
        "result_text": raw.get("result_text") or raw.get("result") or "",
    }


def _normalize_clue(raw: Dict[str, Any], index: int) -> Dict[str, Any]:
    clue_id = raw.get("id") or raw.get("clue_id") or _slug(raw.get("name"), f"clue_{index + 1:03d}")
    routes = raw.get("discover_routes") or []
    return {
        "id": clue_id,
        "name": raw.get("name") or raw.get("title") or clue_id,
        "content": raw.get("content") or "",
        "truth_level": raw.get("truth_level") or raw.get("level") or "hidden_fact",
        "importance": raw.get("importance") or 50,
        "discover_routes": [_normalize_clue_route(route, clue_id, i) for i, route in enumerate(routes) if isinstance(route, dict)],
        "on_discovered": raw.get("on_discovered") or {
            "add_known_fact_to": "discoverer",
            "plot_value": {"mystery": 5, "progress": 10, "conflict": 0},
        },
        "bootstrap_fact": raw.get("bootstrap_fact"),
        "bootstrap_inventory": raw.get("bootstrap_inventory"),
        "bootstrap_event": raw.get("bootstrap_event"),
        "related_thread": raw.get("related_thread"),
    }


def _normalize_save_world_payload(world_id: str, request: SaveWorldRequest) -> Dict[str, Any]:
    bible = dict(request.world_bible or {})
    bible["world_id"] = world_id
    bible.setdefault("title", world_id)
    bible.setdefault("genre", "horror")
    bible.setdefault("tone", "")
    bible.setdefault("era", "Modern")
    bible.setdefault("rules", [])
    bible.setdefault("themes", [])
    bible["draft"] = True
    bible.setdefault("draft_reason", "手动编辑的世界草稿需要通过自动补全确认后才能正式运行。")

    map_payload = request.map.get("locations", []) if isinstance(request.map, dict) else request.map
    clues_payload = request.clues.get("clues", []) if isinstance(request.clues, dict) else request.clues

    characters = [_normalize_character(c, i) for i, c in enumerate(request.characters or []) if isinstance(c, dict)]
    locations = [_normalize_location(loc, i) for i, loc in enumerate(map_payload or []) if isinstance(loc, dict)]
    clues = [_normalize_clue(clue, i) for i, clue in enumerate(clues_payload or []) if isinstance(clue, dict)]

    chapter_goal = dict(request.chapter_goal or {})
    chapter_goal.setdefault("goal", "Setup the story")
    chapter_goal.setdefault("pov", characters[0]["id"] if characters else "char_protagonist")
    chapter_goal.setdefault("start_time", "day1_08:00")
    chapter_goal.setdefault("target_progress", 100)
    chapter_goal.setdefault("tick_limit", 30)
    chapter_goal.setdefault("no_progress_limit", 4)

    return {
        "world_bible.json": bible,
        "characters.json": {"characters": characters},
        "map.json": {"locations": locations},
        "clues.json": {"clues": clues},
        "chapter_goal.json": chapter_goal,
        "plot_arcs.json": {"arcs": request.plot_arcs or []},
        "character_arcs.json": {"arcs": request.character_arcs or []},
    }


@app.post("/api/worlds/create")
async def create_world(request: CreateWorldRequest):
    try:
        world_dir = WORLDS_DIR / request.world_id
        
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
            "draft": True,
            "draft_reason": "手动创建的世界草稿不能直接正式运行，请先通过 Story Bootstrap 使用模型补全。",
        }
        
        default_characters = {
            "characters": [
                {
                    "id": "char_protagonist",
                    "name": "Protagonist",
                    "role": "protagonist",
                    "personality": {
                        "traits": ["Brave", "Curious"]
                    },
                    "goals": {
                        "short_term": "Discover the truth",
                        "long_term": "Find peace"
                    },
                    "skills": {
                        "observation": 70,
                        "logic": 65
                    },
                    "initial_location": "location_001"
                }
            ]
        }
        
        default_map = {
            "locations": [
                {
                    "id": "location_001",
                    "name": "Starting Point",
                    "public_description": "The place where the story begins.",
                    "objects": [],
                    "connected_to": ["location_002"],
                    "danger_level": 1
                },
                {
                    "id": "location_002",
                    "name": "Mysterious Place",
                    "public_description": "A place full of mysteries.",
                    "objects": [],
                    "connected_to": ["location_001"],
                    "danger_level": 2
                }
            ]
        }
        
        default_clues = {
            "clues": [
                {
                    "id": "clue_001",
                    "name": "First Clue",
                    "content": "This is the first clue to start your story.",
                    "truth_level": "hidden_fact",
                    "importance": 50,
                    "discover_routes": [],
                    "on_discovered": {
                        "add_known_fact_to": "discoverer",
                        "plot_value": {
                            "mystery": 10,
                            "progress": 10,
                            "conflict": 5
                        }
                    }
                }
            ]
        }
        
        default_chapter_goal = {
            "goal": "Setup the story",
            "pov": "char_protagonist",
            "start_time": "day1_08:00",
            "target_progress": 100,
            "tick_limit": 30,
            "no_progress_limit": 4
        }
        
        default_quality_policy = {
            "min_characters": 2,
            "min_locations": 2,
            "min_clues": 3,
            "quality_threshold": 70
        }
        
        files = {
            "world_bible.json": default_world_bible,
            "characters.json": default_characters,
            "map.json": default_map,
            "clues.json": default_clues,
            "chapter_goal.json": default_chapter_goal,
            "quality_policy.json": default_quality_policy
        }
        
        for filename, data in files.items():
            file_path = world_dir / filename
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "world_id": request.world_id,
            "message": f"World '{request.title}' created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/worlds/{world_id}")
async def save_world(world_id: str, request: SaveWorldRequest):
    try:
        world_dir = WORLDS_DIR / world_id
        if not world_dir.exists():
            raise HTTPException(status_code=404, detail="World not found")

        files = _normalize_save_world_payload(world_id, request)
        for filename, data in files.items():
            with open(world_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "world_id": world_id,
            "message": "World draft saved",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/worlds/{world_id}/characters")
async def save_world_characters(world_id: str, request: SaveCharactersRequest):
    try:
        world_dir = WORLDS_DIR / world_id
        if not world_dir.exists():
            raise HTTPException(status_code=404, detail="World not found")

        characters = [
            _normalize_character(character, index)
            for index, character in enumerate(request.characters or [])
            if isinstance(character, dict)
        ]
        with open(world_dir / "characters.json", "w", encoding="utf-8") as f:
            json.dump({"characters": characters}, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "world_id": world_id,
            "message": "Characters saved",
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Story Bootstrap APIs（V1 自动补全 / 22 章）
# ============================================================
def _build_bootstrapper():
    """构造 StoryBootstrapper（带 LLM 客户端，若可用）"""
    from app.bootstrap import StoryBootstrapper
    from app.config import Config

    cfg = Config(PROJECT_ROOT)
    llm_client = None
    if cfg.is_llm_available():
        try:
            from app.llm_client import OpenAICompatibleClient
            llm_client = OpenAICompatibleClient.from_config(PROJECT_ROOT)
        except Exception:
            llm_client = None
    return StoryBootstrapper(PROJECT_ROOT, llm_client=llm_client)


def _load_bootstrap_result_from_disk(bootstrap_id: str):
    from app.bootstrap import BootstrapResult

    if not WORLDS_DIR.exists():
        return None, None
    for world_dir in WORLDS_DIR.iterdir():
        if not world_dir.is_dir():
            continue
        result_file = world_dir / "bootstrap_result.json"
        if not result_file.exists():
            continue
        data = json.loads(result_file.read_text(encoding="utf-8"))
        if data.get("bootstrap_id") == bootstrap_id:
            return BootstrapResult.model_validate(data), world_dir
    return None, None


def _load_bootstrap_manifest_from_disk(bootstrap_id: str):
    if not WORLDS_DIR.exists():
        return None, None
    for world_dir in WORLDS_DIR.iterdir():
        if not world_dir.is_dir():
            continue
        manifest = world_dir / "bootstrap_manifest.json"
        if not manifest.exists():
            continue
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("bootstrap_id") == bootstrap_id:
            return data, world_dir
    return None, None


def _get_bootstrap_entry(bootstrap_id: str):
    if bootstrap_id in bootstrap_candidates:
        return bootstrap_candidates[bootstrap_id]

    result, _ = _load_bootstrap_result_from_disk(bootstrap_id)
    if result:
        bootstrapper = _build_bootstrapper()
        bootstrap_candidates[bootstrap_id] = {
            "result": result,
            "bootstrapper_ref": bootstrapper,
        }
        return bootstrap_candidates[bootstrap_id]
    return None


@app.post("/api/worlds/{world_id}/complete")
async def complete_world(world_id: str, request: CompleteWorldRequest):
    try:
        from app.bootstrap.world_completion_service import WorldCompletionService

        world_dir = WORLDS_DIR / world_id
        if not world_dir.exists():
            raise HTTPException(status_code=404, detail="World not found")

        bootstrapper = _build_bootstrapper()
        service = WorldCompletionService(PROJECT_ROOT, bootstrapper)
        result = service.preview_completion(
            world_id=world_id,
            user_seed=request.user_seed,
            manual_world_payload=request.manual_world,
            target_genre=request.target_genre,
            target_words=request.target_words,
        )

        bootstrap_candidates[result.bootstrap_id] = {
            "result": result,
            "bootstrapper_ref": bootstrapper,
        }

        if request.auto_confirm and result.validation and result.validation.passed:
            result.status = "confirmed"
            bootstrapper.write_to_worlds_dir(result)

        return {
            "bootstrap_id": result.bootstrap_id,
            "world_id": result.world_id,
            "status": result.status,
            "title": result.title,
            "summary": result.summary_dict(),
            "validation": result.validation.model_dump() if result.validation else None,
            "fusion_report": result.fusion_report,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/story/bootstrap")
async def create_story_bootstrap(request: BootstrapRequest):
    """
    输入一句模糊设定 → 自动补全完整世界候选（不直接覆盖现有 worlds 目录）
    """
    try:
        from app.bootstrap import BootstrapSeed

        bootstrapper = _build_bootstrapper()
        seed = BootstrapSeed(
            user_seed=request.user_seed,
            target_genre=request.target_genre,
            target_words=request.target_words,
            auto_confirm=request.auto_confirm,
        )
        result = bootstrapper.bootstrap(seed, world_id=request.world_id)

        # 候选缓存
        bootstrap_candidates[result.bootstrap_id] = {
            "result": result,
            "bootstrapper_ref": bootstrapper,
        }

        # 如果 auto_confirm，立即写盘
        if request.auto_confirm and result.validation and result.validation.passed:
            result.status = "confirmed"
            bootstrapper.write_to_worlds_dir(result)

        return {
            "bootstrap_id": result.bootstrap_id,
            "world_id": result.world_id,
            "status": result.status,
            "title": result.title,
            "summary": result.summary_dict(),
            "validation": result.validation.model_dump() if result.validation else None,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/story/bootstrap/{bootstrap_id}")
async def get_story_bootstrap(bootstrap_id: str):
    """查看候选完整内容"""
    entry = _get_bootstrap_entry(bootstrap_id)
    if entry:
        return entry["result"].model_dump(mode="json")

    manifest, _ = _load_bootstrap_manifest_from_disk(bootstrap_id)
    if manifest:
        return manifest
    raise HTTPException(status_code=404, detail="Bootstrap candidate not found")


@app.post("/api/story/bootstrap/{bootstrap_id}/confirm")
async def confirm_story_bootstrap(bootstrap_id: str):
    """确认候选并写入 worlds/<world_id>/"""
    entry = _get_bootstrap_entry(bootstrap_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Bootstrap candidate not found")

    result = entry["result"]
    bootstrapper = entry["bootstrapper_ref"]

    if not result.validation or not result.validation.passed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Bootstrap 校验未通过或缺失，无法确认。",
                "issues": [i.model_dump() for i in result.validation.issues] if result.validation else [],
            },
        )

    result.status = "confirmed"
    world_dir = bootstrapper.write_to_worlds_dir(result)
    return {
        "success": True,
        "world_id": result.world_id,
        "world_dir": str(world_dir),
        "summary": result.summary_dict(),
    }


@app.post("/api/story/bootstrap/{bootstrap_id}/start")
async def start_story_bootstrap(bootstrap_id: str):
    """确认 + 立即启动一次模拟"""
    entry = _get_bootstrap_entry(bootstrap_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Bootstrap candidate not found")

    result = entry["result"]
    bootstrapper = entry["bootstrapper_ref"]

    if not result.validation or not result.validation.passed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Bootstrap 校验未通过或缺失，无法启动模拟。",
                "issues": [i.model_dump() for i in result.validation.issues] if result.validation else [],
            },
        )

    # 1) 写盘
    result.status = "confirmed"
    world_dir = bootstrapper.write_to_worlds_dir(result)

    from app.models.world import WorldConfig
    from app.services.world_runtime_validator import RuntimeWorldValidator
    world = WorldConfig.from_directory(world_dir)
    validation = RuntimeWorldValidator().validate_for_formal_run(world, world_dir)
    if not validation.passed:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Bootstrap 写盘后的 world 仍不可正式运行。",
                "issues": validation.issues,
                "warnings": validation.warnings,
            },
        )

    # 2) 启动模拟（复用现有 run_simulation 路径）
    sim_request = SimulationRequest(
        world_id=result.world_id,
        mode="llm",
        v2_phase="v2.4",
        seed=12345,
        genre_id=(result.world_bible.get("genre") or "horror"),
        target_chapters=10,
        chapter_no=1,
    )
    return await run_simulation(sim_request)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Novel Simulator API v5.2.0")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Worlds Dir: {WORLDS_DIR}")
    print(f"Outputs Dir: {OUTPUTS_DIR}")
    print("=" * 60)

    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8421,
    )
