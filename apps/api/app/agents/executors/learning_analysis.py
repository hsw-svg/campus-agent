from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
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
        if not request.context.attachment_text.strip():
            raise AppError(
                code="learning_analysis_input_invalid",
                message="请选择一份匿名成绩、作业或练习统计表。",
                status_code=422,
            )
        parser = self.skills.get("table_parser")
        statistics = self.skills.get("learning_statistics")
        parsed = parser.run(
            (request.context.attachment_text, request.context.attachment_filenames[0])
        )
        analysis = statistics.run(parsed)
        if not analysis.data["validation"]["valid"]:
            raise AppError(
                code="learning_analysis_input_invalid",
                message="The learning table is incomplete or does not use an anonymous identifier.",
                status_code=422,
                details={"errors": analysis.data["validation"]["errors"]},
            )
        markdown = self.skills.get("output_validation").run(analysis.markdown)
        artifact = AgentArtifact(
            type="learning_analysis",
            title="班级整体学情分析",
            content=markdown,
            data=analysis.data,
        )
        return AgentResult(
            text=markdown,
            structured_data=analysis.data,
            validation=analysis.data["validation"],
            artifact=artifact,
        )
