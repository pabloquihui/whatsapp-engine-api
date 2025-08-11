from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from logger import logger
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import json
import asyncio
from routers.whatsapp import router as whatsapp_router
from core.config import settings
from data.tenants_store import tenants_store

asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Thread pool for sync heyoo calls
    loop = asyncio.get_running_loop()
    app.state.executor = ThreadPoolExecutor(max_workers=32)
    loop.set_default_executor(app.state.executor)

    # Make tenant store available to routers
    app.state.tenants_store = tenants_store

    # Dev seeding (optional)
    if settings.APP_ENV != "production":
        tenants = None
        try:
            if settings.TENANT_DEV_SEED_FILE:
                with open(settings.TENANT_DEV_SEED_FILE, "r", encoding="utf-8") as f:
                    tenants = json.load(f)
        except Exception as e:
            logger.error(f"Failed to parse TENANT_DEV_SEED: {e}")

        if tenants:
            tenants_store.seed_for_dev(tenants)
            logger.info(f"[DEV] Seeded {len(tenants)} tenants")
            logger.info(
                f"[DEV] phone_ids={list(getattr(tenants_store, '_by_phone_id', {}).keys())}"
            )
        else:
            logger.warning("[DEV] No tenants seeded")

    # TODO (prod): attach real loader (Cosmos/KeyVault) here via tenants_store.set_loader(...)
    yield

    # Cleanup
    app.state.executor.shutdown(wait=True)


# FastAPI setup
app = FastAPI(lifespan=lifespan)
app.include_router(whatsapp_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def health_check():
    return {"status": "healthy"}
