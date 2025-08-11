import hmac
import hashlib


def compute_signature_ok(
    raw_body: bytes, header_signature: str | None, app_secret: str
) -> bool:
    if not header_signature or not header_signature.startswith("sha256="):
        return False
    provided = header_signature.split("=", 1)[1]
    expected = hmac.new(
        app_secret.encode("utf-8"), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, provided)
