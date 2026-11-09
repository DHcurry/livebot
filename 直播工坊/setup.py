# -*- coding: utf-8 -*-
"""
直播工坊 安装向导（自研，替代 Inno Setup）
- 单文件：exe 尾部内嵌整包数据（安装时从自身读取）
- 向导界面：欢迎/选目录/进度/完成；写控制面板卸载项；桌面+开始菜单快捷方式
- 旗标：--uninstall 卸载；--silent --dir X 静默安装（测试/批量）
"""
import io
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000
MAGIC = b"LSSETUP1"
APPNAME = "直播工坊"
EXENAME = "LiveStudio.exe"
UNINST_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\LiveStudio"


def _payload():
    # 方式A：自身尾部（兼容旧单文件）；方式B：同目录 LiveStudio.dat（主方案，避让 PyInstaller cookie）
    cands = []
    if sys.argv and sys.argv[0]:
        cands.append(Path(sys.argv[0]).resolve())
    cands.append(Path(sys.executable).resolve())
    own = None
    for c in cands:
        try:
            with open(c, "rb") as t:
                t.seek(-16, 2)
                if t.read(8) == MAGIC:
                    own = c
                    break
        except Exception:
            continue
    if own is not None:
        f = open(own, "rb")
        f.seek(-16, 2)
        size = int.from_bytes(f.read(8), "big")
        f.read(8)
        return f, own.stat().st_size - 16 - size, size
    # 同目录数据包
    dat = cands[0].parent / "LiveStudio.dat"
    if not dat.exists():
        raise RuntimeError("payload missing: LiveStudio.dat not found beside Setup.exe")
    f = open(dat, "rb")
    f.seek(-16, 2)
    size = int.from_bytes(f.read(8), "big")
    magic = f.read(8)
    if magic != MAGIC:
        raise RuntimeError("payload dat corrupt")
    return f, dat.stat().st_size - 16 - size, size


class _Region(io.RawIOBase):
    def __init__(self, f, base, size):
        self.f, self.base, self.size, self.pos = f, base, size, 0

    def seekable(self):
        return True

    def seek(self, off, whence=0):
        if whence == 0:
            self.pos = off
        elif whence == 1:
            self.pos += off
        else:
            self.pos = self.size + off
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        self.f.seek(self.base + self.pos)
        b = self.f.read(min(n, self.size - self.pos))
        self.pos += len(b)
        return b


def _ps(script: str):
    p = Path(os.environ["TEMP"]) / "ls_setup_tmp.ps1"
    p.write_text(script, encoding="utf-8-sig")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(p)],
                   capture_output=True, timeout=60, creationflags=CREATE_NO_WINDOW)


def _shortcuts(exe: str, desktop: bool):
    _ps(f"$w=New-Object -ComObject WScript.Shell\n"
        f"$s=$w.CreateShortcut([Environment]::GetFolderPath('Programs')+'\\直播工坊.lnk')\n"
        f"$s.TargetPath='{exe}';$s.Save()\n"
        + (f"$d=$w.CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\直播工坊.lnk')\n"
           f"$d.TargetPath='{exe}';$d.Save()\n" if desktop else ""))


def _del_shortcuts():
    _ps("foreach($p in @(([Environment]::GetFolderPath('Desktop')+'\\直播工坊.lnk'),"
        "([Environment]::GetFolderPath('Programs')+'\\直播工坊.lnk'))){if(Test-Path $p){Remove-Item $p}}")


def _install_dir() -> Path:
    import winreg
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            k = winreg.OpenKey(hive, UNINST_KEY)
            v, _ = winreg.QueryValueEx(k, "InstallLocation")
            return Path(v)
        except Exception:
            continue
    return Path(os.environ["LOCALAPPDATA"]) / "Programs" / "LiveStudio"


def _register_uninstall(dirp: Path, size_mb: int):
    import winreg
    k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINST_KEY)
    winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "直播工坊 LiveStudio")
    winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, "1.2")
    winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "LiveStudio")
    winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, str(dirp))
    winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ,
                      f'"{sys.executable}" --uninstall')
    winreg.SetValueEx(k, "DisplayIcon", 0, winreg.REG_SZ, str(dirp / EXENAME))
    winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, size_mb)
    winreg.CloseKey(k)


def _unregister():
    import winreg
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            winreg.DeleteKey(hive, UNINST_KEY)
        except Exception:
            pass


VCLSID = "{5c2cd55c-92ad-4999-8666-912bd3e70010}"
VCAT = "{860BB310-5D01-11d0-BD3B-00A0C911CE86}"
VCNAME = "LiveStudio Cam"


def register_vcam(dirp: Path):
    """用户级注册内置虚拟摄像头驱动（HKCU，免管理员）。"""
    import winreg
    dll = dirp / "driver" / "UnityCaptureFilter64.dll"
    if not dll.exists():
        return False
    base = r"Software\Classes\CLSID"
    def mk(p):
        return winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, base + "\\" + p, 0, winreg.KEY_WRITE)
    k = mk(VCLSID); winreg.SetValueEx(k, "", 0, winreg.REG_SZ, VCNAME); k.Close()
    k = mk(VCLSID + "\\InprocServer32")
    winreg.SetValueEx(k, "", 0, winreg.REG_SZ, str(dll))
    winreg.SetValueEx(k, "ThreadingModel", 0, winreg.REG_SZ, "Both"); k.Close()
    k = mk(VCLSID + "\\Instance"); winreg.SetValueEx(k, "", 0, winreg.REG_SZ, VCNAME); k.Close()
    k = mk(VCLSID + "\\Instance\\CLSID"); winreg.SetValueEx(k, "", 0, winreg.REG_SZ, VCLSID); k.Close()
    k = mk(VCAT + "\\Instance\\" + VCLSID)
    winreg.SetValueEx(k, "FriendlyName", 0, winreg.REG_SZ, VCNAME)
    winreg.SetValueEx(k, "CLSID", 0, winreg.REG_SZ, VCLSID); k.Close()
    return True


def unregister_vcam():
    import winreg
    for p in (VCLSID, VCAT + "\\Instance\\" + VCLSID):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\CLSID" + "\\" + p)
        except Exception:
            pass


def do_install(dst: Path, desktop: bool, progress=None, done=None):
    f, base, size = _payload()
    zf = zipfile.ZipFile(_Region(f, base, size))
    infos = zf.infolist()
    total = sum(i.file_size for i in infos) or 1
    dst.mkdir(parents=True, exist_ok=True)
    done_n = 0
    for i in infos:
        if i.is_dir():
            continue
        target = dst / i.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(i) as src, open(target, "wb") as out:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        done_n += i.file_size
        if progress:
            progress(done_n / total, i.filename)
    zf.close(); f.close()
    register_vcam(dst)
    _shortcuts(str(dst / EXENAME), desktop)
    _register_uninstall(dst, total // (1024 * 1024))
    if done:
        done()


def do_uninstall():
    d = _install_dir()
    subprocess.run(["taskkill", "/f", "/im", EXENAME],
                   capture_output=True, creationflags=CREATE_NO_WINDOW)
    _del_shortcuts()
    unregister_vcam()
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    _unregister()


def main():
    argv = sys.argv[1:]
    if "--uninstall" in argv:
        do_uninstall()
        return
    silent = "--silent" in argv
    dst = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "LiveStudio"
    if "--dir" in argv:
        dst = Path(argv[argv.index("--dir") + 1])

    if silent:
        do_install(dst, True)
        return

    # ---------- 向导 ----------
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.title("直播工坊 LiveStudio 安装向导")
    root.geometry("560x360")
    root.resizable(False, False)
    BG, CARD, GOLD, TXT, DIM = "#0F1115", "#171A21", "#D7A743", "#E7EAF0", "#8A93A6"
    root.configure(bg=BG)
    state = {"desktop": True}

    def screen_welcome():
        for w in root.winfo_children():
            w.destroy()
        tk.Label(root, text="▶ 直播工坊 LiveStudio v1.2", font=("Microsoft YaHei UI", 16, "bold"),
                 bg=BG, fg=GOLD).pack(pady=(28, 6))
        tk.Label(root, text="自有去重推流软件 · 全内置运行环境 · 免装任何依赖",
                 bg=BG, fg=DIM, font=("Microsoft YaHei UI", 10)).pack()
        tk.Label(root, text=f"将安装到：{dst}", bg=BG, fg=TXT, font=("Consolas", 9)).pack(pady=(22, 4))
        tk.Button(root, text="更改目录…", bg=CARD, fg=TXT, relief="flat", cursor="hand2",
                  command=lambda: _pick()).pack()
        var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="创建桌面快捷方式", variable=var, bg=BG, fg=TXT,
                       selectcolor=CARD, activebackground=BG,
                       command=lambda: state.__setitem__("desktop", var.get())).pack(pady=(16, 0))
        tk.Button(root, text="开 始 安 装", bg=GOLD, fg="#17171B", relief="flat",
                  font=("Microsoft YaHei UI", 11, "bold"), cursor="hand2", width=16,
                  command=screen_progress).pack(pady=26)
        tk.Label(root, text="需要管理员权限（安装到程序目录并注册卸载信息）",
                 bg=BG, fg=DIM, font=("Microsoft YaHei UI", 8)).pack(side="bottom", pady=8)

    def _pick():
        nonlocal dst
        p = filedialog.askdirectory(title="选择安装目录")
        if p:
            dst = Path(p)
            screen_welcome()

    bar, lbl = None, None

    def screen_progress():
        nonlocal bar, lbl
        for w in root.winfo_children():
            w.destroy()
        tk.Label(root, text="正在安装…", font=("Microsoft YaHei UI", 12, "bold"),
                 bg=BG, fg=TXT).pack(pady=(40, 18))
        bar = tk.Scale(root, from_=0, to=100, orient="horizontal", showvalue=False,
                       bg=BG, fg=GOLD, troughcolor=CARD, highlightthickness=0, bd=0,
                       sliderlength=2, length=420)
        bar.pack()
        lbl = tk.Label(root, text="准备解包…", bg=BG, fg=DIM, font=("Consolas", 9))
        lbl.pack(pady=10)
        threading.Thread(target=run_install, daemon=True).start()

    def run_install():
        import traceback
        def prog(p, name):
            def upd():
                bar.set(p * 100)
                lbl.configure(text=f"{name}  ({int(p*100)}%)")
            root.after(0, upd)
        try:
            do_install(dst, state["desktop"], progress=prog,
                       done=lambda: root.after(0, screen_done))
        except Exception:
            tb = traceback.format_exc()
            try:
                Path(os.environ["TEMP"], "ls_setup_err.txt").write_text(tb, encoding="utf-8")
            except Exception:
                pass
            root.after(0, lambda: _fail(tb))

    def _fail(tb):
        from tkinter import messagebox
        messagebox.showerror("安装失败", f"发生错误：\n\n{tb[-600:]}")
        screen_welcome()

    def screen_done():
        for w in root.winfo_children():
            w.destroy()
        tk.Label(root, text="✔ 安装完成", font=("Microsoft YaHei UI", 16, "bold"),
                 bg=BG, fg=GOLD).pack(pady=(50, 10))
        tk.Label(root, text=f"已安装到 {dst}，并注册到「程序和功能」。",
                 bg=BG, fg=TXT, font=("Microsoft YaHei UI", 10)).pack()
        var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="立即启动直播工坊", variable=var, bg=BG, fg=TXT,
                       selectcolor=CARD, activebackground=BG).pack(pady=(20, 0))

        def finish():
            if var.get():
                subprocess.Popen([str(dst / EXENAME)],
                                 cwd=str(dst), creationflags=CREATE_NO_WINDOW)
            root.destroy()
        tk.Button(root, text="完 成", bg=GOLD, fg="#17171B", relief="flat",
                  font=("Microsoft YaHei UI", 11, "bold"), cursor="hand2", width=14,
                  command=finish).pack(pady=26)

    screen_welcome()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        try:
            Path(os.environ["TEMP"], "ls_setup_err.txt").write_text(
                traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        raise
