"""Evidence-bound student resume analysis executor."""

import json
from dataclasses import replace
from typing import Any

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.p1_contracts import ResumeAnalysisOutput, resume_analysis_markdown
from app.core.errors import AppError, TaskError
from app.core.json_guard import parse_json
from app.integrations.llm.providers import ChatProvider


JSON_RESPONSE_FORMAT = {"type": "json_object"}


class ResumeHelperExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)

    async def execute(self, request: AgentRequest) -> AgentResult:
        input_data = _parse_controlled_input(request.content)
        prompt = {
            "role": "system",
            "content": (
                "你是学生简历优化助手。只允许使用已选择简历中的事实，以及本次请求 JSON 中"
                "由后端生成的课程学习证据。不得新增或夸大项目、实习、证书、成绩、技能、职责"
                "或量化成果。信息不足时必须写“待补充”，不能猜测。课程尚未完成的内容不得描述"
                "为已掌握成果；薄弱知识点只能用于提出学习建议，不能包装成优势。每个问题都要写"
                "出 evidence。优化后草稿必须覆盖简历已有主要模块，并只做重组、压缩和润色。"
                "只输出 JSON，顶层字段必须为 overall_summary、issues、section_suggestions、"
                "course_capability_matches、job_match、optimized_resume_sections、evidence_notice。"
                "issues 每项包含 section、severity(high|medium|low)、problem、evidence、suggestion；"
                "section_suggestions 每项包含 section、suggestions、rewrite_examples；"
                "course_capability_matches 每项包含 course_name、progress_evidence、capability、"
                "suggested_wording；job_match 包含 matched_keywords、gap_keywords、guidance；"
                "optimized_resume_sections 每项包含 heading、markdown。不要输出 Markdown 代码围栏"
                "或额外字段。若未提供岗位/JD，关键词数组可为空并给出通用 guidance。"
            ),
        }
        structured_request = replace(
            request,
            context=replace(
                request.context,
                messages=(prompt, *request.context.messages),
            ),
        )
        result = await self.chat.execute(structured_request)
        try:
            output = parse_json(result.text, ResumeAnalysisOutput)
        except TaskError as error:
            if error.code != "invalid_structured_output":
                raise
            repair_request = replace(
                structured_request,
                context=replace(
                    structured_request.context,
                    messages=(
                        *structured_request.context.messages,
                        {"role": "assistant", "content": result.text},
                        {
                            "role": "user",
                            "content": (
                                "上一次输出未通过 JSON 结构校验。请仅修正输出结构，不添加、"
                                "删除或改变任何简历事实、课程证据和分析结论。返回符合系统消息"
                                "中全部字段要求的完整 JSON 对象，不要输出解释或代码围栏。"
                            ),
                        },
                    ),
                ),
            )
            result = await self.chat.execute(
                repair_request,
                response_format=JSON_RESPONSE_FORMAT,
            )
            output = parse_json(result.text, ResumeAnalysisOutput)
        _validate_course_evidence(output, input_data)
        markdown = resume_analysis_markdown(output)
        report = output.model_dump(mode="json")
        data = {
            "schema_version": "resume_analysis.v1",
            "input": input_data,
            "report": report,
        }
        target_role = input_data.get("target_role")
        title = f"{target_role}简历优化报告" if target_role else "通用简历优化报告"
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            validation={
                "valid": True,
                "schema": "resume_analysis.v1",
                "source_count": len(result.citations),
            },
            artifact=AgentArtifact(
                type="resume_analysis",
                title=title,
                content=markdown,
                data=data,
            ),
        )


def _parse_controlled_input(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise AppError(
            code="resume_analysis_input_invalid",
            message="Resume analysis input is invalid.",
            status_code=422,
        ) from error
    if not isinstance(value, dict):
        raise AppError(
            code="resume_analysis_input_invalid",
            message="Resume analysis input is invalid.",
            status_code=422,
        )
    required = {"resume_attachment_id", "resume_filename", "selected_courses"}
    if not required.issubset(value) or not isinstance(value["selected_courses"], list):
        raise AppError(
            code="resume_analysis_input_invalid",
            message="Resume analysis input is invalid.",
            status_code=422,
        )
    return value


def _validate_course_evidence(
    output: ResumeAnalysisOutput, input_data: dict[str, Any]
) -> None:
    selected_courses = input_data.get("selected_courses")
    allowed_names = {
        item["name"]
        for item in selected_courses
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and item["name"].strip()
    }
    unsupported = sorted(
        {
            item.course_name
            for item in output.course_capability_matches
            if item.course_name not in allowed_names
        }
    )
    if unsupported:
        raise AppError(
            code="resume_analysis_evidence_invalid",
            message="The model used course evidence that was not selected.",
            status_code=422,
            details={"course_names": unsupported},
        )
