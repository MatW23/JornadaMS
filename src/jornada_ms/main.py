"""JornadaMS FastAPI application factory and CLI entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from jornada_ms.api.errors import register_exception_handlers
from jornada_ms.api.health import router as health_router
from jornada_ms.api.middleware import CorrelationIdMiddleware
from jornada_ms.config import Settings, get_settings
from jornada_ms.db.session import Database
from jornada_ms.modules.attendance.api import router as attendance_router
from jornada_ms.modules.employees.api import router as employees_router
from jornada_ms.modules.identity.api import router as identity_router
from jornada_ms.modules.organization.api import router as organization_router
from jornada_ms.modules.schedules.api import router as schedules_router


def _frontend_directory() -> Path | None:
    """Locate the checked-in client in source and container executions."""

    candidates = (
        Path(__file__).resolve().parents[2] / "frontend",
        Path.cwd() / "frontend",
    )
    return next((directory for directory in candidates if directory.is_dir()), None)


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
    app.include_router(identity_router)
    app.include_router(organization_router)
    app.include_router(employees_router)
    app.include_router(attendance_router)
    app.include_router(schedules_router)
    frontend_directory = _frontend_directory()
    if frontend_directory is not None:
        app.mount(
            "/static",
            StaticFiles(directory=frontend_directory),
            name="frontend-static",
        )

        @app.get("/", include_in_schema=False)
        async def client_application() -> FileResponse:
            return FileResponse(frontend_directory / "index.html")

    return app


app = create_app()


def run() -> None:
    """Run the development server through Uvicorn."""

    import uvicorn

    uvicorn.run("jornada_ms.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
