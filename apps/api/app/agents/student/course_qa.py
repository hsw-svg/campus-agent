"""Student course-material question answering executor."""

from dataclasses import replace

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.p1_contracts import CourseQAOutput, course_qa_markdown
from app.core.json_guard import parse_json
from app.integrations.llm.providers import ChatProvider


class CourseQAExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)

    async def execute(self, request: AgentRequest) -> AgentResult:
        prompt = {
            "role": "system",
            "content": (
                "请回答用户关于已选择课程资料的问题。只能使用提供的资料和对话内容；"
                "资料没有答案时，在 answer 中明确说明，不要补造事实。"
                "只输出 JSON，顶层必须包含 answer、key_points、follow_up_questions；"
                "answer 为非空字符串，其余均为字符串数组。不要输出 Markdown、代码围栏或额外字段。"
            ),
        }
        result = await self.chat.execute(
            replace(request, context=replace(request.context, messages=(prompt, *request.context.messages)))
        )
        output = parse_json(result.text, CourseQAOutput)
        markdown = course_qa_markdown(output)
        data = output.model_dump(mode="json")
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            validation={
                "valid": True,
                "schema": "course_qa.v1",
                "source_count": len(result.citations),
            },
            artifact=AgentArtifact(
                type="course_qa",
                title="课程资料问答",
                content=markdown,
                data=data,
            ),
        )
