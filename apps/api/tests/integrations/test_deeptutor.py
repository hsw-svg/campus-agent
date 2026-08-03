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
    assert [request.url.path for request in requests] == [
        "/api/v1/book/books",
        "/api/v1/book/books/confirm-proposal",
        "/api/v1/book/books/confirm-spine",
    ]
    assert json.loads(requests[-1].content) == {"book_id": "book-1", "auto_compile": True}


@pytest.mark.asyncio
async def test_deeptutor_client_reports_disabled_integration() -> None:
    client = DeepTutorClient("http://127.0.0.1:8001")

    assert await client.health_check() is None
    with pytest.raises(DeepTutorError) as error:
        await client.list_books()

    assert error.value.code == "deeptutor_unavailable"
    assert error.value.status_code == 503
