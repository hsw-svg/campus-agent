"""Student personal tutoring executor."""

from dataclasses import replace

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.p1_contracts import PersonalTutorOutput, personal_tutor_markdown
from app.core.json_guard import parse_json
from app.integrations.llm.providers import ChatProvider


class PersonalTutorExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)

    async def execute(self, request: AgentRequest) -> AgentResult:
        prompt = {
            "role": "system",
            "content": (
                "请针对用户明确选择的错题、作业或薄弱点材料进行辅导。只能使用提供的资料和对话内容；"
                "材料没有证据的内容不要臆造，无法判断时明确说明。"
                "只输出 JSON，顶层必须包含 diagnosis、explanation、mistakes、practice、follow_up_questions；"
                "diagnosis 和 explanation 为非空字符串，其余均为字符串数组。不要输出 Markdown、"
                "代码围栏或额外字段。"
            ),
        }
        result = await self.chat.execute(
            replace(request, context=replace(request.context, messages=(prompt, *request.context.messages)))
        )
        output = parse_json(result.text, PersonalTutorOutput)
        markdown = personal_tutor_markdown(output)
        data = output.model_dump(mode="json")
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            validation={
                "valid": True,
                "schema": "personal_tutor.v1",
                "source_count": len(result.citations),
            },
            artifact=AgentArtifact(
                type="personal_tutor",
                title="个性化答疑",
                content=markdown,
                data=data,
            ),
        )
