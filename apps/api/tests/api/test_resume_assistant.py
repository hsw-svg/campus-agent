import json
from collections.abc import AsyncIterator, Sequence
from pathlib import Path

from fastapi.testclient import TestClient

from app.integrations.storage.local import LocalObjectStorage
from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def events_from_stream(text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event_line, data_line = block.split("\n", 1)
        events.append(
            (
                event_line.removeprefix("event: "),
                json.loads(data_line.removeprefix("data: ")),
            )
        )
    return events


class FakeResumeProvider:
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(
        self,
        messages: Sequence[dict[str, str]],
        *,
        response_format: dict | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield json.dumps(
            {
                "overall_summary": "内容真实，但能力表达需要更聚焦。",
                "issues": [
                    {
                        "section": "项目经历",
                        "severity": "high",
                        "problem": "职责描述过于笼统。",
                        "evidence": "原简历仅写“参与系统开发”。",
                        "suggestion": "补充本人负责的具体环节；缺失指标标为待补充。",
                    }
                ],
                "section_suggestions": [
                    {
                        "section": "专业能力",
                        "suggestions": ["结合已完成课程章节描述学习基础。"],
                        "rewrite_examples": ["完成大学英语阅读章节学习，进度依据见课程记录。"],
                    }
                ],
                "course_capability_matches": [
                    {
                        "course_name": "大学英语",
                        "progress_evidence": "已开始学习，进度 0%。",
                        "capability": "持续学习与语言基础",
                        "suggested_wording": "正在学习大学英语相关课程。",
                    }
                ],
                "job_match": {
                    "matched_keywords": ["沟通"],
                    "gap_keywords": ["项目指标"],
                    "guidance": "没有证据的指标使用待补充。",
                },
                "optimized_resume_sections": [
                    {
                        "heading": "个人概况",
                        "markdown": "求职方向：产品助理\n\n项目成果：待补充",
                    }
                ],
                "evidence_notice": "本报告只使用当前简历和所选课程记录。",
            },
            ensure_ascii=False,
        )


def upload_resume(
    client: TestClient, token: str, filename: str = "resume.md", content: str = "# 张同学\n参与校园项目"
) -> dict:
    response = client.post(
        "/api/workspaces/current/attachments",
        files={"file": (filename, content, "text/markdown")},
        headers=auth(token),
    )
    assert response.status_code == 201
    return response.json()


def test_resume_profile_analysis_history_and_delete_are_workspace_scoped(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path / "storage")
    token = make_workspace(client, "student")
    attachment = upload_resume(client, token)

    profile = client.put(
        "/api/resume-assistant/profile",
        json={"attachment_id": attachment["id"]},
        headers=auth(token),
    )
    assert profile.status_code == 200
    assert profile.json()["current_resume"]["filename"] == "resume.md"

    defaults = client.post("/api/courses/defaults", headers=auth(token))
    assert defaults.status_code == 200
    course = defaults.json()[0]
    started = client.post(
        f"/api/courses/{course['id']}/start", headers=auth(token)
    )
    assert started.status_code == 200

    provider = FakeResumeProvider()
    client.app.state.chat_provider = provider
    response = client.post(
        "/api/resume-assistant/analyses/stream",
        json={
            "attachment_id": attachment["id"],
            "target_role": "产品助理",
            "job_description": "重视沟通和项目执行",
            "selected_course_ids": [course["id"]],
        },
        headers=auth(token),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    artifact_event = next(
        data
        for name, data in events
        if name == "artifact" and data.get("type") == "resume_analysis"
    )
    assert artifact_event["data"]["schema_version"] == "resume_analysis.v1"
    assert artifact_event["data"]["input"]["target_role"] == "产品助理"
    assert provider.calls
    serialized_prompt = json.dumps(provider.calls, ensure_ascii=False)
    assert "大学英语" in serialized_prompt
    assert "参与校园项目" in serialized_prompt

    history = client.get("/api/resume-assistant/analyses", headers=auth(token))
    assert history.status_code == 200
    assert len(history.json()) == 1
    item = history.json()[0]
    assert item["target_role"] == "产品助理"
    assert item["resume_filename"] == "resume.md"
    assert item["artifact"]["data"]["report"]["optimized_resume_sections"]

    deleted = client.delete(
        f"/api/resume-assistant/analyses/{item['run_id']}",
        headers=auth(token),
    )
    assert deleted.status_code == 204
    assert client.get(
        "/api/resume-assistant/analyses", headers=auth(token)
    ).json() == []
    restored_profile = client.get(
        "/api/resume-assistant/profile", headers=auth(token)
    )
    assert restored_profile.json()["current_resume"]["id"] == attachment["id"]


def test_resume_profile_rejects_empty_or_foreign_attachment(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path / "storage")
    first_token = make_workspace(client, "student")
    second_token = make_workspace(client, "student")
    empty = upload_resume(client, first_token, content="")

    empty_response = client.put(
        "/api/resume-assistant/profile",
        json={"attachment_id": empty["id"]},
        headers=auth(first_token),
    )
    assert empty_response.status_code == 422
    assert empty_response.json()["error"]["code"] == "resume_attachment_text_unavailable"

    foreign_response = client.put(
        "/api/resume-assistant/profile",
        json={"attachment_id": empty["id"]},
        headers=auth(second_token),
    )
    assert foreign_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == "resume_attachment_not_found"


def test_resume_analysis_rejects_unstarted_course_and_non_student(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path / "storage")
    student_token = make_workspace(client, "student")
    attachment = upload_resume(client, student_token)
    client.put(
        "/api/resume-assistant/profile",
        json={"attachment_id": attachment["id"]},
        headers=auth(student_token),
    )
    courses = client.post("/api/courses/defaults", headers=auth(student_token)).json()

    response = client.post(
        "/api/resume-assistant/analyses/stream",
        json={
            "attachment_id": attachment["id"],
            "selected_course_ids": [courses[0]["id"]],
        },
        headers=auth(student_token),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "resume_course_not_started"

    teacher_token = make_workspace(client, "teacher")
    forbidden = client.get(
        "/api/resume-assistant/profile", headers=auth(teacher_token)
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "resume_assistant_forbidden"
