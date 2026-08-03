import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import APIRouter, Body, Query, Request, WebSocket, WebSocketDisconnect

from app.core.errors import AppError
from app.integrations.deeptutor.client import DeepTutorClient, DeepTutorError


router = APIRouter(prefix="/api/deeptutor", tags=["deeptutor"])
ResultT = TypeVar("ResultT")


def _client(request: Request) -> DeepTutorClient:
    return request.app.state.deeptutor_client


async def _call(operation: Callable[[], Awaitable[ResultT]]) -> ResultT:
    try:
        return await operation()
    except DeepTutorError as error:
        raise AppError(
            code=error.code,
            message=error.message,
            status_code=error.status_code,
            details=error.details,
        ) from error


@router.get("/health")
async def get_deeptutor_health(request: Request) -> dict[str, Any]:
    client = _client(request)
    result = await client.health_check()
    if result is None:
        return {"status": "unavailable", "service": "deeptutor"}
    return {"status": "healthy", "service": "deeptutor", "details": result}


@router.get("/books")
async def list_books(request: Request) -> Any:
    return await _call(_client(request).list_books)


@router.get("/books/{book_id}")
async def get_book(book_id: str, request: Request) -> Any:
    return await _call(lambda: _client(request).get_book(book_id))


@router.get("/books/{book_id}/spine")
async def get_spine(book_id: str, request: Request) -> Any:
    return await _call(lambda: _client(request).get_spine(book_id))


@router.get("/books/{book_id}/pages/{page_id}")
async def get_page(book_id: str, page_id: str, request: Request) -> Any:
    return await _call(lambda: _client(request).get_page(book_id, page_id))


@router.post("/books")
async def create_book(
    request: Request,
    payload: dict[str, Any] = Body(...),
    compile_page: bool = Query(False),
) -> Any:
    return await _call(
        lambda: _client(request).create_or_compile_book(
            payload,
            compile_page=compile_page,
        )
    )


@router.get("/knowledge-bases")
async def list_knowledge_bases(request: Request) -> Any:
    return await _call(_client(request).list_knowledge_bases)


@router.websocket("/chat")
async def proxy_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    client: DeepTutorClient = websocket.app.state.deeptutor_client

    try:
        async with client.chat_socket() as upstream:
            async def browser_to_upstream() -> None:
                while True:
                    message = await websocket.receive()
                    if message["type"] == "websocket.disconnect":
                        return
                    if message.get("text") is not None:
                        await upstream.send(message["text"])
                    elif message.get("bytes") is not None:
                        await upstream.send(message["bytes"])

            async def upstream_to_browser() -> None:
                async for message in upstream:
                    if isinstance(message, bytes):
                        await websocket.send_bytes(message)
                    else:
                        await websocket.send_text(message)

            tasks = {
                asyncio.create_task(browser_to_upstream()),
                asyncio.create_task(upstream_to_browser()),
            }
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            await asyncio.gather(*done, return_exceptions=True)
    except WebSocketDisconnect:
        return
    except DeepTutorError as error:
        try:
            await websocket.close(code=1011, reason=error.message[:123])
        except Exception:
            return
    except Exception:
        try:
            await websocket.close(code=1011, reason="DeepTutor chat proxy failed")
        except Exception:
            return
