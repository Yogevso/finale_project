"""Request network helpers."""

from fastapi import Request

from app.config import settings


def _is_trusted_proxy(request: Request) -> bool:
    if not settings.TRUST_PROXY_HEADERS:
        return False

    trusted_ips = {ip.strip() for ip in settings.TRUSTED_PROXY_IPS if ip and ip.strip()}
    if not trusted_ips:
        return False

    client_ip = request.client.host if request.client else ""
    return client_ip in trusted_ips


def get_client_ip(request: Request) -> str:
    """Resolve client IP, trusting proxy headers only for known proxy IPs."""
    if _is_trusted_proxy(request):
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first_hop = forwarded.split(",")[0].strip()
            if first_hop:
                return first_hop

        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()

    return request.client.host if request.client else "unknown"
