from pathlib import Path, PureWindowsPath
from uuid import uuid4

from app.core.errors import AppError


class LocalObjectStorage:
    """Filesystem-backed storage that confines every key beneath one root."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, content: bytes) -> None:
        target = self._resolve_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, key: str) -> bytes:
        target = self._resolve_key(key)
        if not target.is_file():
            raise AppError(
                code="storage_object_not_found",
                message="The requested storage object does not exist.",
                status_code=404,
            )
        return target.read_bytes()

    def delete(self, key: str) -> None:
        target = self._resolve_key(key)
        if target.exists():
            target.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve_key(key).is_file()

    def _resolve_key(self, key: str) -> Path:
        windows_path = PureWindowsPath(key)
        candidate = (self._root / Path(key)).resolve()
        if not key or windows_path.is_absolute() or windows_path.drive:
            raise self._invalid_key()
        try:
            candidate.relative_to(self._root)
        except ValueError as error:
            raise self._invalid_key() from error
        return candidate

    @staticmethod
    def _invalid_key() -> AppError:
        return AppError(
            code="invalid_storage_key",
            message="The storage key must stay within the configured storage root.",
            status_code=400,
        )
