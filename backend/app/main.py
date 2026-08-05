from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import connector_sync, graph, hcag, router
from app.auth.mcp_oauth import oauth_router
from app.auth.middleware import AuthenticationBoundaryMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging
from app.ingestion.maintenance import sanitize_existing_index


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.assert_safe_for_environment()
    configure_logging()
    init_db()
    with suppress(Exception):
        graph.initialize()
    with suppress(Exception):
        sanitize_existing_index(graph, hcag)
    # Legacy-vector migration can touch thousands of chunks. Run it in a
    # background worker so health checks and the read path become available
    # immediately; mixed-model chunks remain safe because dense scoring only
    # compares vectors produced by the active model.
    backfill_task = asyncio.create_task(asyncio.to_thread(hcag.backfill_existing_chunks))
    sync_worker_task = None
    if settings.connector_sync_worker_enabled:
        async def run_connector_sync_worker() -> None:
            while True:
                await asyncio.to_thread(connector_sync.run_once)
                await asyncio.sleep(max(1, settings.connector_sync_poll_seconds))

        sync_worker_task = asyncio.create_task(run_connector_sync_worker())
    yield
    if not backfill_task.done():
        backfill_task.cancel()
    if sync_worker_task and not sync_worker_task.done():
        sync_worker_task.cancel()


app = FastAPI(title="OrgMemory API", version="1.0.0", lifespan=lifespan)
allowed_origins = [settings.frontend_url.rstrip("/")]
if settings.environment.casefold() != "production":
    # Browsers treat localhost and 127.0.0.1 as different origins. Accept both
    # during local development so a loopback URL cannot make every API request
    # look like a network failure. Production remains restricted to FRONTEND_URL.
    for loopback_origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        if loopback_origin not in allowed_origins:
            allowed_origins.append(loopback_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthenticationBoundaryMiddleware)
app.include_router(router)
app.include_router(oauth_router)


@app.get("/")
def root():
    return {
        "name": "OrgMemory",
        "tagline": "The persistent memory layer for company AI agents.",
        "docs": "/docs",
    }
