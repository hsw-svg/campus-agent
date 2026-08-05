import json
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


TABLE = """匿名编号 | 课程 | 课程章节范围 | 2026-07-01签到 | 2026-07-03签到 | 课堂积极性 | 作业1_Python基础 | 作业2_条件与循环 | 作业3_函数与模块 | 满分
A01 | Python程序设计 | 基础、条件、函数 | 签到 | 签到 | 5 | 90 | 80 | 70 | 100
A02 | Python程序设计 | 基础、条件、函数 | 迟到 | 缺勤 | 3 | 70 | 60 | 50 | 100
A03 | Python程序设计 | 基础、条件、函数 | 签到 | 签到 | 4 | 80 | 70 | 60 | 100
"""

OTHER_TABLE = """匿名编号 | 课程 | 课程章节范围 | 2026-07-01签到 | 课堂积极性 | 作业1_Python基础 | 满分
A04 | Python程序设计 | 基础 | 签到 | 2 | 40 | 100
"""


def test_learning_analysis_creates_class_artifact_without_chat_credentials(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("python_scores.csv", TABLE, "text/csv")},
        headers=auth(teacher),
    )
    assert upload.status_code == 201
    selected_attachment_id = upload.json()["id"]

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={
            "content": "分析学情",
            "agent_id": "learning_analysis",
            "selected_attachment_ids": [selected_attachment_id],
        },
        headers=auth(teacher),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    start = next(data for name, data in events if name == "message_start")
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "learning_analysis")
    done = next(data for name, data in events if name == "done")
    progress = [data for name, data in events if name == "tool_status"]
    assert start["agent_id"] == "learning_analysis"
    assert artifact["artifact_id"]
    assert done["run_id"] == start["run_id"]
    assert {item["phase"] for item in progress} >= {"context", "model", "validation", "artifact"}
    assert all("A01" not in json.dumps(item, ensure_ascii=False) for item in progress)
    assert "班级整体学情分析" in response.text
    assert "A01" not in response.text

    fetched = client.get(f"/api/artifacts/{artifact['artifact_id']}", headers=auth(teacher))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["type"] == "learning_analysis"
    assert body["data"]["scope"] == "class"
    assert body["data"]["student_count"] == 3
    assert "A01" not in body["content"]

    exported = client.get(
        f"/api/artifacts/{artifact['artifact_id']}/export",
        headers=auth(teacher),
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "班级整体学情分析" in exported.text


def test_learning_analysis_requires_explicit_attachment_selection(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("python_scores.csv", TABLE, "text/csv")},
        headers=auth(teacher),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "分析学情", "agent_id": "learning_analysis"},
        headers=auth(teacher),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    error = next(data for name, data in events if name == "error")
    assert error["code"] == "agent_input_incomplete"
    assert error["missing_inputs"]


def test_learning_analysis_accepts_workspace_scope_upload(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("python_scores.csv", TABLE, "text/csv")},
        data={"scope": "workspace"},
        headers=auth(teacher),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={
            "content": "分析学情",
            "agent_id": "learning_analysis",
            "selected_attachment_ids": [upload.json()["id"]],
        },
        headers=auth(teacher),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    assert not any(
        name == "error" and data.get("code") == "agent_input_incomplete"
        for name, data in events
    )
    start = next(data for name, data in events if name == "message_start")
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "learning_analysis")
    assert start["agent_id"] == "learning_analysis"
    assert artifact["artifact_id"]


def test_course_learning_analysis_uses_all_course_materials_by_default(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    teacher = make_workspace(client, "teacher")
    course = client.post("/api/courses", json={"name": "Python 课程"}, headers=auth(teacher)).json()
    other_course = client.post("/api/courses", json={"name": "其他课程"}, headers=auth(teacher)).json()
    conversation = client.post(
        "/api/conversations",
        json={"course_id": course["id"]},
        headers=auth(teacher),
    ).json()
    other_conversation = client.post(
        "/api/conversations",
        json={"course_id": other_course["id"]},
        headers=auth(teacher),
    ).json()

    course_table = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("python_scores.csv", TABLE, "text/csv")},
        data={"scope": "workspace"},
        headers=auth(teacher),
    )
    course_notes = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("course-notes.txt", "本课程资料：列表、切片与函数。", "text/plain")},
        data={"scope": "workspace"},
        headers=auth(teacher),
    )
    other_table = client.post(
        f"/api/conversations/{other_conversation['id']}/attachments",
        files={"file": ("other-course.csv", OTHER_TABLE, "text/csv")},
        data={"scope": "workspace"},
        headers=auth(teacher),
    )
    assert course_table.status_code == course_notes.status_code == other_table.status_code == 201
    visible_course_materials = client.get(
        "/api/workspaces/current/attachments",
        params={"course_id": course["id"]},
        headers=auth(teacher),
    )
    assert {item["filename"] for item in visible_course_materials.json()} == {"python_scores.csv", "course-notes.txt"}

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "分析学情", "agent_id": "learning_analysis"},
        headers=auth(teacher),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "learning_analysis")
    assert artifact["data"]["student_count"] == 3


def test_learning_analysis_uses_only_selected_workspace_attachments(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    selected = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("selected.csv", TABLE, "text/csv")},
        data={"scope": "workspace"},
        headers=auth(teacher),
    ).json()
    client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("not-selected.csv", OTHER_TABLE, "text/csv")},
        data={"scope": "workspace"},
        headers=auth(teacher),
    )

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={
            "content": "分析学情",
            "agent_id": "learning_analysis",
            "selected_attachment_ids": [selected["id"]],
        },
        headers=auth(teacher),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "learning_analysis")
    assert artifact["data"]["student_count"] == 3


def test_learning_artifact_is_isolated_by_workspace(client: TestClient) -> None:
    client.app.state.object_storage = LocalObjectStorage(Path(".tmp-storage"))
    teacher = make_workspace(client, "teacher")
    other_teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("scores.csv", TABLE, "text/csv")},
        headers=auth(teacher),
    )
    assert upload.status_code == 201
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={
            "content": "分析学情",
            "agent_id": "learning_analysis",
            "selected_attachment_ids": [upload.json()["id"]],
        },
        headers=auth(teacher),
    )
    artifact_event = next(
        data for name, data in events_from_stream(response.text) if name == "artifact" and data.get("type") == "learning_analysis"
    )

    forbidden = client.get(
        f"/api/artifacts/{artifact_event['artifact_id']}",
        headers=auth(other_teacher),
    )
    assert forbidden.status_code == 404
