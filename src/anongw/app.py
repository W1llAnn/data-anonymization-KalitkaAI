"""Сборка приложения: компоненты соединяются по контрактам contracts.py."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from anongw import __version__
from anongw.anonymizer.persistent import PersistentAnonymizer
from anongw.api.errors import register_error_handlers
from anongw.api.routes import router
from anongw.config import Settings
from anongw.contracts import MappingStore
from anongw.files.extractor import TxtDocxFileExtractor
from anongw.mapping.sqlite_store import SqliteMappingStore
from anongw.restorer.service import MappingRestorer
from anongw.upstream.client import HttpxUpstreamClient

_logger = logging.getLogger("anongw.mapping")


async def _ttl_cleanup_loop(store: MappingStore, interval_seconds: int) -> None:
    """Фоновая очистка просроченных записей (план: docs/mapping/context-id.md)."""
    while True:
        await asyncio.sleep(interval_seconds)
        removed = await store.cleanup_expired()
        if removed:
            _logger.info("TTL-очистка: удалено записей — %d", removed)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(
        _ttl_cleanup_loop(app.state.mapping_store, app.state.settings.cleanup_interval_seconds)
    )
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(title="anongw", version=__version__, lifespan=_lifespan)
    register_error_handlers(app)
    app.include_router(router)

    mapping_store = SqliteMappingStore(settings.mapping_db_path, settings.mapping_ttl_hours)
    app.state.settings = settings
    app.state.mapping_store = mapping_store
    app.state.anonymizer = PersistentAnonymizer(mapping_store)
    app.state.restorer = MappingRestorer(mapping_store)
    app.state.extractor = TxtDocxFileExtractor(settings)
    app.state.upstream = HttpxUpstreamClient(settings)
    return app


app = create_app()
