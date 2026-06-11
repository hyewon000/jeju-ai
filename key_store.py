"""
key_store.py — API 키 암호화 저장/로드 공유 모듈
launcher.py 와 app.py 에서 함께 사용한다.
"""

import base64
import hashlib
import json
import os
import socket
from pathlib import Path


def _data_dir() -> Path:
    d = Path(os.environ.get("APPDATA", Path.home())) / "GoyangPolicyReport"
    d.mkdir(parents=True, exist_ok=True)
    return d


KEYS_FILE = _data_dir() / "keys.enc"


def _fernet():
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    seed = (socket.gethostname() + os.environ.get("USERNAME", "user")).encode()
    salt = hashlib.sha256(seed).digest()[:16]
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    return Fernet(base64.urlsafe_b64encode(kdf.derive(seed)))


def load_keys() -> dict:
    if not KEYS_FILE.exists():
        return {}
    try:
        return json.loads(_fernet().decrypt(KEYS_FILE.read_bytes()).decode())
    except Exception:
        return {}


def save_keys(keys: dict):
    KEYS_FILE.write_bytes(_fernet().encrypt(json.dumps(keys).encode()))


def apply_keys(keys: dict):
    """os.environ 에 API 키를 반영한다. load_dotenv() 보다 먼저 호출해야 한다."""
    mapping = {
        "claude": "ANTHROPIC_API_KEY",
        "tavily": "TAVILY_API_KEY",
        "law":    "LAW_API_KEY",
    }
    for field, env_var in mapping.items():
        if keys.get(field):
            os.environ[env_var] = keys[field]


def mask_key(val: str) -> str:
    """키 앞 6자 + **** 형태로 마스킹한다."""
    if not val:
        return ""
    show = min(6, len(val) - 2)
    return val[:show] + "****" if show > 0 else "****"
