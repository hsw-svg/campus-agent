from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.services.artifact_presentations import ArtifactPresentationService


@dataclass
class Export:
    content: bytes = b"original-pptx"
    media_type: str = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class MutatingStorage:
    def __init__(self, fail_on_put: int | None = None) -> None:
        self.objects: dict[str, bytes] = {}
        self.put_count = 0
        self.fail_on_put = fail_on_put
        self.deleted: list[str] = []

    def put(self, key: str, content: bytes) -> None:
        self.put_count += 1
        if self.put_count == self.fail_on_put:
            raise RuntimeError("storage failed")
        self.objects[key] = b"stored-pptx" if key.endswith(".pptx") else content

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def exists(self, key: str) -> bool:
        return key in self.objects


class Skill:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, _deck):
        self.calls += 1
        return Export()


def _deck() -> dict:
    return {"slides": [{"id": "slide-001"}, {"id": "slide-002"}]}


def test_presentation_generates_stores_pptx_and_returns_metadata() -> None:
    storage = MutatingStorage()
    skill = Skill()
    service = ArtifactPresentationService(storage, pptx_skill=skill)

    result = service.prepare(
        _deck(), workspace_id=uuid4(), conversation_id=uuid4(), scope_id=uuid4()
    )

    assert skill.calls == 1
    assert result.size_bytes == len(b"stored-pptx")
    assert result.page_count == 2
    assert result.mime_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert len(result.sha256) == 64
    assert result.object_key.endswith("presentation.pptx")
    # No preview manifest or PNG objects
    assert result.object_keys() == (result.object_key,)
    values = result.artifact_values()
    assert values["preview_status"] is None
    assert values["preview_manifest"] is None


def test_presentation_cleans_written_pptx_on_storage_failure() -> None:
    storage = MutatingStorage(fail_on_put=1)
    service = ArtifactPresentationService(storage, pptx_skill=Skill())

    with pytest.raises(RuntimeError):
        service.prepare(_deck(), workspace_id=uuid4(), conversation_id=uuid4(), scope_id=uuid4())

    assert storage.objects == {}
    assert any(key.endswith("presentation.pptx") for key in storage.deleted)


def test_presentation_rejects_deck_without_slides() -> None:
    service = ArtifactPresentationService(MutatingStorage(), pptx_skill=Skill())
    with pytest.raises(Exception, match="at least one"):
        service.prepare({}, workspace_id=uuid4(), conversation_id=uuid4(), scope_id=uuid4())


def test_presentation_rejects_duplicate_slide_ids() -> None:
    service = ArtifactPresentationService(MutatingStorage(), pptx_skill=Skill())
    deck = {"slides": [{"id": "a"}, {"id": "a"}]}
    with pytest.raises(Exception, match="unique"):
        service.prepare(deck, workspace_id=uuid4(), conversation_id=uuid4(), scope_id=uuid4())
