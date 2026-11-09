# -*- coding: utf-8 -*-
"""卡密（零售单位）生成：人类可读、可电话报读
KM-XXXX-XXXX-XXXX-XXXX（16位，去掉易混淆的 I/L/O/U）
"""
import secrets

ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"  # 30字符，无歧义


def card_key() -> str:
    groups = ["".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(4)]
    return "KM-" + "-".join(groups)
