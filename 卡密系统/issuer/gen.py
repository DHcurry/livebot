# -*- coding: utf-8 -*-
"""
签发方命令行工具
用法示例：
  python issuer\gen.py init                     生成密钥对（首次）
  python issuer\gen.py device                   显示本机设备码
  python issuer\gen.py issue --customer 张三 --hwid 3F2A-9C14 --expires 2027-10-22 --out 张三.lic
  python issuer\gen.py issue --customer 张三 --permanent --any-device --out 张三任意设备.lic
  python issuer\gen.py batch --customer 渠道A --count 10 --expires 2027-12-31 --csv batch.csv
  python issuer\gen.py verify 张三.lic [--hwid 本机码]
  python issuer\gen.py revoke --id <授权ID>      加入吊销名单
  python issuer\gen.py unrevoke --id <授权ID>
  python issuer\gen.py embed                    把公钥写入 client\verify.py
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import keys, license as lic, cardkey  # noqa: E402

DATA = ROOT / "data"
REVOCATIONS = DATA / "revocations.txt"
CLIENT_VERIFY = ROOT / "client" / "verify.py"


def cmd_init(_args):
    if keys.key_exists(DATA):
        print("密钥已存在，如需轮换请先删除 data\\issuer.key（旧授权将全部失效！）")
        return 1
    priv, pub_hex = keys.generate_keypair(DATA)
    print("密钥对已生成：")
    print(f"  私钥: {DATA / 'issuer.key'}   ← 备份它！丢了=所有授权作废")
    print(f"  公钥: {pub_hex}")
    print("下一步：python issuer\\gen.py embed   （把公钥嵌入客户端验证器）")
    return 0


def cmd_device(_args):
    from core import fingerprint
    print("采集到的原始信号：")
    for k, v in fingerprint.collect().items():
        print(f"  {k:14} = {v}")
    print(f"\n设备码: {fingerprint.device_code()}")
    return 0


def _load_priv():
    return keys.load_private(DATA)


def cmd_issue(args):
    priv = _load_priv()
    hwid = "" if args.any_device else (args.hwid or "").strip()
    if not args.any_device and not hwid:
        # 未给 hwid 也未声明 any-device → 默认绑定本机（防误发不绑定授权）
        from core import fingerprint
        hwid = fingerprint.device_code()
        print(f"[提示] 未指定 --hwid，已自动绑定本机: {hwid}")
    expires = "" if args.permanent else (args.expires or "")
    if not args.permanent and not expires:
        print("[错误] 请指定 --expires YYYY-MM-DD 或 --permanent")
        return 2
    payload = lic.make_payload(
        customer=args.customer, hwid=hwid, expires=expires,
        features=args.features, product=args.product, notes=args.notes,
        bind_first=getattr(args, "bind_first", False),
    )
    text = lic.sign_license(payload, priv)
    out = Path(args.out) if args.out else Path(f"{args.customer}_授权.lic")
    out.write_text(text, encoding="utf-8")
    print(f"已签发: {out}")
    print(f"  授权ID : {payload['id']}")
    print(f"  客户   : {payload['customer']}")
    print(f"  设备   : {hwid or '不限设备'}")
    print(f"  有效期 : {expires or '永久'}")
    print(f"\n激活码（发给客户，激活时整段粘贴）：\n{text}")
    return 0


def cmd_batch(args):
    priv = _load_priv()
    rows = []
    for i in range(args.count):
        payload = lic.make_payload(
            customer=args.customer, hwid="",
            expires="" if args.permanent else args.expires,
            features=args.features, product=args.product,
            notes=args.notes,
        )
        text = lic.sign_license(payload, priv)
        rows.append({
            "卡密": cardkey.card_key(),
            "授权ID": payload["id"],
            "客户": args.customer,
            "有效期": payload["expires"] or "永久",
            "激活码": text,
        })
    out = Path(args.csv) if args.csv else Path(f"batch_{args.customer}.csv")
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"已生成 {args.count} 张 → {out}")
    print("卡密用于你的销售记账；激活码发给客户粘贴使用。")
    return 0


def cmd_verify(args):
    pub = keys.load_public_from_hex((DATA / "public.hex").read_text())
    revoked = set()
    if REVOCATIONS.exists():
        revoked = {l.strip() for l in REVOCATIONS.read_text(encoding="utf-8").splitlines() if l.strip()}
    text = Path(args.lic).read_text(encoding="utf-8") if Path(args.lic).exists() else args.lic
    res = lic.verify_license(text, pub, local_hwid=args.hwid or "", revoked_ids=revoked)
    print(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
    return 0 if res.ok else 1


def cmd_revoke(args):
    DATA.mkdir(exist_ok=True)
    lines = set()
    if REVOCATIONS.exists():
        lines = {l.strip() for l in REVOCATIONS.read_text(encoding="utf-8").splitlines() if l.strip()}
    lines.add(args.id.strip())
    REVOCATIONS.write_text("\n".join(sorted(lines)) + "\n", encoding="utf-8")
    print(f"已吊销 {args.id}（离线模式下需随应用更新分发 revocations.txt 才能生效）")
    return 0


def cmd_unrevoke(args):
    if not REVOCATIONS.exists():
        print("吊销名单不存在")
        return 1
    lines = {l.strip() for l in REVOCATIONS.read_text(encoding="utf-8").splitlines() if l.strip()}
    lines.discard(args.id.strip())
    REVOCATIONS.write_text("\n".join(sorted(lines)) + ("\n" if lines else ""), encoding="utf-8")
    print(f"已解除吊销 {args.id}")
    return 0


def cmd_embed(_args):
    if not (DATA / "public.hex").exists():
        print("先执行 init")
        return 1
    pub_hex = (DATA / "public.hex").read_text().strip()
    src = CLIENT_VERIFY.read_text(encoding="utf-8")
    import re
    new = re.sub(r'EMBEDDED_PUBKEY = "[0-9A-F]*"',
                 f'EMBEDDED_PUBKEY = "{pub_hex}"', src)
    if new == src and f'"{pub_hex}"' not in src:
        print("警告：未找到占位符 EMBEDDED_PUBKEY，请检查 verify.py")
        return 1
    CLIENT_VERIFY.write_text(new, encoding="utf-8")
    print(f"公钥已嵌入 {CLIENT_VERIFY}")
    print("现在 client\\verify.py 是完全独立的验证器，可随你的产品分发。")
    return 0


def main():
    p = argparse.ArgumentParser(description="卡密系统签发工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(fn=cmd_init)
    sub.add_parser("device").set_defaults(fn=cmd_device)
    sub.add_parser("embed").set_defaults(fn=cmd_embed)

    pi = sub.add_parser("issue")
    pi.add_argument("--customer", required=True)
    pi.add_argument("--hwid", default="")
    pi.add_argument("--any-device", action="store_true")
    pi.add_argument("--bind-first", action="store_true",
                    help="首激活绑定：第一次验证时锁定设备，防转卖")
    pi.add_argument("--expires", default="")
    pi.add_argument("--permanent", action="store_true")
    pi.add_argument("--features", default="*")
    pi.add_argument("--product", default="any")
    pi.add_argument("--notes", default="")
    pi.add_argument("--out", default="")
    pi.set_defaults(fn=cmd_issue)

    pb = sub.add_parser("batch")
    pb.add_argument("--customer", required=True)
    pb.add_argument("--count", type=int, default=10)
    pb.add_argument("--expires", default="")
    pb.add_argument("--permanent", action="store_true")
    pb.add_argument("--features", default="*")
    pb.add_argument("--product", default="any")
    pb.add_argument("--notes", default="")
    pb.add_argument("--csv", default="")
    pb.set_defaults(fn=cmd_batch)

    pv = sub.add_parser("verify")
    pv.add_argument("lic")
    pv.add_argument("--hwid", default="")
    pv.set_defaults(fn=cmd_verify)

    pr = sub.add_parser("revoke"); pr.add_argument("--id", required=True); pr.set_defaults(fn=cmd_revoke)
    pu = sub.add_parser("unrevoke"); pu.add_argument("--id", required=True); pu.set_defaults(fn=cmd_unrevoke)

    args = p.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
