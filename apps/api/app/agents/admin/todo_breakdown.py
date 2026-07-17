"""Admin todo-breakdown executor."""

from dataclasses import replace

from app.agents.contracts import AgentArtifact, AgentRequest, AgentResult
from app.agents.executors.generic_chat import GenericChatExecutor
from app.agents.p1_contracts import TodoBreakdownOutput, todo_breakdown_markdown
from app.core.json_guard import parse_json
from app.integrations.llm.providers import ChatProvider


class TodoBreakdownExecutor:
    def __init__(self, provider: ChatProvider) -> None:
        self.chat = GenericChatExecutor(provider)

    async def execute(self, request: AgentRequest) -> AgentResult:
        prompt = {
            "role": "system",
            "content": (
                "请把当前任务、会议内容或明确选择的行政资料拆解为可执行待办。"
                "只能使用现有证据；没有证据的负责人、日期、优先级或依据使用 null，不得臆造。"
                "只输出 JSON，顶层必须包含 items；每项必须包含 task、owner、due_date、priority、evidence；"
                "task 为非空字符串，其余可以为 null。不要输出 Markdown、代码围栏或额外字段。"
            ),
        }
        result = await self.chat.execute(
            replace(request, context=replace(request.context, messages=(prompt, *request.context.messages)))
        )
        output = parse_json(result.text, TodoBreakdownOutput)
        markdown = todo_breakdown_markdown(output)
        data = output.model_dump(mode="json")
        return AgentResult(
            text=markdown,
            structured_data=data,
            citations=result.citations,
            validation={
                "valid": True,
                "schema": "todo_breakdown.v1",
                "source_count": len(result.citations),
            },
            artifact=AgentArtifact(
                type="todo_breakdown",
                title="待办拆解",
                content=markdown,
                data=data,
            ),
        )
