from typing import Optional, Protocol
from pydantic import BaseModel


class TenantConfig(BaseModel):
    tenant_id: str
    display_name: str
    waba_id: str | None = None
    phone_number_id: str
    verify_token: str
    app_secret: str | None = None
    access_token: str
    engine: dict
    status: str = "active"


class TenantsLoader(Protocol):
    async def by_phone_number_id(self, phone_number_id: str) -> Optional[dict]: ...
    async def by_verify_token(self, verify_token: str) -> Optional[dict]: ...
    async def by_waba_id(self, waba_id: str) -> Optional[dict]: ...


class TenantsStore:
    def __init__(self):
        self._by_verify_token: dict[str, TenantConfig] = {}
        self._by_phone_id: dict[str, TenantConfig] = {}
        self._by_waba_id: dict[str, TenantConfig] = {}
        self._by_tenant_id: dict[str, TenantConfig] = {}
        self._loader: Optional[TenantsLoader] = None

    def set_loader(self, loader: TenantsLoader):
        self._loader = loader

    def _index(self, t: dict | TenantConfig):
        cfg = t if isinstance(t, TenantConfig) else TenantConfig(**t)
        self._by_verify_token[str(cfg.verify_token)] = cfg
        self._by_phone_id[str(cfg.phone_number_id)] = cfg
        if cfg.waba_id:
            self._by_waba_id[str(cfg.waba_id)] = cfg
        self._by_tenant_id[str(cfg.tenant_id)] = cfg

    def seed_for_dev(self, tenants: list[dict]):
        for t in tenants:
            # normalize to strings
            for k in ("phone_number_id", "waba_id", "verify_token", "tenant_id"):
                if k in t and t[k] is not None:
                    t[k] = str(t[k])
            self._index(t)

    async def get_by_verify_token(self, verify_token: str) -> Optional[TenantConfig]:
        verify_token = str(verify_token)
        if verify_token in self._by_verify_token:
            return self._by_verify_token[verify_token]
        if self._loader:
            t = await self._loader.by_verify_token(verify_token)
            if t:
                self._index(t)
                return self._by_verify_token[verify_token]
        return None

    async def get_by_phone_number_id(
        self, phone_number_id: str
    ) -> Optional[TenantConfig]:
        phone_number_id = str(phone_number_id)
        if phone_number_id in self._by_phone_id:
            return self._by_phone_id[phone_number_id]
        if self._loader:
            t = await self._loader.by_phone_number_id(phone_number_id)
            if t:
                self._index(t)
                return self._by_phone_id[phone_number_id]
        return None

    async def get_by_waba_id(self, waba_id: str) -> Optional[TenantConfig]:
        waba_id = str(waba_id)
        if waba_id in self._by_waba_id:
            return self._by_waba_id[waba_id]
        if self._loader:
            t = await self._loader.by_waba_id(waba_id)
            if t:
                self._index(t)
                return self._by_waba_id[waba_id]
        return None

    def resolve_for_send(
        self, tenant_id: str | None, phone_number_id: str | None
    ) -> Optional[TenantConfig]:
        if tenant_id and str(tenant_id) in self._by_tenant_id:
            return self._by_tenant_id[str(tenant_id)]
        if phone_number_id and str(phone_number_id) in self._by_phone_id:
            return self._by_phone_id[str(phone_number_id)]
        return None


tenants_store = TenantsStore()
