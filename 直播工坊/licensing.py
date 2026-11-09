# -*- coding: utf-8 -*-
"""
直播工坊 · 授权模块
- 复用【卡密系统】的 Ed25519 客户端验证逻辑（公钥已嵌入本文件）
- 授权文件存 %LOCALAPPDATA%\LiveStudio\license.dat
- 首次运行/无效时弹激活窗：显示设备码 + 粘贴激活码 / 导入 .lic
"""
import base64
import json
import os
import sys
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

# ==== 由卡密系统签发方公钥（issuer init 生成，本机签发方 data/public.hex） ====
EMBEDDED_PUBKEY = "C532B594EC34AB19FE663557C6D13DBEBEACD1B0920B88ACE34ABF6F53C56902"

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LiveStudio"
LICENSE_FILE = APP_DIR / "license.dat"
MAGIC = "LIC1"
SERVER_URL = "http://154.36.130.188:8777"   # 云端签发中心（卡密在线激活）


def redeem_cardkey(key: str) -> str:
    """卡密在线激活：用 19 位短卡密从云端取回完整激活码。"""
    import urllib.request
    url = f"{SERVER_URL}/api/redeem?k={key.strip().upper()}"
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    if not data.get("ok") or not data.get("lic"):
        raise ValueError("卡密不存在或已失效")
    return data["lic"]


def _b64u_dec(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


_DEV_CACHE = None


def device_code() -> str:
    """本机设备码（进程内缓存——原始实现每次起PowerShell卡1.3秒，禁止热路径重复调用）"""
    global _DEV_CACHE
    if _DEV_CACHE:
        return _DEV_CACHE
    import hashlib
    import subprocess
    import uuid
    guid = "no-machine-guid"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography") as k:
            guid = str(winreg.QueryValueEx(k, "MachineGuid")[0]).strip()
    except Exception:
        pass
    cpu = "no-processor-id"
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor | Select-Object -First 1).ProcessorId"],
            capture_output=True, text=True, timeout=15,
            creationflags=0x08000000)
        if (out.stdout or "").strip():
            cpu = out.stdout.strip()
    except Exception:
        pass
    try:
        mac = f"{uuid.getnode():012X}"
    except Exception:
        mac = "no-mac"
    d = hashlib.blake2b(f"{guid.lower()}|{cpu.lower()}|{mac}".encode(),
                        digest_size=8).hexdigest().upper()
    _DEV_CACHE = f"{d[:8]}-{d[8:]}"
    return _DEV_CACHE


def verify_text(lic_text: str, hwid: str):
    """返回 (ok, reason, payload)。与卡密系统 client/verify.py 同构。"""
    try:
        # 白名单清洗：传输过程可能混入零宽空格/不换行空格/全角标点等隐形字符
        text = lic_text.translate(str.maketrans({"．": ".", "。": ".", "｡": "."}))
        text = "".join(ch for ch in text
                      if ch.isascii() and (ch.isalnum() or ch in "._-"))
        parts = text.split(".")
        if len(parts) != 3 or parts[0] != MAGIC:
            return False, "bad_format", {}
        payload = json.loads(_b64u_dec(parts[1]).decode("utf-8"))
        sig = _b64u_dec(parts[2])
        if len(sig) != 64:
            return False, "bad_format", {}
    except Exception:
        return False, "bad_format", {}
    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(EMBEDDED_PUBKEY))
    try:
        pub.verify(sig, _canonical(payload))
    except Exception:
        return False, "bad_signature", payload
    exp = payload.get("expires") or ""
    if exp:
        try:
            if date.today() > date.fromisoformat(exp):
                return False, "expired", payload
        except ValueError:
            return False, "bad_format", payload
    bound = payload.get("hwid") or ""
    if bound and bound != hwid.upper().strip():
        return False, "hwid_mismatch", payload
    # 首激活绑定：首次验证时锁定本机，防转卖（离线完成，不需服务器）
    if payload.get("bind") == "first" and hwid:
        bind_file = APP_DIR / "bindings.json"
        try:
            store = json.loads(bind_file.read_text(encoding="utf-8")) \
                if bind_file.exists() else {}
        except Exception:
            store = {}
        _id = payload.get("id", "")
        mine = hwid.upper().strip()
        if _id in store:
            if store[_id] != mine:
                return False, "hwid_mismatch", payload
        else:
            store[_id] = mine
            APP_DIR.mkdir(parents=True, exist_ok=True)
            bind_file.write_text(json.dumps(store), encoding="utf-8")
    return True, "ok", payload


def load_stored():
    if LICENSE_FILE.exists():
        return LICENSE_FILE.read_text(encoding="utf-8")
    return ""


def clear_license() -> bool:
    """清除本机授权（换机/换码前清位）。"""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.unlink()
            return True
    except Exception:
        pass
    return False


def current_info():
    """当前授权展示信息：(ok, payload)。"""
    text = load_stored()
    if not text:
        return False, {}
    ok, _reason, payload = verify_text(text, device_code())
    return ok, payload


def save_license(lic_text: str):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(lic_text.strip(), encoding="utf-8")


def check():
    """启动检查。返回 (ok, reason, payload)。"""
    text = load_stored()
    if not text:
        return False, "no_license", {}
    return verify_text(text, device_code())


def import_sibling_license():
    """首次运行时自动导入程序目录下的 我的授权.lic（发行者自用/预装场景）。"""
    if LICENSE_FILE.exists():
        return check()
    for cand in (Path(sys.executable).parent, Path(__file__).resolve().parent,
                 Path(sys.argv[0]).resolve().parent):
        f = cand / "我的授权.lic"
        if f.exists():
            text = f.read_text(encoding="utf-8")
            ok, reason, payload = verify_text(text, device_code())
            if ok:
                save_license(text)
                return True, "ok", payload
    return check()
