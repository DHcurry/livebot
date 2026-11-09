# -*- coding: utf-8 -*-
"""
客户端离线验证器（随你的产品分发，单文件独立）
公钥已嵌入 —— 反编译本文件也无法伪造授权。

CLI:
  python verify.py 授权文件.lic            用本机设备码验证
  python verify.py 授权文件.lic --hwid XX  指定设备码
  python verify.py "LIC1.xxxx.yyyy"        直接验证激活码字符串
  python verify.py 授权.lic --json         JSON 输出
退出码: 0=有效  1=无效

库方式:
  from verify import verify_license_text
  result = verify_license_text(lic_text)   # result.ok / result.reason / result.payload
"""
import base64
import json
import sys
import time
from datetime import date
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

EMBEDDED_PUBKEY = "C532B594EC34AB19FE663557C6D13DBEBEACD1B0920B88ACE34ABF6F53C56902"

MAGIC = "LIC1"
ANCHOR_PATH = Path(__file__).resolve().parent / "verify_anchor.json"
REVOCATION_FILE = Path(__file__).resolve().parent / "revocations.txt"


def load_revoked_ids() -> set:
    """自动加载同目录吊销名单（随应用更新分发；不存在则为空集）。"""
    if not REVOCATION_FILE.exists():
        return set()
    return {l.strip() for l in REVOCATION_FILE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


# ---- 与 core/license.py 同构的最小实现（无内部依赖） ----

def _b64u_dec(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def local_hwid() -> str:
    """本机设备码（与签发方 fingerprint.device_code 一致）。"""
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
            creationflags=0x08000000,
        )
        if (out.stdout or "").strip():
            cpu = out.stdout.strip()
    except Exception:
        pass
    try:
        mac = f"{uuid.getnode():012X}"
    except Exception:
        mac = "no-mac"
    raw = f"{guid.lower()}|{cpu.lower()}|{mac}"
    d = hashlib.blake2b(raw.encode(), digest_size=8).hexdigest().upper()
    return f"{d[:8]}-{d[8:]}"


class Result:
    def __init__(self, ok, reason, payload=None):
        self.ok = ok
        self.reason = reason
        self.payload = payload or {}

    def __bool__(self):
        return self.ok

    def to_dict(self):
        return {"ok": self.ok, "reason": self.reason, "payload": self.payload}


def verify_license_text(lic_text: str, hwid: str = "",
                        revoked_ids: set = None,
                        require_feature: str = "",
                        use_anchor: bool = True,
                        use_revocations: bool = True) -> Result:
    if revoked_ids is None and use_revocations:
        revoked_ids = load_revoked_ids()
    try:
        # 白名单清洗：传输可能混入零宽空格等隐形字符
        text = lic_text.translate(str.maketrans({"．": ".", "。": ".", "｡": "."}))
        text = "".join(ch for ch in text
                      if ch.isascii() and (ch.isalnum() or ch in "._-"))
        parts = text.split(".")
        if len(parts) != 3 or parts[0] != MAGIC:
            return Result(False, "bad_format")
        payload = json.loads(_b64u_dec(parts[1]).decode("utf-8"))
        sig = _b64u_dec(parts[2])
        if len(sig) != 64:
            return Result(False, "bad_format")
    except Exception:
        return Result(False, "bad_format")

    pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(EMBEDDED_PUBKEY))
    try:
        pub.verify(sig, _canonical(payload))
    except Exception:
        return Result(False, "bad_signature", payload)

    exp = payload.get("expires") or ""
    if exp:
        try:
            if date.today() > date.fromisoformat(exp):
                return Result(False, "expired", payload)
        except ValueError:
            return Result(False, "bad_format", payload)

    bound = payload.get("hwid") or ""
    if bound and hwid and bound != hwid.upper().strip():
        return Result(False, "hwid_mismatch", payload)
    # 首激活绑定：首次验证锁本机，防转卖（离线）
    if payload.get("bind") == "first" and hwid:
        bf = Path(__file__).resolve().parent / "bindings.json"
        try:
            store = json.loads(bf.read_text(encoding="utf-8")) if bf.exists() else {}
        except Exception:
            store = {}
        _id = payload.get("id", "")
        mine = hwid.upper().strip()
        if _id in store:
            if store[_id] != mine:
                return Result(False, "hwid_mismatch", payload)
        else:
            store[_id] = mine
            try:
                bf.write_text(json.dumps(store), encoding="utf-8")
            except Exception:
                pass

    if revoked_ids and payload.get("id") in revoked_ids:
        return Result(False, "revoked", payload)

    if require_feature:
        feats = payload.get("features") or "*"
        if feats != "*" and require_feature not in {f.strip() for f in feats.split(",")}:
            return Result(False, "feature_missing", payload)

    if use_anchor:
        try:
            now = time.time()
            if ANCHOR_PATH.exists():
                last = float(ANCHOR_PATH.read_text(encoding="ascii").strip() or 0)
                if last > now + 86400:
                    return Result(False, "clock_rollback", payload)
            ANCHOR_PATH.write_text(str(now), encoding="ascii")
        except Exception:
            pass

    return Result(True, "ok", payload)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    as_json = "--json" in sys.argv
    no_anchor = "--no-anchor" in sys.argv
    hwid = ""
    if "--hwid" in sys.argv:
        hwid = sys.argv[sys.argv.index("--hwid") + 1]
    if not args:
        print("用法: python verify.py <授权文件或激活码> [--hwid 码] [--json] [--no-anchor]")
        return 2
    src = args[0]
    text = src
    if Path(src).exists():
        text = Path(src).read_text(encoding="utf-8")
    if not hwid:
        hwid = local_hwid()
    res = verify_license_text(text, hwid=hwid, use_anchor=not no_anchor)
    if as_json:
        print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("✅ 授权有效" if res.ok else f"❌ 授权无效: {res.reason}")
        if res.payload:
            print(f"   客户: {res.payload.get('customer','')}  "
                  f"有效期: {res.payload.get('expires') or '永久'}  "
                  f"ID: {res.payload.get('id','')}")
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
