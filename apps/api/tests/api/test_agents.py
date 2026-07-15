from fastapi.testclient import TestClient

from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def test_agents_are_listed_per_role_and_never_cross_roles(client: TestClient) -> None:
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")

    student_agents = client.get("/api/agents", headers=auth(student)).json()
    teacher_agents = client.get("/api/agents", headers=auth(teacher)).json()

    assert student_agents["role"] == "student"
    assert teacher_agents["role"] == "teacher"

    student_ids = {agent["id"] for agent in student_agents["agents"]}
    teacher_ids = {agent["id"] for agent in teacher_agents["agents"]}

    assert "resume_helper" in student_ids
    assert "learning_analysis" in teacher_ids
    # The two whitelists must not overlap between roles.
    assert student_ids.isdisjoint(teacher_ids)


def test_creating_a_conversation_with_a_foreign_agent_is_rejected(client: TestClient) -> None:
    student = make_workspace(client, "student")

    # learning_analysis is a teacher-only agent; a student may not select it.
    response = client.post(
        "/api/conversations",
        json={"agent_id": "learning_analysis"},
        headers=auth(student),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "agent_not_available"


def test_streaming_with_a_forged_agent_id_is_rejected(client: TestClient) -> None:
    student = make_workspace(client, "student")
    conversation = client.post(
        "/api/conversations", json={}, headers=auth(student)
    ).json()

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "帮我看看", "agent_id": "learning_analysis"},
        headers=auth(student),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "agent_not_available"


def test_a_whitelisted_agent_can_be_selected(client: TestClient) -> None:
    student = make_workspace(client, "student")

    response = client.post(
        "/api/conversations",
        json={"agent_id": "resume_helper"},
        headers=auth(student),
    )

    assert response.status_code == 201
    assert response.json()["agent_id"] == "resume_helper"
