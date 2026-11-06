from __future__ import annotations

from ..config import KeysteadConfig
from .base import Connector, ConnectorError, Receipt


def build_connectors(cfg: KeysteadConfig) -> dict[str, Connector]:
    """Return action -> connector. Two connectors may not claim the same action."""
    out: dict[str, Connector] = {}
    for name, c in cfg.connectors.items():
        extra = c.model_extra or {}
        conn: Connector
        if name == "cloudflare_dns":
            from .cloudflare_dns import CloudflareDNS

            conn = CloudflareDNS(c.secret, c.zones)
        elif name == "octodns_dns":
            from .octodns_dns import OctoDNS

            if "provider" not in extra or "secret_kwarg" not in extra:
                raise ConnectorError("octodns_dns needs `provider` and `secret_kwarg`")
            conn = OctoDNS(c.secret, c.zones, extra["provider"], extra["secret_kwarg"], extra.get("options"))
        elif name == "postiz_social":
            from .postiz_social import PostizSocial

            if "base_url" not in extra:
                raise ConnectorError("postiz_social needs `base_url`")
            conn = PostizSocial(c.secret, extra["base_url"], extra.get("integrations"))
        else:
            raise ConnectorError(f"unknown connector {name}")
        for action in conn.actions:
            if action in out:
                raise ConnectorError(f"{action} is provided by both {out[action].name} and {name}; enable one")
            out[action] = conn
    return out


__all__ = ["Connector", "ConnectorError", "Receipt", "build_connectors"]
