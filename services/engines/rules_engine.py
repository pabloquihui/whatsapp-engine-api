from .base import ResponseEngine


class RulesEngine(ResponseEngine):
    async def reply(self, tenant_cfg, message):
        text = (message.get("text") or {}).get("body", "")
        if not text:
            return "Gracias, recibí tu mensaje."
        if text.lower() in {"hola", "hello", "hi"}:
            return f"¡Hola de {tenant_cfg['display_name']}! ¿En qué puedo ayudarte?"
        return "Entendido. Estoy procesando tu solicitud."
