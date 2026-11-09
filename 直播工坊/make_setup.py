# -*- coding: utf-8 -*-
"""生成双文件安装包：直播工坊-Setup.exe + LiveStudio.dat（同目录放一起）"""
import shutil
import zipfile
from pathlib import Path

PROJ = Path(r"C:\Users\16575\Desktop\直播工坊")
SRC = PROJ / "dist" / "LiveStudio"
CORE = PROJ / "dist_setup" / "SetupCore.exe"
OUT_DIR = Path(r"C:\Users\16575\Desktop\直播工坊-交付")
EXE_OUT = OUT_DIR / "直播工坊-Setup.exe"
DAT_OUT = OUT_DIR / "LiveStudio.dat"
MAGIC = b"LSSETUP1"

def main():
    payload = PROJ / "build_setup" / "payload.zip"
    print("打包载荷(STORE)…")
    with zipfile.ZipFile(payload, "w", zipfile.ZIP_STORED) as z:
        for f in sorted(SRC.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(SRC).as_posix())
    psz = payload.stat().st_size
    print(f"载荷 {psz/1024/1024:.0f} MB → LiveStudio.dat")
    shutil.copyfile(CORE, EXE_OUT)
    with open(payload, "rb") as p, open(DAT_OUT, "wb") as o:
        shutil.copyfileobj(p, o, 1 << 22)
        o.write(psz.to_bytes(8, "big"))
        o.write(MAGIC)
    payload.unlink()
    print(f"完成: {EXE_OUT.name} ({EXE_OUT.stat().st_size//1024//1024}MB) + "
          f"{DAT_OUT.name} ({DAT_OUT.stat().st_size//1024//1024}MB)")

if __name__ == "__main__":
    main()
