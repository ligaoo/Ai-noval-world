from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.models.blueprint import (
    ActPlan,
    ChapterFunctionPlan,
    ChapterWordBudget,
    NovelBlueprint,
    NovelProgress,
)
from app.services.opening_chapter_policy_service import OpeningChapterPolicyService
from app.services.chapter_clue_budget_controller import ChapterClueBudgetController
from app.services.trace_service import TraceService


@dataclass
class ProductionResult:
    """生产结果"""
    novel_id: str
    total_chapters: int = 0
    total_words: int = 0
    status: str = "success"
    start_time: str = ""
    end_time: str = ""
    chapter_results: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class ChapterFunctionResolver:
    """
    章节功能解析器
    根据当前进度和蓝图决定每章的功能
    """

    def resolve(
        self,
        blueprint: NovelBlueprint,
        progress: NovelProgress,
        thread_recommendations: List[Dict[str, Any]] = None,
    ) -> ChapterFunctionPlan:
        """解析下一章的功能"""
        chapter_no = progress.current_chapter + 1
        act = blueprint.get_act_for_chapter(chapter_no)

        if not act:
            return self._create_default_chapter_plan(chapter_no)

        chapter_function = self._determine_chapter_function(act, chapter_no, thread_recommendations)

        target_words = self._calculate_target_words(blueprint, act, chapter_no)

        return ChapterFunctionPlan(
            chapter_id=f"ch_{chapter_no:03d}",
            chapter_no=chapter_no,
            target_words=target_words,
            act_id=act.act_id,
            chapter_function=chapter_function,
            primary_thread="",
            secondary_threads=[],
            genre_context={
                "genre_id": blueprint.genre_id,
                "genre_stage": act.genre_stage,
            },
            must_not_reveal=act.must_not_reveal,
        )

    def _determine_chapter_function(
        self,
        act: ActPlan,
        chapter_no: int,
        thread_recommendations: List[Dict[str, Any]] = None,
    ) -> str:
        """确定章节功能"""
        if act.act_id == "act_1":
            return self._act1_function(act, chapter_no)
        elif act.act_id == "act_2":
            return self._act2_function(act, chapter_no, thread_recommendations)
        elif act.act_id == "act_3":
            return self._act3_function(act, chapter_no, thread_recommendations)
        else:
            return act.function

    def _act1_function(self, act: ActPlan, chapter_no: int) -> str:
        """第一幕功能"""
        if chapter_no <= 3:
            return "建立异常、主角卷入、打开核心悬念"
        else:
            return "推进线索，加深主角与事件的联系"

    def _act2_function(
        self,
        act: ActPlan,
        chapter_no: int,
        thread_recommendations: List[Dict[str, Any]] = None,
    ) -> str:
        """第二幕功能"""
        if thread_recommendations:
            for rec in thread_recommendations:
                if rec.get("type") == "prioritize_thread":
                    return f"推进悬念: {rec.get('thread_id', '')}"
        return "调查推进、误导升级、灵异规则显形"

    def _act3_function(
        self,
        act: ActPlan,
        chapter_no: int,
        thread_recommendations: List[Dict[str, Any]] = None,
    ) -> str:
        """第三幕功能"""
        return "真相揭示、终局选择、余波收束"

    def _calculate_target_words(
        self,
        blueprint: NovelBlueprint,
        act: ActPlan,
        chapter_no: int,
    ) -> int:
        """计算目标字数"""
        act_words = act.word_range[1] - act.word_range[0]
        act_chapters = act.chapter_range[1] - act.chapter_range[0] + 1
        return max(3000, min(4000, act_words // act_chapters))

    def _create_default_chapter_plan(self, chapter_no: int) -> ChapterFunctionPlan:
        """创建默认章节计划"""
        return ChapterFunctionPlan(
            chapter_id=f"ch_{chapter_no:03d}",
            chapter_no=chapter_no,
            target_words=3500,
            act_id="act_default",
            chapter_function="继续推进故事",
        )


class NovelProductionOrchestrator:
    """
    V5.5 NovelProductionOrchestrator 全书生产调度器
    从"章节生成器"升级为"全书生产器"
    """

    def __init__(
        self,
        project_dir: Path,
        blueprint: NovelBlueprint,
        world_bible: Dict[str, Any],
        quality_policy: Dict[str, Any],
        characters: List[Dict[str, Any]],
        available_clues: List[Dict[str, Any]] = None,
        trace_service: Optional[TraceService] = None,
    ):
        self.project_dir = project_dir
        self.blueprint = blueprint
        self.world_bible = world_bible
        self.quality_policy = quality_policy
        self.characters = characters
        self.available_clues = available_clues or []
        self.trace_service = trace_service

        self.production_dir = project_dir / "productions"
        self.production_dir.mkdir(exist_ok=True)

        self.progress = NovelProgress(
            novel_id=blueprint.novel_id,
            target_chapters=blueprint.target_chapters,
            target_words=blueprint.target_words,
        )

        self.chapter_function_resolver = ChapterFunctionResolver()

        # V1.1 新增服务
        self.opening_policy_service = OpeningChapterPolicyService(
            quality_policy=quality_policy,
            characters=characters,
        )
        self.clue_budget_controller = ChapterClueBudgetController(
            quality_policy=quality_policy,
        )

    def start_production(
        self,
        chapter_generator: Callable,
        quality_evaluator: Callable,
        rewrite_optimizer: Callable,
        thread_manager: Callable,
        max_chapters: int = None,
        max_words: int = None,
    ) -> ProductionResult:
        """
        启动全书生产
        循环生成章节直到达到目标
        """
        start_time = datetime.now()
        self.progress.status = "running"

        chapter_limit = max_chapters or self.blueprint.target_chapters
        word_limit = max_words or self.blueprint.target_words

        result = ProductionResult(
            novel_id=self.blueprint.novel_id,
            start_time=start_time.isoformat(),
        )

        try:
            while (
                self.progress.current_chapters < chapter_limit
                and self.progress.current_words < word_limit
            ):
                chapter_result = self._produce_next_chapter(
                    chapter_generator,
                    quality_evaluator,
                    rewrite_optimizer,
                    thread_manager,
                )

                result.chapter_results.append(chapter_result)

                if chapter_result.get("status") == "failed":
                    self.progress.status = "failed"
                    result.error = f"章节 {self.progress.current_chapter + 1} 生成失败"
                    break

                self._update_progress(chapter_result)
                self._save_progress()

                if self._should_stop_production(chapter_result):
                    break

            self.progress.status = "completed"
            result.total_chapters = self.progress.current_chapter
            result.total_words = self.progress.current_words

        except Exception as e:
            self.progress.status = "failed"
            result.error = str(e)
            if self.trace_service:
                self.trace_service.add_error("production_error", str(e))

        finally:
            result.end_time = datetime.now().isoformat()
            self._save_production_result(result)

        return result

    def _produce_next_chapter(
        self,
        chapter_generator: Callable,
        quality_evaluator: Callable,
        rewrite_optimizer: Callable,
        thread_manager: Callable,
    ) -> Dict[str, Any]:
        """生产下一章"""
        chapter_no = self.progress.current_chapter + 1

        # 1. 解析章节功能
        chapter_function = self.chapter_function_resolver.resolve(
            self.blueprint,
            self.progress,
        )

        # V1.1 2. 应用第一章策略（如果是第一章）
        chapter_plan = chapter_function.to_dict()
        if chapter_no == 1:
            chapter_plan = self.opening_policy_service.apply(
                chapter_plan=chapter_plan,
                world_bible=self.world_bible,
            )

        # V1.1 3. 应用线索预算
        chapter_plan = self.clue_budget_controller.apply(
            chapter_plan=chapter_plan,
            available_clues=self.available_clues,
        )

        # 4. 生成章节（传入增强后的 chapter_plan）
        chapter_result = chapter_generator(
            chapter_no=chapter_no,
            chapter_function=chapter_function,
            chapter_plan=chapter_plan,
        )

        if not chapter_result.get("success"):
            return {
                "chapter_no": chapter_no,
                "status": "failed",
                "error": chapter_result.get("error"),
            }

        # 3. 质量评估
        quality_result = quality_evaluator(
            chapter_no=chapter_no,
            chapter_draft=chapter_result.get("draft", ""),
        )

        # 4. 自动修稿（如果需要）
        if quality_result.get("rewrite_recommended"):
            rewrite_result = rewrite_optimizer(
                chapter_no=chapter_no,
                quality_report=quality_result,
            )
            if rewrite_result.get("accepted"):
                chapter_result["draft"] = rewrite_result.get("rewritten_draft")

        # 5. 更新悬念管理
        thread_result = thread_manager(
            chapter_no=chapter_no,
            chapter_summary=chapter_result.get("summary", {}),
        )

        return {
            "chapter_no": chapter_no,
            "status": "success",
            "words": chapter_result.get("word_count", 0),
            "quality_score": quality_result.get("overall_score", 0),
            "chapter_function": chapter_function.chapter_function,
        }

    def _update_progress(self, chapter_result: Dict[str, Any]) -> None:
        """更新进度"""
        self.progress.current_chapter = chapter_result.get("chapter_no", 0)
        self.progress.current_words += chapter_result.get("words", 0)
        self.progress.progress_ratio = self.progress.current_words / self.blueprint.target_words

        current_act = self.blueprint.get_act_for_chapter(self.progress.current_chapter)
        if current_act:
            self.progress.current_act = current_act.act_id

    def _should_stop_production(self, chapter_result: Dict[str, Any]) -> bool:
        """判断是否停止生产"""
        if self.progress.current_words >= self.blueprint.target_words:
            return True

        if self.progress.current_chapter >= self.blueprint.target_chapters:
            return True

        return False

    def pause_production(self) -> None:
        """暂停生产"""
        self.progress.status = "paused"
        self._save_progress()

    def resume_production(
        self,
        chapter_generator: Callable,
        quality_evaluator: Callable,
        rewrite_optimizer: Callable,
        thread_manager: Callable,
    ) -> ProductionResult:
        """恢复生产"""
        if self.progress.status != "paused":
            raise ValueError("只能恢复已暂停的生产")

        self.progress.status = "running"
        return self.start_production(
            chapter_generator,
            quality_evaluator,
            rewrite_optimizer,
            thread_manager,
        )

    def get_production_status(self) -> Dict[str, Any]:
        """获取生产状态"""
        return self.progress.to_dict()

    def _save_progress(self) -> None:
        """保存进度"""
        progress_file = self.production_dir / "novel_progress.json"
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress.to_dict(), f, ensure_ascii=False, indent=2)

    def _save_production_result(self, result: ProductionResult) -> None:
        """保存生产结果"""
        result_file = self.production_dir / "production_result.json"
        result_dict = result.__dict__.copy()
        result_dict["chapter_results"] = result.chapter_results
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)


class ChapterWordBudgetController:
    """
    章节字数控制器
    控制每章的字数在合理范围内
    """

    def __init__(
        self,
        blueprint: NovelBlueprint,
        progress: NovelProgress,
    ):
        self.blueprint = blueprint
        self.progress = progress

    def get_budget_for_chapter(self, chapter_no: int) -> ChapterWordBudget:
        """获取章节字数预算"""
        act = self.blueprint.get_act_for_chapter(chapter_no)

        if act:
            act_words = act.word_range[1] - act.word_range[0]
            act_chapters = act.chapter_range[1] - act.chapter_range[0] + 1
            target = max(3000, min(4200, act_words // act_chapters))
        else:
            target = 3500

        return ChapterWordBudget(
            target_words=target,
            min_words=int(target * 0.85),
            max_words=int(target * 1.2),
        )

    def check_word_count(self, budget: ChapterWordBudget, actual_words: int) -> Dict[str, Any]:
        """检查字数是否合理"""
        budget.current_draft_words = actual_words

        status = budget.status
        suggestion = ""

        if status == "too_short":
            suggestion = "章节过短，建议扩写已有情绪/场景"
        elif status == "too_long":
            suggestion = "章节过长，建议压缩重复描写"
        else:
            suggestion = "字数合理"

        return {
            "budget": budget.to_dict(),
            "actual_words": actual_words,
            "status": status,
            "suggestion": suggestion,
        }
