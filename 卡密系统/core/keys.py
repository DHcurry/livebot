# -*- coding: utf-8 -*-
"""
密钥对管理（Ed25519）
- issuer.key : 私钥（PEM）——只留在签发方，绝不进客户机
- 公钥以 32 字节 raw hex 形式嵌入客户端验证器
"""
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

PRIV_NAME = "issuer.key"
PUB_PEM_NAME = "public.pem"
PUB_HEX_NAME = "public.hex"


def generate_keypair(data_dir: Path):
    """生成新密钥对，写入 data_dir。返回 (私钥对象, 公钥hex)。"""
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    priv_path = data_dir / PRIV_NAME
    priv_path.write_bytes(priv_pem)
    try:
        import os
        os.chmod(priv_path, 0o600)
    except OSError:
        pass
    pub_hex = export_public_hex(priv)
    (data_dir / PUB_HEX_NAME).write_text(pub_hex + "\n", encoding="ascii")
    (data_dir / PUB_PEM_NAME).write_bytes(
        priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return priv, pub_hex


def load_private(data_dir: Path) -> Ed25519PrivateKey:
    path = Path(data_dir) / PRIV_NAME
    if not path.exists():
        raise FileNotFoundError(f"私钥不存在: {path}（先执行 init）")
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def key_exists(data_dir: Path) -> bool:
    return (Path(data_dir) / PRIV_NAME).exists()


def export_public_hex(priv: Ed25519PrivateKey) -> str:
    pub = priv.public_key()
    raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex().upper()


def load_public_from_hex(hex_str: str) -> Ed25519PublicKey:
    raw = bytes.fromhex(hex_str.strip().replace(" ", "").replace(":", ""))
    if len(raw) != 32:
        raise ValueError("公钥必须是 32 字节（64 位十六进制）")
    return Ed25519PublicKey.from_public_bytes(raw)
