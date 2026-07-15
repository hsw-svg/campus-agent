from fastapi.testclient import TestClient

from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def create_conversation(client: TestClient, token: str) -> dict:
    response = client.post("/api/conversations", json={}, headers=auth(token))
    assert response.status_code == 201
    return response.json()


def test_conversations_are_scoped_to_their_workspace(client: TestClient) -> None:
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")
    student_conversation = create_conversation(client, student)
    create_conversation(client, teacher)

    student_list = client.get("/api/conversations", headers=auth(student)).json()
    teacher_list = client.get("/api/conversations", headers=auth(teacher)).json()

    assert [item["id"] for item in student_list] == [student_conversation["id"]]
    assert student_conversation["id"] not in {item["id"] for item in teacher_list}


def test_another_workspace_cannot_read_a_conversation_by_id(client: TestClient) -> None:
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")
    student_conversation = create_conversation(client, student)

    response = client.get(
        f"/api/conversations/{student_conversation['id']}", headers=auth(teacher)
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


def test_another_workspace_cannot_read_messages_by_id(client: TestClient) -> None:
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")
    student_conversation = create_conversation(client, student)

    response = client.get(
        f"/api/conversations/{student_conversation['id']}/messages", headers=auth(teacher)
    )

    assert response.status_code == 404


def test_another_workspace_cannot_delete_a_conversation(client: TestClient) -> None:
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")
    student_conversation = create_conversation(client, student)

    forged = client.delete(
        f"/api/conversations/{student_conversation['id']}", headers=auth(teacher)
    )
    assert forged.status_code == 404

    owned = client.delete(
        f"/api/conversations/{student_conversation['id']}", headers=auth(student)
    )
    assert owned.status_code == 204


def test_deleting_a_workspace_cascades_to_its_conversations(client: TestClient) -> None:
    student = make_workspace(client, "student")
    conversation = create_conversation(client, student)

    assert client.delete("/api/workspaces/current", headers=auth(student)).status_code == 204

    # A new workspace for the same role starts empty; the old rows are gone.
    fresh = make_workspace(client, "student")
    assert client.get("/api/conversations", headers=auth(fresh)).json() == []
    assert (
        client.get(
            f"/api/conversations/{conversation['id']}", headers=auth(fresh)
        ).status_code
        == 404
    )
