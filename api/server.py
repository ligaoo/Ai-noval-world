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

# 模拟状态存储
running_simulations: Dict[str, Dict] = {}
BOOTSTRAPS_DIR = OUTPUTS_DIR / "bootstraps"
WORLD_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def _safe_world_dir(world_id: str, must_exist: bool = True) -> Path:
    if not world_id or not WORLD_ID_PATTERN.fullmatch(world_id):
        raise HTTPException(status_code=400, detail="World ID 只能包含字母、数字、下划线和连字符")
    world_dir = WORLDS_DIR / world_id
    if must_exist and not world_dir.exists():
        raise HTTPException(status_code=404, detail="World not found")
    return world_dir


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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


def _build_bootstrap_result(request: Dict) -> Dict:
    bootstrap_id = f"boot_{int(time.time() * 1000)}"
    world_id = request.get("world_id") or f"world_{int(time.time() * 1000)}"
    seed = (request.get("user_seed") or "").strip()
    target_genre = request.get("target_genre") or "generic"
    title = seed[:16] if seed else world_id
    world_bible = {
        "world_id": world_id,
        "title": title,
        "genre": target_genre,
        "sub_genre": target_genre,
        "era": "Modern",
        "tone": "待完善",
        "themes": [],
        "rules": [seed] if seed else [],
    }
    locations = [
        {
            "location_id": "location_start",
            "id": "location_start",
            "name": "起点场景",
            "public_description": seed or "故事开始的位置。",
            "objects": [],
            "connected_to": [],
            "danger_level": 1,
        }
    ]
    characters = [
        {
            "character_id": "char_protagonist",
            "id": "char_protagonist",
            "name": "主角",
            "role": "protagonist",
            "agent_type": "core_agent",
            "traits": [],
            "goals": {"short_term": "进入故事并寻找目标", "long_term": "完成主线目标"},
            "skills": {"observation": 60, "logic": 60, "social": 50, "courage": 50},
            "initial_location": "location_start",
        }
    ]
    clues = [_build_generated_clue({"world_bible": world_bible, "map": {"locations": locations}}, 0, "main_arc", "minor")]
    result = {
        "bootstrap_id": bootstrap_id,
        "world_id": world_id,
        "status": "draft",
        "title": title,
        "user_seed": seed,
        "target_words": request.get("target_words"),
        "world_bible": world_bible,
        "characters": characters,
        "map": locations,
        "clues": clues,
        "plot_arcs": [{"arc_id": "main_arc", "name": "主线", "status": "active", "current_stage": "setup", "progress": 0, "stages": []}],
        "character_arcs": [],
        "chapter_goal": {"goal": "建立故事开端", "pov": "char_protagonist", "target_progress": 100, "tick_limit": 30, "no_progress_limit": 4},
        "quality_policy": {"min_characters": 1, "min_locations": 1, "min_clues": 1, "quality_threshold": 70},
        "opening_chapter_plan": {"protagonist_goal": "进入故事并发现第一个异常", "initial_location": "location_start", "selected_clues": [clues[0]["clue_id"]]},
        "truth_chain": [],
        "evidence_graph": {},
        "open_threads": [],
        "writer_story_anchors": {},
        "summary": {"characters": len(characters), "locations": len(locations), "clues": len(clues)},
        "validation": {"passed": True, "issues": [], "warnings": []},
    }
    _write_json(_bootstrap_path(bootstrap_id), result)
    return result


class SimulationRequest(BaseModel):
    world_id: str = "dark_city_001"
    mode: str = "llm"
    version: str = "正式版V1"
    ticks: Optional[int] = None
    seed: int = 12345
    genre_id: str = "horror"
    target_chapters: int = 10
    chapter_no: int = 1
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
        result = await confirm_story_bootstrap(result["bootstrap_id"])
    return {"success": True, "bootstrap_id": result["bootstrap_id"], "world_id": result["world_id"], "status": result.get("status", "draft")}


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
    result = _build_bootstrap_result({
        "user_seed": seed,
        "target_genre": request.target_genre or bible.get("genre") or bible.get("genre_id") or "generic",
        "target_words": request.target_words,
        "world_id": world_id,
    })
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
