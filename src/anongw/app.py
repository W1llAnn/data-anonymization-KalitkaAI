"""Сборка приложения: компоненты соединяются по контрактам contracts.py."""

from __future__ import annotations

from fastapi import FastAPI

from anongw import __version__
from anongw.anonymizer.service import PassThroughAnonymizer
from anongw.api.routes import router
from anongw.config import Settings
from anongw.files.extractor import TxtDocxFileExtractor
from anongw.mapping.store import InMemoryMappingStore
from anongw.restorer.service import MappingRestorer
from anongw.upstream.client import HttpxUpstreamClient


def create_app() -> FastAPI:
    settings = Settings()

    app = FastAPI(title="anongw", version=__version__)
    app.include_router(router)

    # Компоненты недели 1 — заглушки, удовлетворяющие контрактам.
    # По мере готовности ролей заменяются на рабочие реализации; контракты не меняются.
    # Хранилище: InMemory → SqliteMappingStore(mapping_db_path, mapping_ttl_hours) от Р5.
    mapping_store = InMemoryMappingStore()
    app.state.settings = settings
    app.state.mapping_store = mapping_store
    app.state.anonymizer = PassThroughAnonymizer()
    app.state.restorer = MappingRestorer(mapping_store)
    app.state.extractor = TxtDocxFileExtractor(settings)
    app.state.upstream = HttpxUpstreamClient(settings)
    return app


app = create_app()
