"""
The app-factory pattern.

Copy to app/core/app.py. create_app() is the single place that builds the
FastAPI instance: settings, middleware, exception handlers, and router
inclusion are all wired here so main.py stays a one-liner and tests can
build fresh app instances with overridden dependencies.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.shared.errors import AppException

# Import each module's router here as modules are added, e.g.:
# from app.modules.products.api.routes import router as products_router

API_V1_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()

    # Docs are only ever served when debug is on. A production deployment
    # that leaves debug=False (the default) never exposes /docs, /redoc, or
    # the raw OpenAPI schema — an accidental leak of internal endpoint/schema
    # detail is a common, easy-to-miss issue in FastAPI apps shipped as-is.
    app = FastAPI(
        title=settings.app.app_name,
        debug=settings.app.debug,
        docs_url="/docs" if settings.app.debug else None,
        redoc_url="/redoc" if settings.app.debug else None,
        openapi_url="/openapi.json" if settings.app.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    register_routers(app)

    return app


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


def register_routers(app: FastAPI) -> None:
    # app.include_router(products_router, prefix=API_V1_PREFIX)
    # Add one line per module here as fastapi-module-scaffold creates them.
    pass
