from uuid import UUID

from fastapi.testclient import TestClient

from app.agents.models import AgentRun
from app.artifacts.models import Artifact
from app.conversations.models import Message


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def make_workspace(client: TestClient, role: str = "teacher") -> str:
    response = client.post("/api/workspaces", json={"role": role})
    assert response.status_code == 201
    return response.json()["token"]


def test_course_tasks_are_grouped_and_independent_tasks_remain_unassigned(client: TestClient) -> None:
    token = make_workspace(client)
    course = client.post("/api/courses", json={"name": "Python 程序设计"}, headers=auth(token))
    assert course.status_code == 201
    course_id = course.json()["id"]

    linked = client.post("/api/conversations", json={"course_id": course_id}, headers=auth(token))
    independent = client.post("/api/conversations", json={}, headers=auth(token))
    assert linked.status_code == 201
    assert linked.json()["course_id"] == course_id
    assert independent.status_code == 201
    assert independent.json()["course_id"] is None

    conversations = client.get("/api/conversations", headers=auth(token)).json()
    assert {item["course_id"] for item in conversations} == {course_id, None}


def test_course_cannot_be_used_across_workspaces(client: TestClient) -> None:
    first = make_workspace(client)
    second = make_workspace(client)
    course = client.post("/api/courses", json={"name": "仅属于第一空间"}, headers=auth(first)).json()

    response = client.post("/api/conversations", json={"course_id": course["id"]}, headers=auth(second))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "course_not_found"


def test_course_agent_history_is_scoped_and_includes_text_and_artifact_results(client: TestClient) -> None:
    token = make_workspace(client)
    workspace = client.get("/api/workspaces/current", headers=auth(token)).json()
    course = client.post("/api/courses", json={"name": "历史聚合课程"}, headers=auth(token)).json()
    conversation = client.post(
        "/api/conversations",
        json={"course_id": course["id"]},
        headers=auth(token),
    ).json()

    with client.app.state.session_factory() as session:
        artifact = Artifact(
            workspace_id=UUID(workspace["id"]),
            conversation_id=UUID(conversation["id"]),
            type="learning_analysis",
            title="第一次学情分析",
            content="# 学情分析",
            data={"weak_points": []},
            format="markdown",
        )
        session.add(artifact)
        session.flush()
        session.add(
            AgentRun(
                workspace_id=UUID(workspace["id"]),
                conversation_id=UUID(conversation["id"]),
                agent_id="learning_analysis",
                selection_source="manual",
                confidence=1.0,
                reason="教师主动发起学情分析",
                status="completed",
                artifact_id=artifact.id,
                artifact_status="completed",
            )
        )
        result_message = Message(
            workspace_id=UUID(workspace["id"]),
            conversation_id=UUID(conversation["id"]),
            role="assistant",
            content="已根据本次学情分析生成课程迭代建议。",
            agent_id="course_iteration",
        )
        session.add(result_message)
        session.flush()
        session.add(
            AgentRun(
                workspace_id=UUID(workspace["id"]),
                conversation_id=UUID(conversation["id"]),
                agent_id="course_iteration",
                selection_source="rule",
                confidence=0.9,
                reason="用户要求课程迭代",
                status="completed",
                result_message_id=result_message.id,
            )
        )
        session.commit()

    history = client.get(
        f"/api/courses/{course['id']}/agent-history",
        headers=auth(token),
    )
    assert history.status_code == 200
    assert {item["agent_id"] for item in history.json()} == {"learning_analysis", "course_iteration"}
    artifact_item = next(item for item in history.json() if item["artifact"] is not None)
    text_item = next(item for item in history.json() if item["artifact"] is None)
    assert artifact_item["artifact"]["title"] == "第一次学情分析"
    assert text_item["summary"] == "已根据本次学情分析生成课程迭代建议。"

    other_token = make_workspace(client)
    forbidden = client.get(
        f"/api/courses/{course['id']}/agent-history",
        headers=auth(other_token),
    )
    assert forbidden.status_code == 404
