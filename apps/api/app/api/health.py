from fastapi import APIRouter, Request

from app.services.health import build_health_report


router = APIRouter()


@router.get("/api/health")
def get_health(request: Request) -> dict:
    return build_health_report(
        database_probe=request.app.state.database_probe,
        chat_provider=request.app.state.chat_provider,
        embedding_provider=request.app.state.embedding_provider,
    )
