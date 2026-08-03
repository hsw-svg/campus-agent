from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from typing import Any

import httpx


class DeepTutorError(RuntimeError):
    """A downstream DeepTutor failure that can be mapped to AppError."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 502,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class DeepTutorClient:
    """HTTP/WebSocket boundary for the pinned DeepTutor server."""

    book_prefix = "/api/v1/book"
    knowledge_prefix = "/api/v1/knowledge"
    chat_path = "/api/v1/ws"

    def __init__(
        self,
        base_url: str,
        *,
        enabled: bool = False,
        timeout_seconds: float = 20.0,
        health_timeout_seconds: float = 2.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled
        self.timeout_seconds = max(0.5, timeout_seconds)
        self.health_timeout_seconds = max(0.5, health_timeout_seconds)

    @property
    def is_configured(self) -> bool:
        return self.enabled and bool(self.base_url)

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _websocket_url(self, path: str) -> str:
        if self.base_url.startswith("https://"):
            return f"wss://{self.base_url.removeprefix('https://')}{path}"
        return f"ws://{self.base_url.removeprefix('http://')}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: Mapping[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> Any:
        if not self.is_configured:
            raise DeepTutorError(
                "deeptutor_unavailable",
                "DeepTutor integration is not enabled.",
                status_code=503,
            )

        try:
            timeout = timeout_seconds or self.timeout_seconds
            async with httpx.AsyncClient(timeout=timeout) as http_client:
                response = await http_client.request(
                    method,
                    self._url(path),
                    json=dict(payload) if payload is not None else None,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            raise DeepTutorError(
                "deeptutor_upstream_error",
                "DeepTutor rejected the request.",
                status_code=502,
                details={"upstream_status": status, "path": path},
            ) from error
        except (httpx.HTTPError, OSError) as error:
            raise DeepTutorError(
                "deeptutor_unavailable",
                "DeepTutor is unavailable.",
                status_code=503,
                details={"path": path},
            ) from error

        try:
            return response.json()
        except ValueError as error:
            raise DeepTutorError(
                "deeptutor_invalid_response",
                "DeepTutor returned an invalid JSON response.",
                details={"path": path},
            ) from error

    async def health_check(self) -> dict[str, Any] | None:
        if not self.is_configured:
            return None
        try:
            result = await self._request(
                "GET",
                f"{self.book_prefix}/health",
                timeout_seconds=self.health_timeout_seconds,
            )
        except DeepTutorError:
            return None
        return result if isinstance(result, dict) else {"data": result}

    async def list_books(self) -> Any:
        return await self._request("GET", f"{self.book_prefix}/books")

    async def get_book(self, book_id: str) -> Any:
        return await self._request("GET", f"{self.book_prefix}/books/{book_id}")

    async def get_spine(self, book_id: str) -> Any:
        return await self._request("GET", f"{self.book_prefix}/books/{book_id}/spine")

    async def get_page(self, book_id: str, page_id: str) -> Any:
        return await self._request(
            "GET",
            f"{self.book_prefix}/books/{book_id}/pages/{page_id}",
        )

    async def create_or_compile_book(
        self,
        payload: Mapping[str, Any],
        *,
        compile_page: bool = False,
    ) -> Any:
        if compile_page:
            return await self._request(
                "POST",
                f"{self.book_prefix}/compile-page",
                payload=payload,
            )

        created = await self._request(
            "POST",
            f"{self.book_prefix}/books",
            payload=payload,
        )
        book = created.get("book") if isinstance(created, Mapping) else None
        book_id = book.get("id") if isinstance(book, Mapping) else None
        if not isinstance(book_id, str) or not book_id:
            raise DeepTutorError(
                "deeptutor_invalid_response",
                "DeepTutor did not return a book identifier.",
                details={"path": f"{self.book_prefix}/books"},
            )

        proposal_result = await self._request(
            "POST",
            f"{self.book_prefix}/books/confirm-proposal",
            payload={"book_id": book_id},
        )
        spine = proposal_result.get("spine") if isinstance(proposal_result, Mapping) else None
        if not isinstance(spine, Mapping):
            raise DeepTutorError(
                "deeptutor_invalid_response",
                "DeepTutor did not return a book spine.",
                details={"path": f"{self.book_prefix}/books/confirm-proposal"},
            )

        pages_result = await self._request(
            "POST",
            f"{self.book_prefix}/books/confirm-spine",
            payload={"book_id": book_id, "auto_compile": True},
        )
        return {
            "book": proposal_result.get("book", book),
            "proposal": created.get("proposal"),
            "spine": spine,
            "pages": pages_result.get("pages", [])
            if isinstance(pages_result, Mapping)
            else [],
        }

    async def list_knowledge_bases(self) -> Any:
        return await self._request("GET", f"{self.knowledge_prefix}/list")

    @asynccontextmanager
    async def chat_socket(self) -> AsyncIterator[Any]:
        if not self.is_configured:
            raise DeepTutorError(
                "deeptutor_unavailable",
                "DeepTutor integration is not enabled.",
                status_code=503,
            )
        try:
            from websockets.asyncio.client import connect

            async with connect(
                self._websocket_url(self.chat_path),
                open_timeout=self.timeout_seconds,
                close_timeout=5,
                max_size=8 * 1024 * 1024,
            ) as websocket:
                yield websocket
        except DeepTutorError:
            raise
        except Exception as error:
            raise DeepTutorError(
                "deeptutor_unavailable",
                "DeepTutor chat is unavailable.",
                status_code=503,
            ) from error
