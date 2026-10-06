from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI

from core.adapters.controllers.http.exception_handler import register_exception_handlers
from core.adapters.controllers.http.routers import router
from core.config import Config
from core.ioc import AppProvider, CreatePaymentProvider, GetPaymentProvider, PostgresProvider, RepoProvider
from core.logger import setup_logging


def create_app() -> FastAPI:
    config = Config()
    setup_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.dishka_container.close()

    app = FastAPI(title='Paymaster', lifespan=lifespan)
    app.include_router(router)
    register_exception_handlers(app)
    container = make_async_container(
        AppProvider(),
        PostgresProvider(),
        RepoProvider(),
        CreatePaymentProvider(),
        GetPaymentProvider(),
        context={Config: config},
    )
    setup_dishka(container, app)
    return app


app = create_app()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
