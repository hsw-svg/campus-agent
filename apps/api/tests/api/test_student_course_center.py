from uuid import UUID

from fastapi.testclient import TestClient

from app.artifacts.models import Artifact


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


def make_workspace(client: TestClient, role: str = "student") -> str:
    response = client.post("/api/workspaces", json={"role": role})
    assert response.status_code == 201
    return response.json()["token"]


def test_default_courses_are_idempotent_and_do_not_overwrite_changes(client: TestClient) -> None:
    token = make_workspace(client)

    first = client.post("/api/courses/defaults", headers=auth(token))
    second = client.post("/api/courses/defaults", headers=auth(token))

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(first.json()) == 6
    assert {item["name"] for item in first.json()} >= {"大学英语", "形势与政策"}
    assert {item["id"] for item in first.json()} == {item["id"] for item in second.json()}

    english = next(item for item in first.json() if item["name"] == "大学英语")
    renamed = client.patch(
        f"/api/courses/{english['id']}",
        json={"name": "我的大学英语", "description": english["description"]},
        headers=auth(token),
    )
    assert renamed.status_code == 200

    third = client.post("/api/courses/defaults", headers=auth(token))
    assert len(third.json()) == 6
    assert any(item["name"] == "我的大学英语" for item in third.json())


def test_default_courses_are_student_only(client: TestClient) -> None:
    token = make_workspace(client, "teacher")

    response = client.post("/api/courses/defaults", headers=auth(token))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "student_course_center_forbidden"


def test_course_start_chapter_and_completion_persist_progress(client: TestClient) -> None:
    token = make_workspace(client)
    course = client.post("/api/courses/defaults", headers=auth(token)).json()[0]
    detail = client.get(f"/api/courses/{course['id']}", headers=auth(token)).json()
    first_chapter = detail["chapters"][0]
    second_chapter = detail["chapters"][1]

    started = client.post(f"/api/courses/{course['id']}/start", headers=auth(token))
    assert started.status_code == 200
    assert started.json()["started"] is True
    assert started.json()["progress_percent"] == 0
    assert started.json()["current_chapter_id"] == first_chapter["id"]

    selected = client.post(
        f"/api/courses/{course['id']}/chapters/{second_chapter['id']}/start",
        headers=auth(token),
    )
    assert selected.status_code == 200
    assert selected.json()["current_chapter_id"] == second_chapter["id"]

    completed = client.post(
        f"/api/courses/{course['id']}/chapters/{second_chapter['id']}/complete",
        headers=auth(token),
    )
    assert completed.status_code == 200
    assert completed.json()["progress_percent"] == 25
    assert next(item for item in completed.json()["chapters"] if item["id"] == second_chapter["id"])["completed"] is True

    refreshed = client.get(f"/api/courses/{course['id']}", headers=auth(token))
    assert refreshed.json()["progress_percent"] == 25


def test_chapter_conversation_validation_and_evidence_scoping(client: TestClient) -> None:
    token = make_workspace(client)
    workspace = client.get("/api/workspaces/current", headers=auth(token)).json()
    courses = client.post("/api/courses/defaults", headers=auth(token)).json()
    first_detail = client.get(f"/api/courses/{courses[0]['id']}", headers=auth(token)).json()
    second_detail = client.get(f"/api/courses/{courses[1]['id']}", headers=auth(token)).json()
    chapter = first_detail["chapters"][0]

    missing_course = client.post(
        "/api/conversations",
        json={"chapter_id": chapter["id"]},
        headers=auth(token),
    )
    assert missing_course.status_code == 422
    assert missing_course.json()["error"]["code"] == "course_required_for_chapter"

    wrong_course = client.post(
        "/api/conversations",
        json={"course_id": courses[1]["id"], "chapter_id": chapter["id"]},
        headers=auth(token),
    )
    assert wrong_course.status_code == 404
    assert wrong_course.json()["error"]["code"] == "course_chapter_not_found"

    conversation = client.post(
        "/api/conversations",
        json={"course_id": courses[0]["id"], "chapter_id": chapter["id"]},
        headers=auth(token),
    )
    assert conversation.status_code == 201
    assert conversation.json()["chapter_id"] == chapter["id"]

    with client.app.state.session_factory() as session:
        session.add(
            Artifact(
                workspace_id=UUID(workspace["id"]),
                conversation_id=UUID(conversation.json()["id"]),
                type="personal_tutor",
                title="错题辅导",
                content="诊断与练习",
                data={
                    "diagnosis": "时态使用不稳定",
                    "explanation": "需要区分完成时与一般过去时。",
                    "mistakes": ["现在完成时与一般过去时混淆"],
                    "practice": ["完成 3 组时间线辨析练习"],
                    "follow_up_questions": [],
                },
                format="markdown",
            )
        )
        session.commit()

    completed = client.post(
        f"/api/courses/{courses[0]['id']}/chapters/{chapter['id']}/complete",
        headers=auth(token),
    )
    assert completed.status_code == 200
    assert completed.json()["weak_points"] == [
        {
            "id": completed.json()["weak_points"][0]["id"],
            "chapter_id": chapter["id"],
            "name": "现在完成时与一般过去时混淆",
            "recommendation": "完成 3 组时间线辨析练习",
        }
    ]

    untouched = client.get(f"/api/courses/{courses[1]['id']}", headers=auth(token))
    assert untouched.status_code == 200
    assert untouched.json()["weak_points"] == []
    assert second_detail["weak_points"] == []
