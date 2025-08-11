from .rules_engine import RulesEngine
from .openai_engine import OpenAIEngine
from .mistral_engine import MistralLangChainEngine


async def get_engine(tenant_cfg: dict):
    etype = tenant_cfg["engine"]["type"]
    cfg = tenant_cfg["engine"]["config"]
    if etype == "rules":
        return RulesEngine()
    if etype == "openai":
        return OpenAIEngine(cfg or {})
    if etype == "mistral":
        return MistralLangChainEngine(cfg or {})
    # Add 'openai' / 'azure_openai' here later
    raise ValueError(f"Unsupported engine type: {etype}")
