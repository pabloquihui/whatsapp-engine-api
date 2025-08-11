from fastapi import APIRouter, Request, Header, HTTPException, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
from typing import Tuple, Optional
from services.engines.factory import get_engine
from services.whatsapp_client import get_client_for
from services.utils import compute_signature_ok
from schemas.whatsapp import SendMessageRequest
from logger import logger

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def get_store(request: Request):
    # Provided by app lifespan: app.state.tenants_store = TenantsStore()
    return request.app.state.tenants_store


def extract_ids(payload: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (phone_number_id, waba_id). Scans all entries/changes.
    """
    phone_number_id = None
    waba_id = None
    for entry in payload.get("entry", []):
        if not waba_id:
            waba_id = entry.get("id")  # WABA ID
        for change in entry.get("changes", []):
            value = change.get("value", {}) or {}
            meta = value.get("metadata", {}) or {}
            if meta.get("phone_number_id"):
                phone_number_id = str(meta["phone_number_id"])
    return phone_number_id, (str(waba_id) if waba_id else None)


@router.get("/webhook")
async def verify(
    request: Request,
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    if hub_mode != "subscribe" or not hub_verify_token:
        raise HTTPException(status_code=400, detail="Missing/invalid query params")

    store = get_store(request)
    tenant = await store.get_by_verify_token(hub_verify_token)  # <- await lookup
    if tenant:
        return PlainTextResponse(content=hub_challenge or "", media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook")
async def receive_webhook(
    request: Request,
    background: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
):
    raw = await request.body()
    payload = await request.json()

    phone_number_id, waba_id = extract_ids(payload)
    logger.info(f"Resolved IDs: phone_number_id={phone_number_id}, waba_id={waba_id}")

    store = get_store(request)
    tenant = None
    if phone_number_id:
        tenant = await store.get_by_phone_number_id(phone_number_id)  # <- await
    if not tenant and waba_id:
        tenant = await store.get_by_waba_id(waba_id)  # <- await

    if not tenant:
        logger.error(f"Unknown phone_number_id={phone_number_id} (waba_id={waba_id})")
        return {"status": "IGNORED"}  # don't 4xx to avoid webhook disablement

    # Per-tenant signature verification (if app_secret present)
    if tenant.app_secret:
        if not compute_signature_ok(raw, x_hub_signature_256, tenant.app_secret):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Process in background (don’t block webhook)
    background.add_task(process_events, tenant, payload)
    return {"status": "EVENT_RECEIVED"}


async def process_events(tenant, payload: dict):
    """
    tenant: TenantConfig (Pydantic) – use attributes (tenant.phone_number_id, tenant.access_token)
    """
    value = payload["entry"][0]["changes"][0]["value"]
    engine = await get_engine(
        tenant.model_dump()
    )  # pass as dict if your engine expects dict
    client = get_client_for(tenant.phone_number_id, tenant.access_token)

    for msg in value.get("messages", []):
        wa_id = msg.get("from")
        # optional: log raw types
        await handle_message(value, msg)
        reply_text = await engine.reply(tenant.model_dump(), msg)
        if reply_text:
            await client.send(wa_id, "text", {"body": reply_text})

    for status in value.get("statuses", []):
        logger.info(f"[{tenant.tenant_id}] status: {status}")


async def handle_message(context: dict, msg: dict):
    from_ = msg.get("from")
    msg_type = msg.get("type")

    if msg_type == "text":
        body = msg["text"]["body"]
        logger.info(f"[text] from {from_}: {body}")
    elif msg_type in {"image", "audio", "video", "document", "sticker"}:
        media = msg[msg_type]
        logger.info(f"[{msg_type}] from {from_}: {media}")
    elif msg_type == "location":
        loc = msg["location"]
        logger.info(f"[location] from {from_}: ({loc['latitude']}, {loc['longitude']})")
    elif msg_type == "contacts":
        logger.info(f"[contacts] from {from_}: {msg['contacts']}")
    elif msg_type == "interactive":
        i = msg["interactive"]
        if "button_reply" in i:
            br = i["button_reply"]
            logger.info(
                f"[interactive-button] from {from_}: id={br['id']} title={br['title']}"
            )
        elif "list_reply" in i:
            lr = i["list_reply"]
            logger.info(
                f"[interactive-list] from {from_}: id={lr['id']} title={lr['title']}"
            )
        else:
            logger.info(f"[interactive] from {from_}: {i}")
    else:
        logger.info(f"[unknown] type={msg_type} full={msg}")


async def handle_status(context: dict, status: dict):
    logger.info(f"[status] {status}")


@router.post("/send")
async def send_message(request: Request, req: SendMessageRequest):
    store = get_store(request)
    tenant = store.resolve_for_send(
        req.tenant_id, req.phone_number_id
    )  # sync resolver is fine
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    client = get_client_for(tenant.phone_number_id, tenant.access_token)
    try:
        result = await client.send(req.to, req.type, req.content)
        return {"ok": True, "tenant": tenant.tenant_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/_debug/tenants")
async def debug_tenants(request: Request):
    store = get_store(request)
    phone_keys = list(getattr(store, "_by_phone_id", {}).keys())
    return {"phone_ids": phone_keys}
