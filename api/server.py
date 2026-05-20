from __future__ import annotations

import io
import json
import os
import sys
import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional

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
    v2_phase: str = "v2.3"
    ticks: Optional[int] = None
    seed: int = 12345
    genre_id: str = "horror"
    target_chapters: int = 10
    chapter_no: int = 1


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
                worlds.append(world_info)
    return {"worlds": worlds}


@app.get("/api/worlds/{world_id}")
async def get_world(world_id: str):
    world_dir = WORLDS_DIR / world_id
    if not world_dir.exists():
        raise HTTPException(status_code=404, detail="World not found")

    world_data = {"id": world_id}
    for json_file in ["world_bible", "characters", "map", "clues", "quality_policy"]:
        file_path = world_dir / f"{json_file}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                world_data[json_file] = json.load(f)

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

        # 最终版本统一使用：move+memory+LLM叙事+一致性修订（v2.3）
        forced_mode = "llm"
        forced_phase = "v2.3"

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


class CreateWorldRequest(BaseModel):
    world_id: str
    title: str = "New World"
    genre: str = "horror"
    tone: str = ""
    era: str = "Modern"


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
            "rules": [
                "Add your world rules here"
            ],
            "themes": [
                "Theme 1",
                "Theme 2"
            ]
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
