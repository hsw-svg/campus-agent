from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MANAGED_PROFILE_ID = "campus-agent-shared-profile"
MANAGED_MODEL_ID = "campus-agent-shared-model"


class CatalogSyncError(RuntimeError):
    """Raised when DeepTutor's runtime model catalog cannot be synchronized."""


@dataclass(frozen=True, slots=True)
class SharedModelConfig:
    binding: str
    model: str
    api_key: str
    base_url: str
    api_version: str = ""
    dimension: int | None = None


def _upsert_service(
    catalog: dict[str, Any],
    service_name: str,
    config: SharedModelConfig,
) -> None:
    services = catalog.setdefault("services", {})
    service = services.setdefault(
        service_name,
        {"active_profile_id": None, "active_model_id": None, "profiles": []},
    )
    model: dict[str, Any] = {
        "id": MANAGED_MODEL_ID,
        "name": config.model,
        "model": config.model,
    }
    if service_name == "embedding":
        model["dimension"] = config.dimension or ""
        model["supported_dimensions"] = ""

    profile = {
        "id": MANAGED_PROFILE_ID,
        "name": "Campus Agent shared model",
        "binding": config.binding,
        "api_key": config.api_key,
        "base_url": config.base_url,
        "api_version": config.api_version,
        "extra_headers": {},
        "models": [model],
    }
    profiles = service.setdefault("profiles", [])
    service["profiles"] = [
        existing
        for existing in profiles
        if existing.get("id") != MANAGED_PROFILE_ID
    ] + [profile]
    service["active_profile_id"] = MANAGED_PROFILE_ID
    service["active_model_id"] = MANAGED_MODEL_ID


def build_synced_catalog(
    catalog: dict[str, Any],
    llm: SharedModelConfig,
    embedding: SharedModelConfig | None = None,
) -> dict[str, Any]:
    """Return a catalog with Campus Agent-managed profiles selected."""
    synced = deepcopy(catalog)
    _upsert_service(synced, "llm", llm)
    if embedding is not None:
        _upsert_service(synced, "embedding", embedding)
    return synced


def _request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310 - fixed local URL
            return json.load(response)
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise CatalogSyncError(
            f"DeepTutor catalog request failed ({error.code}): {body[:500]}"
        ) from error
    except (URLError, OSError, ValueError) as error:
        raise CatalogSyncError(f"DeepTutor catalog request failed: {error}") from error


def sync_catalog(base_url: str, llm: SharedModelConfig, embedding: SharedModelConfig | None) -> None:
    endpoint = base_url.rstrip("/") + "/api/v1/settings"
    current = _request_json("GET", f"{endpoint}/catalog")
    if not isinstance(current, dict) or not isinstance(current.get("catalog"), dict):
        raise CatalogSyncError("DeepTutor returned an invalid model catalog.")
    catalog = build_synced_catalog(current["catalog"], llm, embedding)
    _request_json("PUT", f"{endpoint}/catalog", {"catalog": catalog})
    _request_json("POST", f"{endpoint}/apply")


def _required_environment(prefix: str) -> SharedModelConfig | None:
    values = {
        "binding": os.getenv(f"{prefix}_BINDING", "").strip(),
        "model": os.getenv(f"{prefix}_MODEL", "").strip(),
        "api_key": os.getenv(f"{prefix}_API_KEY", "").strip(),
        "base_url": os.getenv(f"{prefix}_HOST", "").strip(),
    }
    if not all(values.values()):
        return None
    dimension: int | None = None
    if prefix == "EMBEDDING":
        raw_dimension = os.getenv("EMBEDDING_DIMENSION", "").strip()
        if raw_dimension:
            try:
                dimension = int(raw_dimension)
            except ValueError as error:
                raise CatalogSyncError("EMBEDDING_DIMENSION must be an integer.") from error
    return SharedModelConfig(
        **values,
        api_version=os.getenv(f"{prefix}_API_VERSION", "").strip(),
        dimension=dimension,
    )


def main() -> int:
    llm = _required_environment("LLM")
    if llm is None:
        print(
            "[entrypoint] DeepTutor catalog sync skipped: "
            "LLM_BINDING, LLM_MODEL, LLM_API_KEY and LLM_HOST are required",
            file=sys.stderr,
        )
        return 0

    embedding = _required_environment("EMBEDDING")
    sync_catalog(os.getenv("DEEPTUTOR_BASE_URL", "http://127.0.0.1:8001"), llm, embedding)
    embedding_label = embedding.model if embedding else "not configured"
    print(
        "[entrypoint] DeepTutor model catalog synchronized "
        f"(llm={llm.model}, embedding={embedding_label})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
