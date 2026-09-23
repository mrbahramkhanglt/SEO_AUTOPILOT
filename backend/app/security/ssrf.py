"""SSRF protection – validate URLs before crawling."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "metadata.google",
    "metadata",
    "kubernetes.default",
    "kubernetes.default.svc",
}


class SSRFError(ValueError):
    pass


def is_ip_blocked(ip_str: str) -> bool:
    try:
        return _is_blocked_ip(ipaddress.ip_address(ip_str))
    except ValueError:
        return False


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        return True
    for net in BLOCKED_NETWORKS:
        try:
            if ip in net:
                return True
        except TypeError:
            continue
    return False


def validate_url_for_crawl(url: str) -> str:
    """
    Validate URL is safe to fetch. Returns normalized URL or raises SSRFError.
    Resolves DNS and rejects private/metadata targets.
    """
    if not url or not isinstance(url, str):
        raise SSRFError("URL is required")
    url = url.strip()
    if len(url) > 2048:
        raise SSRFError("URL too long")
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFError("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise SSRFError("URL must include a hostname")
    host = parsed.hostname.lower().rstrip(".")
    if host in BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        raise SSRFError("Hostname is not allowed")
    if parsed.username or parsed.password:
        raise SSRFError("URLs with embedded credentials are not allowed")
    # Block literal IPs that are private
    try:
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip):
            raise SSRFError("IP address is not allowed")
        return url
    except ValueError:
        pass  # hostname, resolve below

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise SSRFError(f"Could not resolve hostname: {host}") from e
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if _is_blocked_ip(ip):
            raise SSRFError("Hostname resolves to a blocked address")
    # Prefer https normalization only when scheme missing – already required
    return url
