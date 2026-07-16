import json

from fastapi.testclient import TestClient

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


def test_learning_analysis_creates_class_artifact_without_chat_credentials(client: TestClient) -> None:
    teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    csv_text = (
        "匿名编号,课程,2026-07-01签到,2026-07-03签到,课堂积极性评分,"
        "作业1_Python基础,作业2_条件与循环,作业3_函数与模块,满分\n"
        "A01,Python程序设计,签到,签到,5,90,80,70,100\n"
        "A02,Python程序设计,迟到,缺勤,3,70,60,50,100\n"
    )
    upload = client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("python_scores.csv", csv_text, "text/csv")},
        headers=auth(teacher),
    )
    assert upload.status_code == 201

    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "分析这份 Python 班级成绩和签到表"},
        headers=auth(teacher),
    )

    assert response.status_code == 200
    events = events_from_stream(response.text)
    start = next(data for name, data in events if name == "message_start")
    artifact = next(data for name, data in events if name == "artifact" and data.get("type") == "learning_analysis")
    done = next(data for name, data in events if name == "done")
    assert start["agent_id"] == "learning_analysis"
    assert artifact["artifact_id"]
    assert done["run_id"] == start["run_id"]
    assert "班级整体学情分析" in response.text
    assert "A01" not in response.text

    fetched = client.get(f"/api/artifacts/{artifact['artifact_id']}", headers=auth(teacher))
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["type"] == "learning_analysis"
    assert body["data"]["scope"] == "class"
    assert body["data"]["student_count"] == 2
    assert "A01" not in body["content"]

    exported = client.get(
        f"/api/artifacts/{artifact['artifact_id']}/export",
        headers=auth(teacher),
    )
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/markdown")
    assert "班级整体学情分析" in exported.text


def test_learning_artifact_is_isolated_by_workspace(client: TestClient) -> None:
    teacher = make_workspace(client, "teacher")
    other_teacher = make_workspace(client, "teacher")
    conversation = client.post("/api/conversations", json={}, headers=auth(teacher)).json()
    csv_text = "匿名编号,作业1,课堂积极性评分\nA01,80,4\n"
    client.post(
        f"/api/conversations/{conversation['id']}/attachments",
        files={"file": ("scores.csv", csv_text, "text/csv")},
        headers=auth(teacher),
    )
    response = client.post(
        f"/api/conversations/{conversation['id']}/messages/stream",
        json={"content": "分析成绩表"},
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
