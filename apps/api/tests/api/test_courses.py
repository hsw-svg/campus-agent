from fastapi.testclient import TestClient


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
