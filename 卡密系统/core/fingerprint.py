# -*- coding: utf-8 -*-
"""
设备指纹采集（Windows 优先）
信号源：注册表 MachineGuid + CPU ProcessorId + 网卡 MAC
输出格式：XXXXXXXX-XXXXXXXX（16位十六进制，与常见设备码风格一致）
"""
import hashlib
import subprocess
import uuid

CREATE_NO_WINDOW = 0x08000000


def _machine_guid() -> str:
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(val).strip()
    except Exception:
        return "no-machine-guid"


def _processor_id() -> str:
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor | Select-Object -First 1).ProcessorId"],
            capture_output=True, text=True, timeout=15,
            creationflags=CREATE_NO_WINDOW,
        )
        val = (out.stdout or "").strip()
        if val:
            return val
    except Exception:
        pass
    return "no-processor-id"


def _mac() -> str:
    try:
        return f"{uuid.getnode():012X}"
    except Exception:
        return "no-mac"


def collect() -> dict:
    """采集原始信号（调试用）。"""
    return {
        "machine_guid": _machine_guid(),
        "processor_id": _processor_id(),
        "mac": _mac(),
    }


def device_code() -> str:
    """稳定设备码：三信号混合 → blake2b-64 → 16 hex 分组。"""
    raw = "|".join([
        _machine_guid().lower(),
        _processor_id().lower(),
        _mac(),
    ])
    digest = hashlib.blake2b(raw.encode("utf-8"), digest_size=8).hexdigest().upper()
    return f"{digest[:8]}-{digest[8:]}"


if __name__ == "__main__":
    print(device_code())
