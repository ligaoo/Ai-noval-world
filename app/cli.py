from pathlib import Path
from typing import Optional

import os
import sys

# Windows 编码修复：强制使用 UTF-8，避免替换 stdout/stderr 导致 logging 持有已关闭 stream
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    os.environ["PYTHONIOENCODING"] = "utf-8"

import typer
from rich.console import Console

from app.config import Config
from app.models.quality_controls import QualityControls
from app.models.world import WorldConfig
from app.runner.simulation_runner import SimulationRunner


app = typer.Typer(no_args_is_help=True, help="小说沙盘引擎 正式版V1：LLM Agent + 记忆系统 + 叙事生成")
console = Console()


@app.command(help="运行一次模拟，生成事件日志、章节与一致性报告（本地文件输出）")
def main(
    world: str = typer.Option("dark_city_001", "--world", "-w", help="worlds/ 下的世界 ID（目录名），如 dark_city_001"),
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="scripted/heuristic/llm（最终版本默认 llm）"),
    ticks: Optional[int] = typer.Option(None, "--ticks", "-t", help="覆盖 chapter_goal.tick_limit"),
    seed: int = typer.Option(12345, "--seed", "-s", help="随机种子（可复现）"),
    temperature: Optional[float] = typer.Option(None, "--temperature", help="LLM 温度（仅 llm 模式，默认从 .env 读取）"),
    max_retries: int = typer.Option(2, "--max-retries", help="LLM 最大重试次数（仅 llm 模式）"),
    version: Optional[str] = typer.Option(
        "正式版V1",
        "--version",
        help="运行版本：正式版V1",
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

    if version is not None and version != "正式版V1":
        raise typer.BadParameter("--version 仅支持 正式版V1")

    if version is None:
        version = "正式版V1"

    worlds_dir = project_root / "worlds"

    # 加载世界配置
    world_config = WorldConfig.from_directory(worlds_dir / world)

    console.print(f"[bold]运行配置：[/bold] mode={actual_mode}, ticks={actual_ticks}, temperature={actual_temperature}")
    if version:
        console.print(f"[cyan]运行版本：[/cyan]{version}")
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
        version=version,  # type: ignore[arg-type]
        quality_controls=QualityControls(),
    )

    console.print("\n[green][OK] 完成[/green]")
    console.print(f"输出目录：{result.sim_dir}")


if __name__ == "__main__":
    app()
