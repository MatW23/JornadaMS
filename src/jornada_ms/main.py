"""JornadaMS FastAPI application factory and CLI entry point."""

from fastapi import FastAPI

from jornada_ms.api.errors import register_exception_handlers
from jornada_ms.api.health import router as health_router
from jornada_ms.api.middleware import CorrelationIdMiddleware
from jornada_ms.config import Settings, get_settings
from jornada_ms.db.session import Database


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured application instance."""

    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        description="API REST privada do JornadaMS.",
    )
    app.state.settings = resolved_settings
    app.state.database = Database.from_settings(resolved_settings)
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name=resolved_settings.correlation_header,
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()


def run() -> None:
    """Run the development server through Uvicorn."""

    import uvicorn

    uvicorn.run("jornada_ms.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
