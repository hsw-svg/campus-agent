import io
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Sequence

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.integrations.storage.local import LocalObjectStorage
from tests.api.conftest import make_workspace


def auth(token: str) -> dict[str, str]:
    return {"X-Workspace-Token": token}


class FakeChatProvider:
    is_configured = True

    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []

    async def stream_reply(self, messages: Sequence[dict[str, str]]) -> AsyncIterator[str]:
        self.calls.append(list(messages))
        yield "已根据资料回答"


class FakeEmbeddingProvider:
    is_configured = True

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def create_conversation(client: TestClient, token: str) -> dict:
    response = client.post("/api/conversations", json={}, headers=auth(token))
    assert response.status_code == 201
    return response.json()


def make_xlsx_attendance_book() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "出勤记录"
    sheet.append(["匿名编号", "第一次出勤", "第二次出勤"])
    sheet.append(["A01", "出勤", "缺勤"])
    content = io.BytesIO()
    workbook.save(content)
    return content.getvalue()


def test_upload_parses_real_xlsx_attendance_book(client: TestClient, tmp_path: Path) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")

    response = client.post(
        "/api/workspaces/current/attachments",
        files={
            "file": (
                "attendance.xlsx",
                make_xlsx_attendance_book(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=auth(token),
    )

    assert response.status_code == 201
    attachment = response.json()
    assert attachment["status"] == "degraded"
    assert attachment["extracted_chars"] > 0


def test_upload_parses_and_indexes_text_with_workspace_scope(client: TestClient, tmp_path: Path) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")
    conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("lesson.md", "线性代数的矩阵秩是本节重点。", "text/markdown")},
        data={"scope": "workspace"},
        headers=auth(token),
    )

    assert response.status_code == 201
    attachment = response.json()
    assert attachment["scope"] == "workspace"
    assert attachment["status"] == "degraded"
    assert attachment["extracted_chars"] > 0
    listed = client.get(
        f"/api/conversations/{conversation['id']}/attachments", headers=auth(token)
    )
    assert listed.json() == []


def test_workspace_attachments_do_not_appear_as_new_conversation_upload_status(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")
    first_conversation = create_conversation(client, token)
    next_conversation = create_conversation(client, token)

    response = client.post(
        f"/api/conversations/{first_conversation['id']}/attachments",
        files={"file": ("learning.xlsx", "匿名编号,作业1\nA01,90", "text/csv")},
        data={"scope": "workspace"},
        headers=auth(token),
    )
    assert response.status_code == 201

    listed = client.get(
        f"/api/conversations/{next_conversation['id']}/attachments", headers=auth(token)
    )

    assert listed.status_code == 200
    assert listed.json() == []


def test_workspace_attachment_can_be_uploaded_and_listed_without_conversation(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")

    response = client.post(
        "/api/workspaces/current/attachments",
        files={"file": ("learning.csv", "匿名编号,得分\nA01,90", "text/csv")},
        headers=auth(token),
    )

    assert response.status_code == 201
    attachment = response.json()
    assert attachment["scope"] == "workspace"
    assert attachment["conversation_id"] is None

    listed = client.get("/api/workspaces/current/attachments", headers=auth(token))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [attachment["id"]]
    assert client.get("/api/conversations", headers=auth(token)).json() == []


def test_course_library_upload_rejects_unsupported_file_type(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")
    course = client.post("/api/courses", json={"name": "程序设计"}, headers=auth(token)).json()

    response = client.post(
        "/api/workspaces/current/attachments",
        params={"course_id": course["id"]},
        files={"file": ("legacy.xls", b"not-an-xls", "application/vnd.ms-excel")},
        headers=auth(token),
    )

    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "unsupported_attachment_type",
        "message": "Only txt, md, docx, pdf, xlsx and csv files are supported.",
        "details": {"supported_extensions": [".csv", ".docx", ".md", ".pdf", ".txt", ".xlsx"]},
    }
    assert client.get(
        "/api/workspaces/current/attachments",
        params={"course_id": course["id"]},
        headers=auth(token),
    ).json() == []


def test_course_library_upload_rejects_oversized_file_without_creating_attachment(
    client: TestClient, tmp_path: Path, monkeypatch
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")
    course = client.post("/api/courses", json={"name": "程序设计"}, headers=auth(token)).json()
    monkeypatch.setattr("app.api.attachments.MAX_ATTACHMENT_BYTES", 8)

    response = client.post(
        "/api/workspaces/current/attachments",
        params={"course_id": course["id"]},
        files={"file": ("large.txt", b"123456789", "text/plain")},
        headers=auth(token),
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "attachment_too_large"
    assert client.get(
        "/api/workspaces/current/attachments",
        params={"course_id": course["id"]},
        headers=auth(token),
    ).json() == []


def test_workspace_attachment_listing_is_isolated_by_course(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    token = make_workspace(client, "teacher")
    calculus = client.post("/api/courses", json={"name": "高等数学"}, headers=auth(token)).json()
    programming = client.post("/api/courses", json={"name": "程序设计"}, headers=auth(token)).json()

    calculus_file = client.post(
        f"/api/workspaces/current/attachments?course_id={calculus['id']}",
        files={"file": ("calculus-learning.csv", "学号,极限,A01,90", "text/csv")},
        headers=auth(token),
    ).json()
    programming_file = client.post(
        f"/api/workspaces/current/attachments?course_id={programming['id']}",
        files={"file": ("programming-learning.csv", "学号,函数,A01,90", "text/csv")},
        headers=auth(token),
    ).json()

    listed = client.get(
        f"/api/workspaces/current/attachments?course_id={calculus['id']}",
        headers=auth(token),
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [calculus_file["id"]]
    assert programming_file["id"] not in {item["id"] for item in listed.json()}


def test_workspace_attachment_course_scope_must_belong_to_workspace(
    client: TestClient, tmp_path: Path
) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    owner = make_workspace(client, "teacher")
    other_teacher = make_workspace(client, "teacher")
    other_course = client.post(
        "/api/courses", json={"name": "其他教师课程"}, headers=auth(other_teacher)
    ).json()

    listed = client.get(
        "/api/workspaces/current/attachments",
        params={"course_id": other_course["id"]},
        headers=auth(owner),
    )
    uploaded = client.post(
        "/api/workspaces/current/attachments",
        params={"course_id": other_course["id"]},
        files={"file": ("learning.csv", "匿名编号,得分\nA01,90", "text/csv")},
        headers=auth(owner),
    )

    assert listed.status_code == 404
    assert listed.json()["error"]["code"] == "course_not_found"
    assert uploaded.status_code == 404
    assert uploaded.json()["error"]["code"] == "course_not_found"


def test_attachment_and_retrieval_are_isolated_by_workspace(client: TestClient, tmp_path: Path) -> None:
    client.app.state.object_storage = LocalObjectStorage(tmp_path)
    student = make_workspace(client, "student")
    teacher = make_workspace(client, "teacher")
    student_conversation = create_conversation(client, student)
    teacher_conversation = create_conversation(client, teacher)

    for token, conversation, text in (
        (student, student_conversation, "学生私有资料：量子力学"),
        (teacher, teacher_conversation, "教师私有资料：课堂评价"),
    ):
        response = client.post(
            f"/api/conversations/{conversation['id']}/attachments",
            files={"file": ("material.txt", text, "text/plain")},
            headers=auth(token),
        )
        assert response.status_code == 201

    fake_chat = FakeChatProvider()
    client.app.state.chat_provider = fake_chat
    client.app.state.embedding_provider = FakeEmbeddingProvider()
    response = client.post(
        f"/api/conversations/{teacher_conversation['id']}/messages/stream",
        json={"content": "课堂评价"},
        headers=auth(teacher),
    )
    assert response.status_code == 200
    assert "教师私有资料" in response.text
    assert "学生私有资料" not in response.text
    assert "教师私有资料" in fake_chat.calls[0][0]["content"]
    assert "学生私有资料" not in fake_chat.calls[0][0]["content"]

    forged = client.get(
        f"/api/conversations/{student_conversation['id']}/attachments", headers=auth(teacher)
    )
    assert forged.status_code == 404
