from abc import ABC, abstractmethod


class ResponseEngine(ABC):
    @abstractmethod
    async def reply(self, tenant_cfg: dict, message: dict) -> str | None: ...
