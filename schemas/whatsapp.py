from pydantic import BaseModel, Field, model_validator
from typing import Literal, Any

MessageType = Literal[
    "text",
    "image",
    "audio",
    "video",
    "document",
    "sticker",
    "location",
    "contacts",
    "interactive",
    "template",
]


class SendMessageRequest(BaseModel):
    tenant_id: str | None = Field(
        default=None, description="Preferred way to select tenant"
    )
    phone_number_id: str | None = Field(
        default=None, description="Alternative if no tenant_id"
    )

    to: str = Field(..., description="Recipient in E.164 without +, e.g. 5218112345678")
    type: MessageType
    content: dict[str, Any]

    @model_validator(mode="after")
    def _require_tenant_hint(self):
        if not self.tenant_id and not self.phone_number_id:
            raise ValueError("Provide either tenant_id or phone_number_id")
        return self
