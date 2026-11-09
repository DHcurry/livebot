# -*- coding: utf-8 -*-
"""
卡密系统管理面板（签发方用）
- 零依赖（Python 标准库）+ cryptography（签发）
- 只监听 127.0.0.1，默认不对局域网暴露
- 启动: python panel/server.py  或双击 启动面板.bat
- 可选环境变量: KMS_PORT(默认8777) KMS_TOKEN(设置后所有API需带 ?token=)
"""
import csv
import io
import json
import os
import sqlite3
import sys
import threading
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import keys, license as lic, cardkey, fingerprint  # noqa: E402

DATA = ROOT / "data"
DB = DATA / "licenses.db"
REVOCATIONS = DATA / "revocations.txt"
PORT = int(os.environ.get("KMS_PORT", "8777"))
TOKEN = os.environ.get("KMS_TOKEN", "")
HOST = os.environ.get("KMS_HOST", "127.0.0.1")

_db_lock = threading.Lock()


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DATA.mkdir(exist_ok=True)
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS licenses(
            id TEXT PRIMARY KEY, customer TEXT, hwid TEXT, expires TEXT,
            features TEXT, product TEXT, notes TEXT, cardkey TEXT,
            created TEXT, revoked INTEGER DEFAULT 0, lic_text TEXT)""")


def revoked_ids():
    if not REVOCATIONS.exists():
        return set()
    return {l.strip() for l in REVOCATIONS.read_text(encoding="utf-8").splitlines() if l.strip()}


def stats():
    with db() as c:
        total = c.execute("SELECT COUNT(*) n FROM licenses").fetchone()["n"]
        rev = c.execute("SELECT COUNT(*) n FROM licenses WHERE revoked=1").fetchone()["n"]
        today = date.today().isoformat()
        exp = c.execute(
            "SELECT COUNT(*) n FROM licenses WHERE expires!='' AND expires<?", (today,)
        ).fetchone()["n"]
    return {"total": total, "active": total - rev - exp, "revoked": rev, "expired": exp,
            "key_ready": keys.key_exists(DATA)}


class H(BaseHTTPRequestHandler):
    server_version = "KMS/1.0"

    def log_message(self, fmt, *args):
        pass

    # ---------- 基础 ----------
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _authed(self, query):
        if not TOKEN:
            return True
        return query.get("token", [""])[0] == TOKEN

    # ---------- 路由 ----------
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        path = u.path

        if path in ("/", "/index.html"):
            html = (Path(__file__).parent / "index.html").read_bytes()
            return self._send(200, html, "text/html; charset=utf-8")

        if path.startswith("/api/") and path != "/api/redeem" and not self._authed(q):
            return self._send(401, {"error": "token 错误"})

        if path == "/api/stats":
            return self._send(200, stats())
        if path == "/api/pubkey":
            if not keys.key_exists(DATA):
                return self._send(400, {"error": "未初始化"})
            return self._send(200, {"pubkey": (DATA / "public.hex").read_text().strip()})
        if path == "/api/device":
            return self._send(200, {"device": fingerprint.device_code(),
                                    "signals": fingerprint.collect()})
        if path == "/api/licenses":
            kw = (q.get("q", [""])[0]).strip()
            with db() as c:
                if kw:
                    rows = c.execute(
                        "SELECT id,customer,hwid,expires,features,notes,cardkey,created,revoked "
                        "FROM licenses WHERE customer LIKE ? OR id LIKE ? OR cardkey LIKE ? "
                        "ORDER BY created DESC LIMIT 200",
                        (f"%{kw}%", f"%{kw}%", f"%{kw}%")).fetchall()
                else:
                    rows = c.execute(
                        "SELECT id,customer,hwid,expires,features,notes,cardkey,created,revoked "
                        "FROM licenses ORDER BY created DESC LIMIT 200").fetchall()
            return self._send(200, [dict(r) for r in rows])
        if path.startswith("/api/lic/"):
            lid = path[len("/api/lic/"):]
            with db() as c:
                row = c.execute("SELECT lic_text FROM licenses WHERE id=?", (lid,)).fetchone()
            if not row:
                return self._send(404, {"error": "不存在"})
            body = row["lic_text"].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition",
                             f"attachment; filename*=UTF-8''{quote(lid)}.lic")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/revocations.txt":
            body = (REVOCATIONS.read_text(encoding="utf-8") if REVOCATIONS.exists() else "")
            return self._send(200, body.encode("utf-8"), "text/plain; charset=utf-8")
        if path == "/api/export.csv":
            with db() as c:
                rows = c.execute("SELECT cardkey,id,customer,hwid,expires,features,created,revoked "
                                 "FROM licenses ORDER BY created").fetchall()
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["卡密", "授权ID", "客户", "设备码", "有效期", "功能", "签发日", "已吊销"])
            for r in rows:
                w.writerow([r["cardkey"], r["id"], r["customer"], r["hwid"],
                            r["expires"] or "永久", r["features"], r["created"], r["revoked"]])
            return self._send(200, buf.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8")
        if path == "/api/redeem":
            k = (q.get("k", [""])[0]).strip().upper()
            with db() as c:
                row = c.execute("SELECT lic_text FROM licenses WHERE UPPER(cardkey)=?",
                                (k,)).fetchone()
            if row:
                return self._send(200, {"ok": True, "lic": row["lic_text"]})
            return self._send(404, {"error": "卡密不存在"})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if not self._authed(q):
            return self._send(401, {"error": "token 错误"})
        body = self._json_body()

        if u.path == "/api/init":
            if keys.key_exists(DATA):
                return self._send(400, {"error": "密钥已存在（轮换会作废全部旧授权）"})
            _, pub = keys.generate_keypair(DATA)
            return self._send(200, {"pubkey": pub, "hint": "记得运行 embed 或分发公钥"})

        if not keys.key_exists(DATA):
            return self._send(400, {"error": "请先初始化密钥对"})
        priv = keys.load_private(DATA)

        if u.path == "/api/issue":
            customer = (body.get("customer") or "").strip()
            if not customer:
                return self._send(400, {"error": "客户名必填"})
            hwid = "" if body.get("any_device") else (body.get("hwid") or "").strip()
            expires = "" if body.get("permanent") else (body.get("expires") or "").strip()
            if not body.get("permanent") and not expires:
                return self._send(400, {"error": "请选择有效期或永久"})
            payload = lic.make_payload(
                customer=customer, hwid=hwid, expires=expires,
                features=(body.get("features") or "*").strip(),
                product=(body.get("product") or "any").strip(),
                notes=(body.get("notes") or "").strip(),
                bind_first=bool(body.get("bind_first")),
            )
            text = lic.sign_license(payload, priv)
            ck = cardkey.card_key()
            with _db_lock, db() as c:
                c.execute("INSERT INTO licenses VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                          (payload["id"], customer, hwid, expires, payload["features"],
                           payload["product"], payload["notes"], ck,
                           date.today().isoformat(), 0, text))
            return self._send(200, {"id": payload["id"], "cardkey": ck, "lic": text})

        if u.path == "/api/batch":
            customer = (body.get("customer") or "").strip() or "批量客户"
            count = max(1, min(500, int(body.get("count") or 10)))
            expires = "" if body.get("permanent") else (body.get("expires") or "").strip()
            if not body.get("permanent") and not expires:
                return self._send(400, {"error": "请选择有效期或永久"})
            items = []
            with _db_lock, db() as c:
                for _ in range(count):
                    payload = lic.make_payload(
                        customer=customer, hwid="", expires=expires,
                        features=(body.get("features") or "*").strip(),
                        product=(body.get("product") or "any").strip(),
                        notes=(body.get("notes") or "").strip(),
                    )
                    text = lic.sign_license(payload, priv)
                    ck = cardkey.card_key()
                    c.execute("INSERT INTO licenses VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                              (payload["id"], customer, "", expires, payload["features"],
                               payload["product"], payload["notes"], ck,
                               date.today().isoformat(), 0, text))
                    items.append({"cardkey": ck, "id": payload["id"], "lic": text})
            return self._send(200, {"count": count, "items": items})

        if u.path in ("/api/revoke", "/api/unrevoke"):
            lid = (body.get("id") or "").strip()
            flag = 1 if u.path.endswith("revoke") and u.path.endswith("/api/revoke") else 0
            with _db_lock, db() as c:
                c.execute("UPDATE licenses SET revoked=? WHERE id=?", (flag, lid))
            # 同步吊销名单文件（离线验证用）
            ids = revoked_ids()
            if flag:
                ids.add(lid)
            else:
                ids.discard(lid)
            REVOCATIONS.write_text("\n".join(sorted(ids)) + ("\n" if ids else ""), encoding="utf-8")
            return self._send(200, {"ok": True, "revoked": bool(flag)})

        self._send(404, {"error": "not found"})


def main():
    init_db()
    srv = ThreadingHTTPServer((HOST, PORT), H)
    print(f"卡密管理面板: http://{HOST}:{PORT}")
    print(f"数据目录: {DATA}   私钥: {DATA / 'issuer.key'}（务必备份）")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
