from pathlib import Path
from typing import Optional

import io
import os
import sys

# Windows 编码修复：强制使用 UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

import typer
from rich.console import Console

from app.config import Config
from app.models.world import WorldConfig
from app.runner.simulation_runner import SimulationRunner


app = typer.Typer(no_args_is_help=True, help="小说沙盘引擎 V2.3：LLM Agent + 记忆系统 + 叙事生成")
console = Console()


@app.command(help="运行一次模拟，生成事件日志、章节与一致性报告（本地文件输出）")
def main(
    world: str = typer.Option("dark_city_001", "--world", "-w", help="worlds/ 下的世界 ID（目录名），如 dark_city_001"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="scripted/heuristic/llm（最终版本默认 llm）"),
    ticks: Optional[int] = typer.Option(None, "--ticks", "-t", help="覆盖 chapter_goal.tick_limit"),
    seed: int = typer.Option(12345, "--seed", "-s", help="随机种子（可复现）"),
    temperature: Optional[float] = typer.Option(None, "--temperature", help="LLM 温度（仅 llm 模式，默认从 .env 读取）"),
    max_retries: int = typer.Option(2, "--max-retries", help="LLM 最大重试次数（仅 llm 模式）"),
    v2_phase: Optional[str] = typer.Option(
        "v2.3",
        "--v2-phase",
        help="V2 阶段模式：v2.1 / v2.2 / v2.3 / v2.4（v2.4 启用 Agent Sandbox）",
    ),
):
    project_root = Path(__file__).parent.parent

    # 加载配置
    cfg = Config(project_root)
    run_cfg = cfg.get_run_config()

    # 命令行参数优先，其次配置文件
    actual_mode = mode if mode else "llm"
    actual_ticks = ticks if ticks else run_cfg.ticks
    actual_temperature = temperature if temperature is not None else run_cfg.temperature

    # 检查 LLM 可用性
    if actual_mode == "llm" and not cfg.is_llm_available():
        console.print("[yellow][!] 警告：未检测到 LLM 配置，将自动切换到 heuristic 模式[/yellow]")
        console.print("[dim]   请在 .env 文件中配置 OPENAI_API_KEY[/dim]")
        actual_mode = "heuristic"

    if v2_phase is not None and v2_phase not in ("v2.1", "v2.2", "v2.3", "v2.4"):
        raise typer.BadParameter("--v2-phase 仅支持 v2.1 / v2.2 / v2.3 / v2.4")

    if v2_phase is None:
        v2_phase = "v2.3"

    worlds_dir = project_root / "worlds"

    # 加载世界配置
    world_config = WorldConfig.from_directory(worlds_dir / world)

    console.print(f"[bold]运行配置：[/bold] mode={actual_mode}, ticks={actual_ticks}, temperature={actual_temperature}")
    if v2_phase:
        console.print(f"[cyan]V2 阶段：[/cyan]{v2_phase}")
        if v2_phase in ("v2.1", "v2.2") and actual_mode != "llm":
            console.print("[yellow]提示：V2.1/V2.2 推荐使用 llm 模式验证 JSON 决策稳定性。[/yellow]")
    if cfg.is_llm_available():
        console.print(f"[dim]LLM 已就绪：{cfg.get_llm_config().model}[/dim]")

    # 运行模拟（SimulationRunner 现在已经集成了章节生成和一致性检查）
    runner = SimulationRunner(project_root=project_root, console=console)
    result = runner.run(
        world=world_config,
        mode=actual_mode,  # type: ignore
        ticks=actual_ticks,
        seed=seed,
        temperature=actual_temperature,
        max_retries=max_retries,
        v2_phase=v2_phase,  # type: ignore[arg-type]
    )

    console.print("\n[green][OK] 完成[/green]")
    console.print(f"输出目录：{result.sim_dir}")


if __name__ == "__main__":
    app()
