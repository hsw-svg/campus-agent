import json

import httpx
import pytest

from app.integrations.deeptutor.client import DeepTutorClient, DeepTutorError


@pytest.mark.asyncio
async def test_deeptutor_client_uses_book_and_knowledge_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/health"):
            return httpx.Response(200, json={"status": "healthy"})
        if request.url.path.endswith("/knowledge/list"):
            return httpx.Response(200, json={"items": [{"name": "course-kb"}]})
        return httpx.Response(200, json={"books": [{"id": "book-1"}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    client = DeepTutorClient("http://127.0.0.1:8001", enabled=True)

    assert client.chat_path == "/api/v1/ws"
    assert (await client.health_check()) == {"status": "healthy"}
    assert (await client.list_books()) == {"books": [{"id": "book-1"}]}
    assert (await client.list_knowledge_bases()) == {"items": [{"name": "course-kb"}]}
    assert [request.url.path for request in requests] == [
        "/api/v1/book/health",
        "/api/v1/book/books",
        "/api/v1/knowledge/list",
    ]


@pytest.mark.asyncio
async def test_create_book_completes_the_three_stage_deeptutor_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/confirm-proposal"):
            return httpx.Response(
                200,
                json={"book": {"id": "book-1", "status": "spine_ready"}, "spine": {"chapters": []}},
            )
        if request.url.path.endswith("/confirm-spine"):
            return httpx.Response(200, json={"pages": [{"id": "page-1"}]})
        if request.url.path.endswith("/spine"):
            return httpx.Response(
                200,
                json={"spine": {"chapters": [{"id": "chapter-1", "page_ids": ["page-1"]}]}},
            )
        return httpx.Response(
            200,
            json={"book": {"id": "book-1", "status": "draft"}, "proposal": {"title": "Python"}},
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    client = DeepTutorClient("http://127.0.0.1:8001", enabled=True)

    result = await client.create_or_compile_book({"user_intent": "Python"})

    assert result["book"]["status"] == "spine_ready"
    assert result["pages"] == [{"id": "page-1"}]
    assert result["spine"]["chapters"][0]["page_ids"] == ["page-1"]
    assert [request.url.path for request in requests] == [
        "/api/v1/book/books",
        "/api/v1/book/books/confirm-proposal",
        "/api/v1/book/books/confirm-spine",
        "/api/v1/book/books/book-1/spine",
    ]
    assert json.loads(requests[-2].content) == {"book_id": "book-1", "auto_compile": True}


@pytest.mark.asyncio
async def test_deeptutor_client_reports_disabled_integration() -> None:
    client = DeepTutorClient("http://127.0.0.1:8001")

    assert await client.health_check() is None
    with pytest.raises(DeepTutorError) as error:
        await client.list_books()

    assert error.value.code == "deeptutor_unavailable"
    assert error.value.status_code == 503


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("listed", "expected_path", "expected_operation"),
    [
        ([], "/api/v1/knowledge/create", "create"),
        (
            [{"name": "campus-course-12345678123456781234567812345678"}],
            "/api/v1/knowledge/campus-course-12345678123456781234567812345678/upload",
            "upload",
        ),
    ],
)
async def test_sync_course_material_creates_or_appends_stable_knowledge_base(
    monkeypatch: pytest.MonkeyPatch,
    listed: list[dict[str, str]],
    expected_path: str,
    expected_operation: str,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/knowledge/list"):
            return httpx.Response(200, json=listed)
        return httpx.Response(200, json={"task_id": "kb-task-1"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    client = DeepTutorClient("http://127.0.0.1:8001", enabled=True)

    result = await client.sync_course_material(
        course_id="12345678-1234-5678-1234-567812345678",
        filename="calculus.pdf",
        content=b"textbook",
        content_type="application/pdf",
    )

    assert result == {
        "knowledge_base_name": "campus-course-12345678123456781234567812345678",
        "task_id": "kb-task-1",
        "operation": expected_operation,
    }
    assert requests[-1].url.path == expected_path
    assert "multipart/form-data" in requests[-1].headers["content-type"]
    assert b'filename="calculus.pdf"' in requests[-1].content
    if expected_operation == "create":
        assert b'name="name"' in requests[-1].content
        assert b"campus-course-12345678123456781234567812345678" in requests[-1].content
