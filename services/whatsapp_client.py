from __future__ import annotations
from functools import lru_cache
from typing import Any, Optional
from starlette.concurrency import run_in_threadpool
from heyoo import WhatsApp


class WhatsAppClient:
    """
    Wrapper around heyoo's (sync) WhatsApp client.
    Methods are exposed as async by running the blocking calls in a thread pool.
    One instance per (phone_number_id, token).
    """

    def __init__(self, token: str, phone_number_id: str):
        # per docs: WhatsApp(token, phone_number_id='...')
        self.messenger = WhatsApp(token, phone_number_id=str(phone_number_id))

    # --- Typed helpers (async wrappers over sync heyoo) ---

    async def send_text(self, to: str, body: str):
        # heyoo README: send_message('Your message', '2557...')
        return await run_in_threadpool(self.messenger.send_message, body, to)

    async def send_image(self, to: str, link: str, caption: Optional[str] = None):
        return await run_in_threadpool(
            self.messenger.send_image, image=link, recipient_id=to, caption=caption
        )

    async def send_audio(self, to: str, link: str):
        return await run_in_threadpool(
            self.messenger.send_audio, audio=link, recipient_id=to
        )

    async def send_video(self, to: str, link: str, caption: Optional[str] = None):
        return await run_in_threadpool(
            self.messenger.send_video, video=link, recipient_id=to, caption=caption
        )

    async def send_document(
        self,
        to: str,
        link: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
    ):
        return await run_in_threadpool(
            self.messenger.send_document,
            document=link,
            recipient_id=to,
            filename=filename,
            caption=caption,
        )

    async def send_sticker(self, to: str, link: str):
        send_sticker = getattr(self.messenger, "send_sticker", None)
        if not send_sticker:
            raise NotImplementedError(
                "send_sticker is not available in this heyoo version"
            )
        return await run_in_threadpool(send_sticker, sticker=link, recipient_id=to)

    async def send_location(
        self,
        to: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ):
        # README uses lat/long keywords
        return await run_in_threadpool(
            self.messenger.send_location,
            lat=latitude,
            long=longitude,
            name=name,
            address=address,
            recipient_id=to,
        )

    async def send_button(self, to: str, button_payload: dict[str, Any]):
        return await run_in_threadpool(
            self.messenger.send_button, recipient_id=to, button=button_payload
        )

    async def send_reply_button(self, to: str, button_payload: dict[str, Any]):
        return await run_in_threadpool(
            self.messenger.send_reply_button, recipient_id=to, button=button_payload
        )

    async def send_template(
        self,
        to: str,
        name: str,
        lang: str = "en_US",
        components: list[dict] | None = None,
    ):
        # README: send_template("hello_world", "2557...", components=[], lang="en_US")
        return await run_in_threadpool(
            self.messenger.send_template,
            name,
            to,
            components=components or [],
            lang=lang,
        )

    # --- Generic entrypoint used by the router (/send) ---

    async def send(self, to: str, type_: str, content: dict[str, Any]):
        match type_:
            case "text":
                return await self.send_text(to, content.get("body", ""))

            case "image":
                return await self.send_image(
                    to, content["link"], content.get("caption")
                )

            case "audio":
                return await self.send_audio(to, content["link"])

            case "video":
                return await self.send_video(
                    to, content["link"], content.get("caption")
                )

            case "document":
                return await self.send_document(
                    to, content["link"], content.get("filename"), content.get("caption")
                )

            case "sticker":
                return await self.send_sticker(to, content["link"])

            case "location":
                lat = content.get("latitude", content.get("lat"))
                lon = content.get("longitude", content.get("long"))
                if lat is None or lon is None:
                    raise ValueError("location content must include latitude/longitude")
                return await self.send_location(
                    to,
                    float(lat),
                    float(lon),
                    content.get("name"),
                    content.get("address"),
                )

            case "contacts":
                send_contacts = getattr(self.messenger, "send_contacts", None)
                if not send_contacts:
                    raise NotImplementedError(
                        "send_contacts is not available in this heyoo version"
                    )
                return await run_in_threadpool(
                    send_contacts, contacts=content["contacts"], recipient_id=to
                )

            case "interactive":
                # Auto-pick reply vs list buttons
                button = content.get("button") or content
                action = (button or {}).get("action", {})
                buttons = action.get("buttons", [])
                if (
                    buttons
                    and isinstance(buttons, list)
                    and buttons[0].get("type") == "reply"
                ):
                    return await self.send_reply_button(to, button)
                return await self.send_button(to, button)

            case "template":
                name = content["name"]
                lang = (
                    content.get("lang")
                    or (content.get("language") or {}).get("code")
                    or "en_US"
                )
                components = content.get("components", [])
                return await self.send_template(
                    to, name, lang=lang, components=components
                )

            case _:
                raise ValueError(f"Unsupported message type: {type_}")


@lru_cache(maxsize=256)
def get_client_for(phone_number_id: str, token: str) -> WhatsAppClient:
    # normalize to strings to avoid cache key mismatches
    return WhatsAppClient(token=str(token), phone_number_id=str(phone_number_id))
