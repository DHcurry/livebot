# -*- coding: utf-8 -*-
"""
授权载荷 / 签发 / 离线验证

.lic 格式:  LIC1.<base64url(载荷JSON)>.<base64url(签名64B)>
载荷 JSON : 规范化（键排序、无空白、UTF-8），签名直接签载荷文本本身
验证只嵌入 32 字节公钥 —— 客户端被反编译也无法伪造新授权
"""
import base64
import json
import time
from datetime import date, datetime

MAGIC = "LIC1"

# ---------- 编解码 ----------

def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64u_dec(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def canonical_payload(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def make_payload(
    customer: str,
    hwid: str = "",            # 空 = 不绑定设备
    expires: str = "",         # YYYY-MM-DD；空 = 永久
    features: str = "*",       # "*" 或 逗号分隔功能名
    product: str = "any",
    notes: str = "",
    license_id: str = "",
    bind_first: bool = False,  # 首激活绑定：首次验证时锁定设备，防转卖
) -> dict:
    if not license_id:
        import uuid
        license_id = str(uuid.uuid4())
    issued = date.today().isoformat()
    payload = {
        "v": 1,
        "id": license_id,
        "customer": customer,
        "hwid": "" if bind_first else hwid.upper().strip(),
        "issued": issued,
        "expires": expires.strip(),
        "features": features.strip() or "*",
        "product": product.strip() or "any",
        "notes": notes.strip(),
    }
    if bind_first:
        payload["bind"] = "first"
    # 简单格式自检
    if payload["expires"]:
        date.fromisoformat(payload["expires"])
    return payload


def sign_license(payload: dict, priv) -> str:
    body = canonical_payload(payload)
    sig = priv.sign(body)
    return f"{MAGIC}.{_b64u(body)}.{_b64u(sig)}"


def parse_license(lic_text: str) -> tuple:
    """返回 (载荷 dict, 签名 bytes)。格式错误抛 ValueError。"""
    # 白名单清洗：微信/QQ 传输常插入零宽空格等隐形字符
    text = lic_text.translate(str.maketrans({"．": ".", "。": ".", "｡": "."}))
    text = "".join(ch for ch in text
                  if ch.isascii() and (ch.isalnum() or ch in "._-"))
    parts = text.split(".")
    if len(parts) != 3 or parts[0] != MAGIC:
        raise ValueError("格式错误：应为 LIC1.<载荷>.<签名>")
    payload = json.loads(_b64u_dec(parts[1]).decode("utf-8"))
    sig = _b64u_dec(parts[2])
    if len(sig) != 64:
        raise ValueError("签名长度错误")
    return payload, sig


# ---------- 验证 ----------

class VerifyResult:
    OK = "ok"
    BAD_FORMAT = "bad_format"
    BAD_SIGNATURE = "bad_signature"
    EXPIRED = "expired"
    HWID_MISMATCH = "hwid_mismatch"
    REVOKED = "revoked"
    CLOCK_ROLLBACK = "clock_rollback"
    FEATURE_MISSING = "feature_missing"

    def __init__(self, ok: bool, reason: str, payload: dict = None):
        self.ok = ok
        self.reason = reason
        self.payload = payload or {}

    def __bool__(self):
        return self.ok

    def to_dict(self):
        return {"ok": self.ok, "reason": self.reason, "payload": self.payload}


def _check_expiry(payload: dict) -> bool:
    exp = payload.get("expires") or ""
    if not exp:
        return True
    try:
        return date.today() <= date.fromisoformat(exp)
    except ValueError:
        return False


def verify_license(
    lic_text: str,
    pub,                      # Ed25519PublicKey
    local_hwid: str = "",
    revoked_ids: set = None,
    require_feature: str = "",
    anchor_path=None,         # 启发式防回拨状态文件路径（可选）
    bind_store: dict = None,  # 首激活绑定存储 {授权id: 设备码}（调用方持久化）
) -> VerifyResult:
    try:
        payload, sig = parse_license(lic_text)
    except Exception:
        return VerifyResult(False, VerifyResult.BAD_FORMAT)

    # 1) 签名（密码学核心防线）
    try:
        pub.verify(sig, canonical_payload(payload))
    except Exception:
        return VerifyResult(False, VerifyResult.BAD_SIGNATURE, payload)

    # 2) 有效期（含到期日当天）
    if not _check_expiry(payload):
        return VerifyResult(False, VerifyResult.EXPIRED, payload)

    # 3) 设备绑定（含首激活绑定：首次验证锁本机，防转卖）
    bound = payload.get("hwid") or ""
    if bound and local_hwid and bound != local_hwid.upper().strip():
        return VerifyResult(False, VerifyResult.HWID_MISMATCH, payload)
    if payload.get("bind") == "first" and bind_store is not None and local_hwid:
        _id = payload.get("id", "")
        mine = local_hwid.upper().strip()
        if _id in bind_store:
            if bind_store[_id] != mine:
                return VerifyResult(False, VerifyResult.HWID_MISMATCH, payload)
        else:
            bind_store[_id] = mine

    # 4) 吊销名单（离线模式下的尽力而为）
    if revoked_ids and payload.get("id") in revoked_ids:
        return VerifyResult(False, VerifyResult.REVOKED, payload)

    # 5) 功能点
    if require_feature:
        feats = payload.get("features") or "*"
        if feats != "*":
            want = {f.strip() for f in feats.split(",")}
            if require_feature not in want:
                return VerifyResult(False, VerifyResult.FEATURE_MISSING, payload)

    # 6) 时钟回拨防护（启发式：本地记录上次成功验证时间）
    if anchor_path:
        import os
        try:
            now = time.time()
            if os.path.exists(anchor_path):
                last = float(open(anchor_path, "r", encoding="ascii").read().strip() or 0)
                if last > now + 86400:      # 未来时间锚点 = 系统时间被回拨
                    return VerifyResult(False, VerifyResult.CLOCK_ROLLBACK, payload)
            open(anchor_path, "w", encoding="ascii").write(str(now))
        except Exception:
            pass

    return VerifyResult(True, VerifyResult.OK, payload)
