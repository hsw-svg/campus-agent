import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.agents import router as agents_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.api.workspaces import router as workspaces_router
from app.api.attachments import router as attachments_router
from app.api.attachments import workspace_attachment_router
from app.api.agent_runs import router as agent_runs_router
from app.api.artifacts import router as artifacts_router
from app.api.courses import router as courses_router
from app.api.student_agents import router as student_agents_router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.db.session import create_database_engine, create_session_factory, make_database_probe
from app.integrations.embedding.providers import OpenAICompatibleEmbeddingProvider
from app.integrations.llm.providers import OpenAICompatibleChatProvider
from app.integrations.search.bing import BingSearchProvider
from app.integrations.pptx_renderer import PptxRenderer
from app.integrations.storage.local import LocalObjectStorage
from app.services.artifact_presentations import ArtifactPresentationService
from app.services.background_tasks import BackgroundTaskManager
from app.attachments.models import Attachment, MaterialChunk  # noqa: F401
from app.agents.models import AgentRun  # noqa: F401
from app.artifacts.models import Artifact  # noqa: F401
from app.workspaces.models import AnonymousWorkspace
from app.courses.models import Course  # noqa: F401

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()
    app = FastAPI(title=settings.app_name)
    engine = create_database_engine(settings.database_url)
    app.state.settings = settings
    app.state.database_engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.database_probe = make_database_probe(engine)
    app.state.chat_provider = OpenAICompatibleChatProvider(
        settings.chat_base_url,
        settings.chat_api_key,
        settings.chat_model,
    )
    app.state.embedding_provider = OpenAICompatibleEmbeddingProvider(
        settings.embedding_base_url,
        settings.embedding_api_key,
        settings.embedding_model,
    )
    app.state.object_storage = LocalObjectStorage(settings.local_storage_root)

    # PPTX renderer with LibreOffice + PyMuPDF; None if unavailable
    try:
        renderer = PptxRenderer(
            converter_path=settings.pptx_converter_path,
            timeout_seconds=settings.pptx_renderer_timeout,
        )
    except Exception:
        logger.warning(
            "PPTX renderer initialization failed; previews will be unavailable",
            exc_info=True,
        )
        renderer = None

    app.state.artifact_presentation_service = ArtifactPresentationService(
        app.state.object_storage,
        renderer=renderer,
    )
    app.state.background_task_manager = BackgroundTaskManager()
    app.state.workspace_model = AnonymousWorkspace
    app.state.bing_provider = BingSearchProvider(
        api_key=settings.bing_search_api_key,
        endpoint=settings.bing_search_endpoint,
    )

    if settings.chat_is_configured:
        try:
            from app.agents.nanobot.config import build_nanobot_config
            from app.agents.nanobot.runner import NanobotRunner

            app.state.nanobot_runner = NanobotRunner(
                build_nanobot_config(settings),
                bing_provider=app.state.bing_provider,
                chat_provider=app.state.chat_provider,
            )
        except (ImportError, ValueError, TypeError):
            logger.exception(
                "Nanobot initialization failed; course iteration will use the v1 executor"
            )
            app.state.nanobot_runner = None
    else:
        app.state.nanobot_runner = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content=error.to_payload())

    app.include_router(health_router)
    app.include_router(workspaces_router)
    app.include_router(conversations_router)
    app.include_router(agents_router)
    app.include_router(attachments_router)
    app.include_router(workspace_attachment_router)
    app.include_router(agent_runs_router)
    app.include_router(artifacts_router)
    app.include_router(courses_router)
    app.include_router(student_agents_router)
    return app


app = create_app()
