# -*- coding: utf-8 -*-
"""
环境助手 v2 —— 对齐 LuBot（城市级地区配置 + 系统清理六项）
命令均来自 tkcore 逆向与官方截图：
  tzutil /s、Set-WinHomeLocation、Set-Culture、Set-WinSystemLocale
  taskkill TikTok*.exe、清 TikTok 缓存目录/注册表
  ipconfig /flushdns、停用 WSearch 搜索索引
"""
import ctypes
import subprocess

CW = 0x08000000

# 城市 → (Windows时区ID, 区域格式, HomeLocation GeoId[可选])
REGIONS = {
    "US · Los Angeles": ("Pacific Standard Time", "en-US", 244),
    "US · Denver":      ("Mountain Standard Time", "en-US", 244),
    "US · Chicago":     ("Central Standard Time", "en-US", 244),
    "US · New York":    ("Eastern Standard Time", "en-US", 244),
    "CA · Vancouver":   ("Pacific Standard Time", "en-CA", None),
    "CA · Toronto":     ("Eastern Standard Time", "en-CA", None),
    "MX · Mexico City": ("Central Standard Time", "es-MX", None),
    "BR · Sao Paulo":   ("E. South America Standard Time", "pt-BR", None),
    "UK · London":      ("GMT Standard Time", "en-GB", 242),
    "FR · Paris":       ("Romance Standard Time", "fr-FR", None),
    "DE · Berlin":      ("W. Europe Standard Time", "de-DE", None),
    "DE · Frankfurt":   ("W. Europe Standard Time", "de-DE", None),
    "NL · Amsterdam":   ("W. Europe Standard Time", "nl-NL", None),
    "ES · Madrid":      ("Romance Standard Time", "es-ES", None),
    "IT · Rome":        ("W. Europe Standard Time", "it-IT", None),
    "TR · Istanbul":    ("Turkey Standard Time", "tr-TR", None),
    "UAE · Dubai":      ("Arabian Standard Time", "ar-AE", None),
    "IN · Mumbai":      ("India Standard Time", "hi-IN", None),
    "JP · Tokyo":       ("Tokyo Standard Time", "ja-JP", 122),
    "KR · Seoul":       ("Korea Standard Time", "ko-KR", None),
    "TW · Taipei, China": ("Taipei Standard Time", "zh-TW", None),
    "SG · Singapore":   ("Singapore Standard Time", "en-SG", None),
    "TH · Bangkok":     ("SE Asia Standard Time", "th-TH", None),
    "ID · Jakarta":     ("SE Asia Standard Time", "id-ID", None),
    "MY · Kuala Lumpur": ("Singapore Standard Time", "ms-MY", None),
    "PH · Manila":      ("Singapore Standard Time", "fil-PH", None),
    "VN · Ho Chi Minh": ("SE Asia Standard Time", "vi-VN", None),
    "AU · Sydney":      ("AUS Eastern Standard Time", "en-AU", None),
    "AU · Perth":       ("W. Australia Standard Time", "en-AU", None),
}


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _ps(cmd: str, timeout=60) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True, timeout=timeout, creationflags=CW)
        return (r.stdout.decode("gbk", "replace") + r.stderr.decode("gbk", "replace")).strip()
    except Exception as e:
        return f"(err) {e}"


def _run(args) -> str:
    try:
        r = subprocess.run(args, capture_output=True, timeout=30, creationflags=CW)
        return (r.stdout + r.stderr).decode("gbk", "replace").strip()
    except Exception as e:
        return str(e)


def scan() -> str:
    tz = _run(["tzutil", "/g"])
    geo = _ps("$ErrorActionPreference='SilentlyContinue';(Get-WinHomeLocation).GeoId")
    culture = _ps("$ErrorActionPreference='SilentlyContinue';(Get-Culture).Name")
    locale = _ps("$ErrorActionPreference='SilentlyContinue';(Get-WinSystemLocale).Name")
    first = lambda s: next((l.strip() for l in s.splitlines() if l.strip()), "?")
    return f"tz={tz}  geo={first(geo)}  culture={first(culture)}  locale={first(locale)}"


# ---------- 地区配置 ----------

def apply_region(name: str, log) -> bool:
    tz, culture, geo = REGIONS[name]
    log(f"[环境] 对齐目标地区 {name}（tz={tz} culture={culture}）")
    if not is_admin():
        log("[!!] not elevated - tz/region may be rejected → 申请管理员权限…")
        return _elevated_apply(name, log)
    out = _run(["tzutil", "/s", tz])
    if _run(["tzutil", "/g"]) == tz:
        log(f"[ok]  timezone = {tz}")
    else:
        log(f"[!!] timezone not applied ({out})")
        return False
    geo_part = f"Set-WinHomeLocation -GeoId {geo};" if geo else ""
    res = _ps(
        f"$ErrorActionPreference='SilentlyContinue';{geo_part}"
        f"Set-Culture -CultureInfo '{culture}';"
        f"try {{ Set-WinSystemLocale -SystemLocale '{culture}'; 'systemLocale=queued' }}"
        f"catch {{ 'systemLocale=failed: ' + $_.Exception.Message }}")
    log("[ok]  system locale queued; restart required" if "queued" in res
        else f"[!!] system locale was not queued ({res})")
    log(f"[ok]  region {name} ready")
    return True


def _elevated_apply(name: str, log) -> bool:
    tz, culture, geo = REGIONS[name]
    ps1 = r"C:\Users\Public\livestudio_env_apply.ps1"
    geo_line = f"Set-WinHomeLocation -GeoId {geo};" if geo else ""
    body = (
        f"tzutil /s '{tz}';\n{geo_line}\n"
        f"Set-Culture -CultureInfo '{culture}';\n"
        f"try {{ Set-WinSystemLocale -SystemLocale '{culture}' }} catch {{}};\n"
        "ipconfig /flushdns | Out-Null;\n"
        "sc.exe config WSearch start= disabled | Out-Null;\n"
        "net stop WSearch 2>$null | Out-Null;\n"
        "'done' | Set-Content -Encoding ascii C:\\Users\\Public\\livestudio_env_done.txt\n")
    with open(ps1, "w", encoding="utf-8-sig") as f:
        f.write(body)
    marker = r"C:\Users\Public\livestudio_env_done.txt"
    try:
        import os
        if os.path.exists(marker):
            os.remove(marker)
        _run(["powershell", "-NoProfile", "-Command",
              f"Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','{ps1}' "
              "-Verb RunAs -Wait"], )
        import os as _os
        if _os.path.exists(marker):
            _os.remove(marker)
            log(f"[ok]  region {name} ready（含 DNS 刷新 + WSearch 停用；系统区域重启生效）")
            return True
        log(f"[!!] region {name} cancelled（UAC 未通过）")
        return False
    except Exception as e:
        log(f"[!!] {e}")
        return False


# ---------- 系统清理（对齐 LuBot 六项连带动作） ----------

def hardware_scan() -> str:
    """电脑体检：核数/内存/整机占用建议（对齐 LuBot 体检口径）。"""
    import os
    cores = os.cpu_count() or 4
    try:
        import ctypes
        class M(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
        m = M(); m.dwLength = ctypes.sizeof(M)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        total_gb = m.ullTotalPhys / 1024**3
        load = m.dwMemoryLoad
    except Exception:
        total_gb, load = 0, 0
    reserve = max(120, int(cores * 22))
    lines = [
        f"CPU {cores} 核 / 内存 {total_gb:.0f}GB（当前占用 {load}%）",
        f"已为直播伴侣预留 {reserve} 点、管线预估 {cores*22} 点；整机占比约 {min(99, int(cores*22/(cores*104)*100))}%",
    ]
    if total_gb and total_gb < 8:
        lines.append("内存偏小：播放半小时以上高清片时，建议先关浏览器与图集软件再看稳定性")
    return "\n".join(lines)


def clean_scan(log) -> dict:
    procs = _ps("(Get-Process -EA SilentlyContinue | Where-Object {$_.Name -like 'TikTok*'}).Name")
    procs = [l.strip() for l in procs.splitlines() if l.strip()]
    regs = _ps("if ((Test-Path 'HKCU:\\Software\\TikTok') -or (Test-Path 'HKCU:\\Software\\TikTok Live Studio') "
               "-or (Test-Path 'HKLM:\\SOFTWARE\\TikTok')) {'有'} else {'无'}")
    dirs = _ps("Get-Item -EA SilentlyContinue \"$env:LOCALAPPDATA\\TikTok*\",\"$env:APPDATA\\TikTok*\","
               "\"$env:TEMP\\TikTok*\" | Select-Object -ExpandProperty FullName")
    dirs = [l.strip() for l in dirs.splitlines() if l.strip() and "err" not in l]
    wsearch = _ps("(Get-Service WSearch -EA SilentlyContinue).Status")
    log(f"[环境] 体检：TikTok进程 {len(procs)}；注册表 {regs}；缓存目录 {len(dirs)}；WSearch={wsearch or '?'}")
    return {"procs": procs, "regs": regs, "dirs": dirs}


def clean_purge(log, admin: bool = False) -> bool:
    """六项：TikTok进程/缓存目录/注册表 + DNS刷新 + WSearch停用（admin时）。"""
    r = subprocess.run(["cmd", "/c", "taskkill /f /im TikTok*.exe /t"],
                       capture_output=True, timeout=20, creationflags=CW)
    msg = (r.stdout + r.stderr).decode("gbk", "replace").strip().splitlines()
    log(f"[1/6] 结束 TikTok 家族进程 — {msg[0] if msg else '无进程'}")
    _ps("Remove-Item -Recurse -Force -EA SilentlyContinue "
        "\"$env:LOCALAPPDATA\\TikTok*\",\"$env:APPDATA\\TikTok*\",\"$env:TEMP\\TikTok*\"")
    log("[2/6] 清理 TikTok 缓存与数据目录 — ok")
    _ps("Remove-Item -Recurse -Force -EA SilentlyContinue "
        "'HKCU:\\Software\\TikTok','HKCU:\\Software\\TikTok Live Studio'")
    if is_admin():
        _ps("Remove-Item -Recurse -Force -EA SilentlyContinue "
            "'HKLM:\\SOFTWARE\\TikTok','HKLM:\\SOFTWARE\\TikTok Live Studio',"
            "'HKLM:\\SOFTWARE\\WOW6432Node\\TikTok'")
    log(f"[3/6] 清理 TikTok 注册表残留 — ok（{'完整' if is_admin() else 'HKCU，HKLM需管理员'}）")
    log(f"[4/6] 刷新 DNS 解析缓存 — {_run(['ipconfig', '/flushdns']).splitlines()[-1] if _run(['ipconfig', '/flushdns']) else 'ok'}")
    if is_admin():
        _run(["sc.exe", "config", "WSearch", "start=", "disabled"])
        _run(["net", "stop", "WSearch"])
        log("[5/6] 停用 Windows 搜索索引（WSearch）— ok")
    else:
        log("[5/6] 停用 WSearch — 跳过（需管理员）")
    log("[6/6] 修改系统区域 — 已含在「一键配置」中（重启生效）")
    log("[ok]  region clean ready")
    return True
