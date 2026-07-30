import pytest

from app.core.errors import AppError
from app.integrations.storage.local import LocalObjectStorage


def test_local_storage_round_trips_data(tmp_path) -> None:
    storage = LocalObjectStorage(tmp_path)

    storage.put("workspace/a.txt", b"x")
    storage.put("workspace/a.txt", b"replacement")

    assert storage.get("workspace/a.txt") == b"replacement"
    assert storage.exists("workspace/a.txt") is True
    assert list((tmp_path / "workspace").iterdir()) == [tmp_path / "workspace" / "a.txt"]


@pytest.mark.parametrize("key", ["../secret", "C:/outside.txt", "/outside.txt"])
def test_local_storage_rejects_paths_outside_the_root(tmp_path, key: str) -> None:
    storage = LocalObjectStorage(tmp_path)

    with pytest.raises(AppError, match="invalid_storage_key"):
        storage.put(key, b"x")
