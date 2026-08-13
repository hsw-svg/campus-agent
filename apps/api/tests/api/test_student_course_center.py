from uuid import UUID

from fastapi.testclient import TestClient

from app.artifacts.models import Artifact
from app.attachments.models import Attachment
from app.courses.models import Course, CourseChapter
from app.integrations.deeptutor.client import course_knowledge_base_name


class TextbookDeepTutor:
    def __init__(self, response: object | None = None) -> None:
        self.response = response or {
            "book": {"id": "bk_course_linear_algebra"},
            "spine": {
                "chapters": [
                    {
                        "id": "ch_overview",
                        "title": "本书导览",
                        "auto_overview": True,
                        "page_ids": ["pg_overview"],
                        "order": 0,
                    },
                    {
                        "id": "ch_vectors",
                        "title": "向量与线性组合",
                        "summary": "从几何与代数两个视角认识向量。",
                        "learning_objectives": ["向量", "线性组合"],
                        "page_ids": ["pg_vectors", "pg_vectors_practice"],
                        "order": 1,
                    },
                    {
                        "id": "ch_matrices",
                        "title": "矩阵与线性变换",
                        "summary": "理解矩阵表示的线性变换。",
                        "learning_objectives": ["矩阵", "线性变换"],
                        "page_ids": ["pg_matrices"],
                        "order": 2,
                    },
                ]
            },
        }
        self.payloads: list[dict] = []

    async def create_or_compile_book(self, payload: dict, *, compile_page: bool = False) -> object:
        assert compile_page is False
        self.payloads.append(payload)
        return self.response


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


def test_student_can_create_and_bind_topic_textbook_to_empty_course(client: TestClient) -> None:
    token = make_workspace(client)
    deep_tutor = TextbookDeepTutor()
    client.app.state.deeptutor_client = deep_tutor
    created = client.post(
        "/api/courses",
        json={"name": "线性代数自学", "description": "面向大一学生"},
        headers=auth(token),
    )
    course_id = created.json()["id"]

    response = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "向量、矩阵与线性变换", "use_course_materials": False},
        headers=auth(token),
    )

    assert response.status_code == 200
    detail = response.json()
    assert detail["deeptutor_book_id"] == "bk_course_linear_algebra"
    assert [chapter["title"] for chapter in detail["chapters"]] == [
        "向量与线性组合",
        "矩阵与线性变换",
    ]
    assert detail["chapters"][0]["knowledge_points"] == ["向量", "线性组合"]
    assert detail["chapters"][0]["deeptutor_chapter_id"] == "ch_vectors"
    assert detail["chapters"][0]["deeptutor_page_ids"] == ["pg_vectors", "pg_vectors_practice"]
    assert deep_tutor.payloads[0]["knowledge_bases"] == []
    assert "线性代数自学" in deep_tutor.payloads[0]["user_intent"]

    refreshed = client.get(f"/api/courses/{course_id}", headers=auth(token))
    assert refreshed.json()["deeptutor_book_id"] == "bk_course_linear_algebra"
    assert refreshed.json()["chapter_count"] == 2


def test_course_textbook_requires_ready_material_and_rejects_duplicate_binding(client: TestClient) -> None:
    token = make_workspace(client)
    client.app.state.deeptutor_client = TextbookDeepTutor()
    course_id = client.post(
        "/api/courses",
        json={"name": "材料驱动课程"},
        headers=auth(token),
    ).json()["id"]

    missing_material = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "基于教材生成", "use_course_materials": True},
        headers=auth(token),
    )
    assert missing_material.status_code == 409
    assert missing_material.json()["error"]["code"] == "course_materials_not_ready"

    first = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "按主题生成", "use_course_materials": False},
        headers=auth(token),
    )
    assert first.status_code == 200
    duplicate = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "重复生成", "use_course_materials": False},
        headers=auth(token),
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "course_textbook_exists"


def test_course_textbook_uses_owned_submitted_material_knowledge_base(client: TestClient) -> None:
    token = make_workspace(client)
    workspace_id = client.get("/api/workspaces/current", headers=auth(token)).json()["id"]
    deep_tutor = TextbookDeepTutor()
    client.app.state.deeptutor_client = deep_tutor
    course_id = client.post(
        "/api/courses",
        json={"name": "教材驱动课程"},
        headers=auth(token),
    ).json()["id"]
    knowledge_base_name = course_knowledge_base_name(course_id)
    with client.app.state.session_factory() as session:
        session.add(
            Attachment(
                workspace_id=UUID(workspace_id),
                course_id=UUID(course_id),
                conversation_id=None,
                filename="lesson.md",
                content_type="text/markdown",
                size_bytes=12,
                storage_key=f"test/{course_id}/lesson.md",
                scope="workspace",
                status="ready",
                knowledge_base_name=knowledge_base_name,
                knowledge_base_status="queued",
                knowledge_base_task_id="task-course-material",
            )
        )
        session.commit()

    response = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "根据上传教材生成", "use_course_materials": True},
        headers=auth(token),
    )

    assert response.status_code == 200
    assert deep_tutor.payloads[0]["knowledge_bases"] == [knowledge_base_name]


def test_textbook_binding_preserves_template_chapters_and_progress(client: TestClient) -> None:
    token = make_workspace(client)
    client.app.state.deeptutor_client = TextbookDeepTutor()
    course = client.post("/api/courses/defaults", headers=auth(token)).json()[0]
    before = client.get(f"/api/courses/{course['id']}", headers=auth(token)).json()
    started = client.post(f"/api/courses/{course['id']}/start", headers=auth(token)).json()
    first_chapter_id = started["chapters"][0]["id"]
    client.post(
        f"/api/courses/{course['id']}/chapters/{first_chapter_id}/complete",
        headers=auth(token),
    )

    response = client.post(
        f"/api/courses/{course['id']}/textbook",
        json={"topic": "配套交互教材", "use_course_materials": False},
        headers=auth(token),
    )

    assert response.status_code == 200
    detail = response.json()
    assert [chapter["id"] for chapter in detail["chapters"]] == [
        chapter["id"] for chapter in before["chapters"]
    ]
    assert [chapter["title"] for chapter in detail["chapters"]] == [
        chapter["title"] for chapter in before["chapters"]
    ]
    assert detail["completed_chapter_count"] == 1
    assert detail["chapters"][0]["deeptutor_page_ids"] == ["pg_vectors", "pg_vectors_practice"]
    assert detail["chapters"][2]["deeptutor_page_ids"] == []


def test_invalid_textbook_response_does_not_partially_bind_course(client: TestClient) -> None:
    token = make_workspace(client)
    client.app.state.deeptutor_client = TextbookDeepTutor({"book": {"id": "bk_invalid"}, "spine": {"chapters": []}})
    course_id = client.post(
        "/api/courses",
        json={"name": "响应校验课程"},
        headers=auth(token),
    ).json()["id"]

    response = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "无效结构", "use_course_materials": False},
        headers=auth(token),
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "deeptutor_invalid_response"
    with client.app.state.session_factory() as session:
        course = session.get(Course, UUID(course_id))
        assert course is not None
        assert course.deeptutor_book_id is None
        assert session.query(CourseChapter).filter_by(course_id=course.id).count() == 0


def test_textbook_without_page_mapping_does_not_bind_course(client: TestClient) -> None:
    token = make_workspace(client)
    client.app.state.deeptutor_client = TextbookDeepTutor(
        {
            "book": {"id": "bk_missing_pages"},
            "spine": {
                "chapters": [
                    {
                        "id": "ch_uncompiled",
                        "title": "尚未编译的章节",
                        "auto_overview": False,
                        "page_ids": [],
                    }
                ]
            },
        }
    )
    course_id = client.post(
        "/api/courses",
        json={"name": "页面映射校验课程"},
        headers=auth(token),
    ).json()["id"]

    response = client.post(
        f"/api/courses/{course_id}/textbook",
        json={"topic": "未编译教材", "use_course_materials": False},
        headers=auth(token),
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "deeptutor_invalid_response"
    with client.app.state.session_factory() as session:
        course = session.get(Course, UUID(course_id))
        assert course is not None
        assert course.deeptutor_book_id is None
        assert session.query(CourseChapter).filter_by(course_id=course.id).count() == 0


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
