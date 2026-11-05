"""AES-256-GCM secret store in data/vault.json. One fresh 12-byte nonce per value."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class VaultError(Exception):
    pass


def new_master_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


class Vault:
    def __init__(self, path: Path, master_key_b64: str | None):
        if not master_key_b64:
            raise VaultError("KEYSTEAD_MASTER_KEY is not set (run `keystead init`)")
        try:
            key = base64.b64decode(master_key_b64, validate=True)
        except Exception as e:
            raise VaultError("KEYSTEAD_MASTER_KEY is not valid base64") from e
        if len(key) != 32:
            raise VaultError("KEYSTEAD_MASTER_KEY must decode to 32 bytes")
        self._aes = AESGCM(key)
        self.path = path

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        os.chmod(tmp, 0o600)
        tmp.replace(self.path)

    def set(self, name: str, value: str) -> None:
        if not value:
            raise VaultError("empty secret")
        nonce = os.urandom(12)
        ct = self._aes.encrypt(nonce, value.encode(), name.encode())
        data = self._load()
        data[name] = {"nonce": base64.b64encode(nonce).decode(), "ct": base64.b64encode(ct).decode()}
        self._save(data)

    def get(self, name: str) -> str:
        entry = self._load().get(name)
        if entry is None:
            raise VaultError(f"secret {name!r} not in vault (run `keystead secret set {name}`)")
        try:
            return self._aes.decrypt(
                base64.b64decode(entry["nonce"]), base64.b64decode(entry["ct"]), name.encode()
            ).decode()
        except Exception as e:
            raise VaultError(f"secret {name!r} cannot be decrypted with this master key") from e

    def names(self) -> list[str]:
        return sorted(self._load())

    def all_values(self) -> list[str]:
        return [self.get(n) for n in self.names()]


class Redactor:
    """Removes every stored secret value from outgoing text."""

    def __init__(self, values: list[str]):
        self.values = sorted({v for v in values if len(v) >= 4}, key=len, reverse=True)

    def __call__(self, text: str) -> str:
        for v in self.values:
            text = text.replace(v, "[redacted]")
        return text

    def scrub(self, obj):
        if isinstance(obj, str):
            return self(obj)
        if isinstance(obj, dict):
            return {k: self.scrub(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.scrub(v) for v in obj]
        return obj
