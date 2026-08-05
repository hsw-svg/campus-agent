import asyncio
from collections.abc import AsyncIterator

from app.agents.contracts import (
    AgentArtifact,
    AgentExecutionEvent,
    AgentRequest,
    AgentResult,
    progress_event,
    result_event,
)
from app.core.errors import AppError
from app.skills.contracts import SkillRegistry
from app.skills.learning_statistics import LearningStatisticsSkill
from app.skills.output_validation import OutputValidationSkill
from app.skills.table_parser import TableParserSkill


class LearningAnalysisExecutor:
    def __init__(self, skills: SkillRegistry | None = None) -> None:
        self.skills = skills or SkillRegistry(
            (TableParserSkill(), LearningStatisticsSkill(), OutputValidationSkill())
        )

    async def execute(self, request: AgentRequest) -> AgentResult:
        final_result: AgentResult | None = None
        async for event in self.stream(request):
            if event.type == "result" and event.result is not None:
                final_result = event.result
        if final_result is None:
            raise RuntimeError("learning_analysis_stream_did_not_complete")
        return final_result

    async def stream(self, request: AgentRequest) -> AsyncIterator[AgentExecutionEvent]:
        if not request.context.attachment_text.strip():
            raise AppError(
                code="learning_analysis_input_invalid",
                message="请选择一份匿名成绩、作业或练习统计表。",
                status_code=422,
            )
        parser = self.skills.get("table_parser")
        statistics = self.skills.get("learning_statistics")
        yield progress_event(
            step_id="learning-analysis-table",
            phase="context",
            state="active",
            label="正在读取匿名学习资料",
        )
        parsed = await asyncio.to_thread(
            parser.run,
            (request.context.attachment_text, request.context.attachment_filenames[0]),
        )
        yield progress_event(
            step_id="learning-analysis-table",
            phase="context",
            state="completed",
            label="匿名学习资料读取完成",
        )
        yield progress_event(
            step_id="learning-analysis-statistics",
            phase="model",
            state="active",
            label="正在计算班级学习统计",
        )
        analysis = await asyncio.to_thread(statistics.run, parsed)
        yield progress_event(
            step_id="learning-analysis-statistics",
            phase="model",
            state="completed",
            label="班级学习统计计算完成",
        )
        if not analysis.data["validation"]["valid"]:
            yield progress_event(
                step_id="learning-analysis-validation",
                phase="validation",
                state="failed",
                label="学情资料校验未通过",
            )
            raise AppError(
                code="learning_analysis_input_invalid",
                message="The learning table is incomplete or does not use an anonymous identifier.",
                status_code=422,
                details={"errors": analysis.data["validation"]["errors"]},
            )
        markdown = await asyncio.to_thread(
            self.skills.get("output_validation").run,
            analysis.markdown,
        )
        yield progress_event(
            step_id="learning-analysis-validation",
            phase="validation",
            state="completed",
            label="学情分析结果校验完成",
        )
        artifact = AgentArtifact(
            type="learning_analysis",
            title="班级整体学情分析",
            content=markdown,
            data=analysis.data,
        )
        yield progress_event(
            step_id="learning-analysis-artifact",
            phase="artifact",
            state="completed",
            label="学情分析报告已生成",
        )
        yield result_event(AgentResult(
            text=markdown,
            structured_data=analysis.data,
            validation=analysis.data["validation"],
            artifact=artifact,
        ))
