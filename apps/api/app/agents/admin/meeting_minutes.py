"""Admin meeting-minutes executor."""

from dataclasses import replace

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.p1_contracts import MeetingMinutesOutput, meeting_minutes_markdown
from app.core.json_guard import parse_json
from app.integrations.llm.providers import ChatProvider


class MeetingMinutesExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)

    async def execute(self, request: AgentRequest) -> AgentResult:
        prompt = {
            "role": "system",
            "content": (
                "请把当前会议内容整理成会议纪要。只能使用用户输入、对话历史和明确选择的资料；"
                "没有证据的负责人、日期、决议不要推断，owner、due_date、evidence 使用 null。"
                "只输出 JSON，顶层必须包含 topics、decisions、action_items；"
                "topics 为字符串数组，decisions 每项包含 decision、owner、due_date、evidence，"
                "action_items 每项包含 task、owner、due_date、evidence；不要输出 Markdown、代码围栏或额外字段。"
            ),
        }
        result = await self.chat.execute(
            replace(request, context=replace(request.context, messages=(prompt, *request.context.messages)))
        )
        output = parse_json(result.text, MeetingMinutesOutput)
        markdown = meeting_minutes_markdown(output)
        data = output.model_dump(mode="json")
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            validation={
                "valid": True,
                "schema": "meeting_minutes.v1",
                "source_count": len(result.citations),
            },
            artifact=AgentArtifact(
                type="meeting_minutes",
                title="会议纪要",
                content=markdown,
                data=data,
            ),
        )
