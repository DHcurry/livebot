# -*- coding: utf-8 -*-
"""装配交付物：runtime 组件 + 授权 + 安装/卸载脚本 → dist\\LiveStudio"""
import shutil
import sys
from pathlib import Path

SRC_TOOLS = Path(r"C:\Users\16575\Desktop\TK奥德彪直播工具")
FF = SRC_TOOLS / "FFmpeg完整版含MTX" / "ffmpeg-9.0.2-full_build" / "bin" / "ffmpeg.exe"
MTX = SRC_TOOLS / "FFmpeg完整版含MTX" / "Mediamtx" / "mediamtx.exe"
MTX_YML = SRC_TOOLS / "FFmpeg完整版含MTX" / "Mediamtx" / "mediamtx.yml"
PROJ = Path(r"C:\Users\16575\Desktop\直播工坊")
DIST = PROJ / "dist" / "LiveStudio"
RT = DIST / "runtime"

def main():
    assert (DIST / "LiveStudio.exe").exists(), "LiveStudio.exe 不存在，先跑 PyInstaller"
    RT.mkdir(exist_ok=True)
    print("拷贝 ffmpeg.exe …");  shutil.copy2(FF, RT / "ffmpeg.exe")
    print("拷贝 mediamtx.exe …"); shutil.copy2(MTX, RT / "mediamtx.exe")
    print("拷贝 mediamtx.yml …"); shutil.copy2(MTX_YML, RT / "mediamtx.yml")
    lic = PROJ / "我的授权.lic"
    if lic.exists():
        shutil.copy2(lic, DIST / "我的授权.lic")
        print("预置授权: 我的授权.lic")

    # 内置虚拟摄像头驱动（UnityCapture, MIT）
    drv_src = PROJ / "driver"
    drv_dst = DIST / "driver"
    if drv_src.exists():
        drv_dst.mkdir(exist_ok=True)
        for p in drv_src.iterdir():
            if p.is_file():
                shutil.copy2(p, drv_dst / p.name)
        print("内置虚拟摄像头驱动:", [p.name for p in drv_dst.iterdir()])

    ps1 = ("$dst = $args[0]\r\n"
           "$w = New-Object -ComObject WScript.Shell\r\n"
           "$s = $w.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\直播工坊.lnk')\r\n"
           "$s.TargetPath = Join-Path $dst 'LiveStudio.exe'\r\n"
           "$s.WorkingDirectory = $dst\r\n"
           "$s.Save()\r\n"
           "$s2 = $w.CreateShortcut([Environment]::GetFolderPath('Programs') + '\\直播工坊.lnk')\r\n"
           "$s2.TargetPath = Join-Path $dst 'LiveStudio.exe'\r\n"
           "$s2.WorkingDirectory = $dst\r\n"
           "$s2.Save()\r\n")
    (DIST / "make_shortcuts.ps1").write_text(ps1, encoding="utf-8-sig")

    (DIST / "安装.bat").write_bytes(
        "@echo off\r\n"
        "set SRC=%~dp0\r\n"
        "set DST=%LOCALAPPDATA%\\Programs\\LiveStudio\r\n"
        "echo.\r\n"
        "echo   直播工坊 LiveStudio 安装\r\n"
        "echo   =========================\r\n"
        "if not exist \"%DST%\" mkdir \"%DST%\"\r\n"
        "xcopy /E /Y /Q \"%SRC%*\" \"%DST%\\\" >nul\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0make_shortcuts.ps1\" \"%DST%\"\r\n"
        "echo   完成！已创建桌面快捷方式「直播工坊」。\r\n"
        "echo.\r\n"
        "start \"\" \"%DST%\\LiveStudio.exe\"\r\n"
        "pause\r\n".encode("gbk"))

    (DIST / "卸载.bat").write_bytes(
        "@echo off\r\n"
        "taskkill /f /im LiveStudio.exe >nul 2>&1\r\n"
        "del \"%USERPROFILE%\\Desktop\\直播工坊.lnk\" >nul 2>&1\r\n"
        "powershell -NoProfile -Command \""
        "$p=[Environment]::GetFolderPath('Programs')+'\\直播工坊.lnk';"
        "if(Test-Path $p){Remove-Item $p}\"\r\n"
        "rmdir /s /q \"%LOCALAPPDATA%\\Programs\\LiveStudio\" >nul 2>&1\r\n"
        "echo 已卸载（用户配置与授权保留在 %LOCALAPPDATA%\\LiveStudio）。\r\n"
        "pause\r\n".encode("gbk"))

    (DIST / "使用说明.txt").write_text(
        "直播工坊 LiveStudio v1.2\n"
        "========================\n\n"
        "【使用】\n"
        "  双击 LiveStudio.exe（或安装.bat 装好后用桌面快捷方式）。\n"
        "  首次运行自动导入随包授权；如未激活，点顶栏「🔑 激活」粘贴激活码。\n\n"
        "【日常开播】\n"
        "  1. 左侧素材库添加视频（或点「扫描目录」读取 E:\\jianhaodesucai）\n"
        "  2. 可选：📷 画面叠加 → 扫描设备 → 选摄像头 → 勾「启用」\n"
        "  3. 点「🔴 开始推流」→ 智能处理 14 项自动逐项点亮\n"
        "  4. 直播伴侣/OBS 添加「媒体源」地址：rtmp://127.0.0.1:1935/tklive\n"
        "     （或 VLC 播放 http://127.0.0.1:8888/tklive/index.m3u8）\n\n"
        "【换激活码】\n"
        "  顶栏「🔑 激活」→ 粘贴新码点「更换激活码」，或先「清除授权」再激活。\n\n"
        "【卸载】\n"
        "  双击 卸载.bat。\n\n"
        "【说明】\n"
        "  本软件自带全部运行环境（Python/加密库/ffmpeg/MediaMTX），\n"
        "  无需安装任何其他软件。Windows 10/11 64位。\n",
        encoding="utf-8")
    print("装配完成:", DIST)
    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"总大小: {total/1024/1024:.0f} MB")

if __name__ == "__main__":
    sys.exit(main())
