from fastapi import APIRouter, Request

from app.services.health import build_health_report


router = APIRouter()


@router.get("/api/health")
async def get_health(request: Request) -> dict:
    report = build_health_report(
        database_probe=request.app.state.database_probe,
        chat_provider=request.app.state.chat_provider,
        embedding_provider=request.app.state.embedding_provider,
    )
    settings = request.app.state.settings
    if settings.deeptutor_enabled:
        deep_tutor_health = await request.app.state.deeptutor_client.health_check()
        report["components"]["deep_tutor"] = {
            "status": "healthy" if deep_tutor_health is not None else "unavailable"
        }
        if deep_tutor_health is None:
            report["status"] = "degraded"
    return report
