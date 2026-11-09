# -*- coding: utf-8 -*-
"""
直播工坊 LiveStudio v1.2 —— 自有去重推流软件
底层引擎：自有 txt 管线（参数化复刻）｜授权：自有卡密系统（Ed25519）
v1.2：右侧仅保留「智能处理」动效面板 + 环境助手（照 LuBot 风格）；
      推流目标/中继/图层/摄像头等高级项全部内定为脚本默认值，界面不显示。
"""
import base64
import json
import os
import queue
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import licensing
import pipeline
import envassist
from pipeline import Engine, SCRIPT_DEFAULTS

BG = "#0F1115"; CARD = "#171A21"; LINE = "#262B36"
TXT = "#E7EAF0"; DIM = "#8A93A6"; GOLD = "#D7A743"; GOLD_HI = "#E5B654"
RED = "#EF4444"; GREEN = "#34D399"; BLUE = "#60A5FA"; INP = "#0C0E12"
PILL_BG = "#E8EDF2"
FONT = ("Microsoft YaHei UI", 10)
FONT_B = ("Microsoft YaHei UI", 10, "bold")
VERSION = "1.2"
CAROUSEL_SEC = 120

CONFIG_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LiveStudio" / "config.json"

# 智能处理清单（与 LuBot 面板同名逐项）
SMART_ITEMS = [
    "关键帧间隔", "前后帧对比", "动态哈希值", "光流运动重构", "骨骼点位位移",
    "音频感知指纹", "音频能量时序", "音色特征提取", "帧时间戳", "像素方差",
    "画面熵值", "DTS 时序异常", "分区运动密度检测", "VAD 语音活动检测",
]


def load_config() -> dict:
    try:
        if CONFIG_PATH.exists():
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_config(cfg: dict):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


class ActivationDialog(tk.Toplevel):
    """激活/更换激活码窗口：设备码 + 当前授权 + 激活码/文件导入 + 清除授权。"""

    def __init__(self, master, on_ok, current=None):
        super().__init__(master)
        self.on_ok = on_ok
        self.current = current or None
        self.title("直播工坊 · 激活 / 更换激活码")
        self.configure(bg=CARD)
        self.resizable(False, False)
        w, h = 580, 390
        self.geometry(f"+{(self.winfo_screenwidth()-w)//2}+{(self.winfo_screenheight()-h)//2}")
        tk.Label(self, text="🔑 激活 / 更换激活码", font=("Microsoft YaHei UI", 14, "bold"),
                 bg=CARD, fg=GOLD).pack(pady=(18, 4))
        if self.current:
            cur = (f"当前授权：{self.current.get('customer','')}　·　"
                   f"有效期 {self.current.get('expires') or '永久'}")
            tk.Label(self, text=cur, bg=CARD, fg=GREEN, font=FONT).pack()
            tk.Label(self, text="粘贴新激活码或导入 .lic 即可替换（旧授权在新码验证通过前不会失效）",
                     bg=CARD, fg=DIM, font=("Microsoft YaHei UI", 8)).pack(pady=(2, 0))
        else:
            tk.Label(self, text="未激活 —— 本机设备码如下（复制发给软件作者换取激活码）",
                     bg=CARD, fg=DIM, font=FONT).pack()
        dev = licensing.device_code()
        row = tk.Frame(self, bg=CARD); row.pack(pady=8)
        e = tk.Entry(row, font=("Consolas", 13), fg=GOLD, bg=INP, insertbackground=TXT,
                     relief="flat", width=24)
        e.insert(0, dev); e.configure(state="readonly")
        e.pack(side="left", padx=6, ipady=6)
        tk.Button(row, text="复制", bg=GOLD, fg="#17171B", relief="flat",
                  font=FONT_B, cursor="hand2",
                  command=lambda: (self.clipboard_clear(), self.clipboard_append(dev),
                                   tip.configure(text="已复制 ✓", fg=GREEN))).pack(side="left")
        tip = tk.Label(self, text="", bg=CARD, fg=GREEN, font=FONT); tip.pack()
        tk.Label(self, text="粘贴激活码（整段）或导入 .lic 文件：",
                 bg=CARD, fg=DIM, font=FONT, anchor="w").pack(fill="x", padx=40, pady=(10, 2))
        self.code = tk.Text(self, height=4, bg=INP, fg=TXT, insertbackground=TXT,
                            relief="flat", font=("Consolas", 9))
        self.code.pack(fill="x", padx=40)
        # 在线激活：19位短卡密（可电话报读，避免长码传输截断）
        ckrow = tk.Frame(self, bg=CARD); ckrow.pack(fill="x", padx=40, pady=(10, 2))
        tk.Label(ckrow, text="或输卡密在线激活：", bg=CARD, fg=DIM, font=FONT).pack(side="left")
        self.cardkey = tk.Entry(ckrow, font=("Consolas", 12), fg=GOLD, bg=INP,
                                insertbackground=TXT, relief="flat")
        self.cardkey.pack(side="left", fill="x", expand=True, padx=6, ipady=4)
        self.cardkey.insert(0, "KM-")
        self.ck_btn = tk.Button(ckrow, text="在线获取", bg=GOLD, fg="#17171B", relief="flat",
                                font=FONT_B, cursor="hand2", command=self.redeem_online)
        self.ck_btn.pack(side="left")
        btns = tk.Frame(self, bg=CARD); btns.pack(pady=12)
        tk.Button(btns, text=("更换激活码" if self.current else "激  活"), bg=GOLD, fg="#17171B",
                  relief="flat", font=FONT_B, cursor="hand2", width=10,
                  command=self.try_activate).pack(side="left", padx=6)
        tk.Button(btns, text="导入 .lic", bg=INP, fg=TXT, relief="flat", bd=1,
                  cursor="hand2", command=self.import_file).pack(side="left", padx=6)
        if self.current:
            tk.Button(btns, text="清除授权", bg=CARD, fg=RED, relief="flat", bd=1,
                      cursor="hand2", command=self.clear_license).pack(side="left", padx=6)
        tk.Button(btns, text="关闭", bg=CARD, fg=DIM, relief="flat", bd=1,
                  cursor="hand2", command=self.destroy).pack(side="left", padx=6)
        self.msg = tk.Label(self, text="", bg=CARD, fg=RED, font=FONT)
        self.msg.pack()
        self.grab_set()

    def try_activate(self):
        text = self.code.get("1.0", "end").strip()
        if not text:
            self.msg.configure(text="请粘贴激活码")
            return
        ok, reason, payload = licensing.verify_text(text, licensing.device_code())
        if ok:
            licensing.save_license(text)
            self.destroy()
            self.on_ok(payload)
        else:
            zh = {"bad_format": "格式错误", "bad_signature": "签名无效（非本软件授权）",
                  "expired": "授权已过期", "hwid_mismatch": "设备码不匹配"}.get(reason, reason)
            self.msg.configure(text=f"更换失败：{zh}（当前授权未受影响）")

    def redeem_online(self):
        """卡密在线激活：短码从云端取回完整授权（后台线程，不卡界面）。"""
        import threading
        k = self.cardkey.get().strip()
        if len(k) < 10:
            self.msg.configure(text="请输入完整卡密（KM-XXXX-XXXX-XXXX-XXXX）")
            return
        self.ck_btn.configure(text="获取中…", state="disabled")
        self.msg.configure(text="")

        def work():
            try:
                lic_text = licensing.redeem_cardkey(k)
                self.code.delete("1.0", "end")
                self.code.insert("1.0", lic_text)
                self.root.after(0, self.try_activate)
            except Exception as ex:
                self.root.after(0, lambda: (
                    self.ck_btn.configure(text="在线获取", state="normal"),
                    self.msg.configure(text=f"在线获取失败：{ex}")))
        threading.Thread(target=work, daemon=True).start()

    def import_file(self):
        p = filedialog.askopenfilename(filetypes=[("授权文件", "*.lic"), ("全部", "*.*")])
        if p:
            self.code.delete("1.0", "end")
            self.code.insert("1.0", open(p, encoding="utf-8").read())
            self.try_activate()

    def clear_license(self):
        if messagebox.askyesno("清除授权", "确定清除本机授权？\n清除后需要新的激活码才能再次使用。",
                               parent=self):
            licensing.clear_license()
            self.destroy()
            self.on_ok(None)


class App:
    def __init__(self, root: tk.Tk, payload: dict):
        self.root = root
        self.customer = payload.get("customer", "")
        self.engine = Engine()
        self.logq = queue.Queue()
        self.cfg = load_config()
        self.materials = pipeline.scan_materials()
        self.playing = False
        self.streaming = False
        self._restart_after = None
        self._suspend_live = False
        self._scanning = False
        self._smart_lit = 0
        self._smart_items = []
        # 内定的运行参数（界面不显示，保持脚本默认）
        self.carousel_on = tk.BooleanVar(value=False)
        self.server_on = tk.BooleanVar(value=False)
        self.url_var = tk.StringVar(value="rtmp://127.0.0.1:1935/tklive")
        # 画面叠加（摄像头）
        self.vars = {}
        self.cam_on = tk.BooleanVar(value=False)
        self.cam_var = tk.StringVar(value="")
        self.vcam_on = tk.BooleanVar(value=False)
        self.vcam = pipeline.VirtualCam()          # 内置虚拟摄像头（LiveStudio Cam）
        self._build_ui()
        self._apply_config()
        self.engine.set_log(lambda line: self.logq.put(line))
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        self._poll_logs(); self._poll_stats(); self._tick_carousel(); self._smart_tick()

    # ---------- 配置 ----------
    def _apply_config(self):
        c = self.cfg
        mats = [pipeline.Path(p) for p in c.get("materials", []) if pipeline.Path(p).exists()]
        if mats:
            self.materials = mats
        self._refresh_list()
        self.carousel_on.set(c.get("carousel_on", False))
        self.cam_on.set(c.get("cam_on", False))
        self.cam_var.set(c.get("cam_dev", ""))
        if "realcam_opacity" in self.vars:
            self.vars["realcam_opacity"].set(c.get("realcam_opacity", 0.05))
        if c.get("cam_dev"):
            self._scan_cams(prefill=c.get("cam_dev"))
        self._log(f"[配置] 已加载 {CONFIG_PATH.name}")

    def _collect_config(self) -> dict:
        return {"materials": [str(p) for p in self.materials],
                "carousel_on": self.carousel_on.get(),
                "cam_on": self.cam_on.get(),
                "cam_dev": self.cam_var.get(),
                "realcam_opacity": self.vars.get("realcam_opacity").get()
                if "realcam_opacity" in self.vars else 0.05}

    def save(self):
        try:
            save_config(self._collect_config())
        except Exception as ex:
            self._log(f"[配置] 保存失败: {ex}")

    def _quit(self):
        self.stop_all(); self.save(); self.root.destroy()

    # ---------- UI 基件 ----------
    def _btn(self, parent, text, cmd, primary=False, width=10):
        return tk.Button(parent, text=text, command=cmd, relief="flat", cursor="hand2",
                         font=FONT_B, width=width,
                         bg=GOLD if primary else INP, fg="#17171B" if primary else TXT,
                         activebackground=GOLD_HI if primary else LINE, bd=0)

    def _card(self, parent, title):
        f = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        tk.Label(f, text=title, bg=CARD, fg=GOLD, font=FONT_B).pack(anchor="w", padx=10, pady=(8, 2))
        return f

    def _slider(self, parent, label, key, lo, hi):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=10, pady=1)
        tk.Label(row, text=label, bg=CARD, fg=DIM, font=FONT, width=8, anchor="w").pack(side="left")
        v = tk.DoubleVar(value=SCRIPT_DEFAULTS.get(key, 0.05))
        s = tk.Scale(row, variable=v, from_=lo, to=hi, resolution=(hi - lo) / 200,
                     orient="horizontal", showvalue=True, bg=CARD, fg=TXT,
                     troughcolor=INP, highlightthickness=0, bd=0, sliderlength=14,
                     font=("Consolas", 8), command=lambda *_: self._live_restart())
        s.pack(side="left", fill="x", expand=True, padx=4)
        self.vars[key] = v
        return v

    # ---------- 实时生效（防抖自动重启管线） ----------
    def _live_restart(self, *_):
        if self._suspend_live:
            return
        if self._restart_after is not None:
            try:
                self.root.after_cancel(self._restart_after)
            except Exception:
                pass
        self._restart_after = self.root.after(900, self._do_live_restart)

    def _do_live_restart(self):
        self._restart_after = None
        self.save()
        if not (self.playing or self.streaming):
            return
        was_push, was_play = self.streaming, self.playing
        if self.playing:
            self.stop_preview_side()
        if self.streaming:
            self.engine.stop_push()
            self.streaming = False
            self.push_btn.configure(text="🔴 开始推流", bg=GOLD, fg="#17171B")
        self.params = self._collect_params()
        self._log("[设置] 画面叠加已变更，管线自动重启…")
        if was_push:
            self.push()
        elif was_play:
            self.play()

    def _build_ui(self):
        r = self.root
        r.title(f"直播工坊 LiveStudio v{VERSION}")
        r.configure(bg=BG)
        _w, _h = 1180, 840
        r.geometry(f"{_w}x{_h}+{max(0,(r.winfo_screenwidth()-_w)//2)}"
                   f"+{max(0,(r.winfo_screenheight()-_h-40)//2)}")
        r.minsize(1180, 740)

        # 顶栏
        top = tk.Frame(r, bg=CARD, height=44)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text="▶ 直播工坊 ", bg=CARD, fg=GOLD,
                 font=("Microsoft YaHei UI", 12, "bold")).pack(side="left", padx=(14, 2))
        tk.Label(top, text=f"LiveStudio v{VERSION}", bg=CARD, fg=DIM,
                 font=FONT).pack(side="left")
        self.act_lbl = tk.Label(top, text=(f"已激活：{self.customer}" if self.customer else ""),
                                bg=CARD, fg=GREEN, font=FONT)
        self.act_lbl.pack(side="right", padx=(6, 10))
        self._btn(top, "🔑 激活", self._open_activation, width=6).pack(side="right", padx=4, pady=8)
        self._btn(top, "❔ 关于", self._about, width=6).pack(side="right", padx=4, pady=8)
        self._btn(top, " ✕ ", r.destroy, width=4).pack(side="right", padx=6, pady=8)
        self._btn(top, " — ", r.iconify, width=4).pack(side="right", pady=8)

        body = tk.Frame(r, bg=BG); body.pack(fill="both", expand=True, padx=10, pady=8)

        # 左：素材库
        left = self._card(body, "📁 素材库")
        left.pack(side="left", fill="y", padx=(0, 8))
        self.listbox = tk.Listbox(left, bg=INP, fg=TXT, selectbackground=GOLD,
                                  selectforeground="#17171B", relief="flat",
                                  font=("Consolas", 9), width=28, highlightthickness=0)
        self.listbox.pack(padx=10, pady=6, fill="y", expand=True)
        self.listbox.bind("<Double-Button-1>", lambda e: self.play())
        lb = tk.Frame(left, bg=CARD); lb.pack(fill="x", padx=10, pady=(0, 4))
        for i, (t, c) in enumerate([("添加", self.add_files), ("移除", self.remove_sel),
                                    ("清空", self.clear_all), ("扫描目录", self.scan_dir)]):
            self._btn(lb, t, c, width=6).grid(row=i // 2, column=i % 2, padx=2, pady=2, sticky="we")
        lb2 = tk.Frame(left, bg=CARD); lb2.pack(fill="x", padx=10, pady=(0, 10))
        self._btn(lb2, "上移", lambda: self.move(-1), width=6).pack(side="left", expand=True, fill="x", padx=2)
        self._btn(lb2, "下移", lambda: self.move(1), width=6).pack(side="left", expand=True, fill="x", padx=2)

        # 中：预览 + 走带
        mid = tk.Frame(body, bg=BG); mid.pack(side="left", fill="both", expand=True, padx=8)
        self.preview_lbl = tk.Label(mid, bg="#000000", text="预览区\n（双击素材或点 ▶ 预览）",
                                    fg=DIM, font=FONT, width=30, height=12)
        self.preview_lbl.pack(fill="both", expand=True)
        transport = tk.Frame(mid, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        transport.pack(fill="x", pady=(8, 0))
        self.play_btn = self._btn(transport, "▶  预  览", self.toggle_play, primary=True, width=9)
        self.play_btn.pack(side="left", padx=10, pady=10)
        self.push_btn = self._btn(transport, "🔴 开始推流", self.toggle_push, primary=True, width=11)
        self.push_btn.pack(side="left", padx=6, pady=10)
        self._btn(transport, "⏹ 全部停止", self.stop_all, width=9).pack(side="left", padx=6, pady=10)
        tk.Checkbutton(transport, text="自动轮播", variable=self.carousel_on, bg=CARD, fg=TXT,
                       selectcolor=INP, activebackground=CARD, activeforeground=GOLD,
                       font=FONT, command=self._carousel_switched).pack(side="right", padx=14)

        # 右：智能处理 + 画面叠加 + 环境助手
        right = tk.Frame(body, bg=BG); right.pack(side="right", fill="y", padx=(8, 0))
        self._smart_card(right)
        self._cam_card(right)
        self._env_card(right)

        # 底：状态 + 日志
        bottom = tk.Frame(r, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        bottom.pack(fill="x", padx=10, pady=(0, 8))
        self.status_dot = tk.Label(bottom, text=" ● 就绪", bg=CARD, fg=GREEN, font=FONT)
        self.status_dot.pack(side="left", padx=8, pady=4)
        self.status_txt = tk.Label(bottom, text="", bg=CARD, fg=DIM, font=("Consolas", 9))
        self.status_txt.pack(side="left", padx=8)
        self._btn(bottom, "📜 日志", self.toggle_log, width=8).pack(side="right", padx=8, pady=4)
        self.logf = tk.Frame(r, bg=BG)
        self.logtxt = tk.Text(self.logf, bg=INP, fg=DIM, relief="flat", height=8,
                              font=("Consolas", 8), state="disabled")
        self.logtxt.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        # 按实际需求尺寸居中（防高 DPI 缩放下窗口被内容撑宽出屏）
        r.update_idletasks()
        sw, sh = r.winfo_screenwidth(), r.winfo_screenheight()
        w2 = min(r.winfo_reqwidth(), sw - 40)
        h2 = min(r.winfo_reqheight(), sh - 80)
        r.geometry(f"{w2}x{h2}+{(sw - w2) // 2}+{max(0, (sh - h2 - 30) // 2)}")

    # ---------- 智能处理面板（照 LuBot 图样） ----------
    def _smart_card(self, parent):
        card = tk.Frame(parent, bg=CARD, highlightbackground=LINE, highlightthickness=1)
        card.pack(fill="x")
        # 白底胶囊标题
        pill = tk.Canvas(card, width=140, height=40, bg=CARD, highlightthickness=0)
        pill.pack(pady=(10, 0))
        pill.create_rectangle(10, 4, 130, 36, fill=PILL_BG, width=0)
        pill.create_text(70, 20, text="智能处理", fill="#111827",
                         font=("Microsoft YaHei UI", 12, "bold"))
        tk.Label(card, text="点击「立即播放」后自动逐项预处理，无需任何设置。",
                 bg=CARD, fg=DIM, font=("Microsoft YaHei UI", 8), wraplength=300,
                 justify="center").pack(padx=12, pady=(2, 8))
        self._smart_dots = []
        for name in SMART_ITEMS:
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=22, pady=1)
            dot = tk.Canvas(row, width=14, height=14, bg=CARD, highlightthickness=0)
            dot.pack(side="left", padx=(0, 8))
            lbl = tk.Label(row, text=name, bg=CARD, fg="#5B6472",
                           font=("Microsoft YaHei UI", 10), anchor="w")
            lbl.pack(side="left")
            self._smart_dots.append((dot, lbl))
        self.smart_status = tk.Label(card, text="待机 · 点击「▶ 预览 / 🔴 开始推流」后开始预处理",
                                     bg=CARD, fg=DIM, font=("Microsoft YaHei UI", 8),
                                     anchor="w", wraplength=300)
        self.smart_status.pack(fill="x", padx=14, pady=(10, 12))
        return card

    def _smart_draw(self):
        n = self._smart_lit
        for i, (dot, lbl) in enumerate(self._smart_dots):
            dot.delete("all")
            lit = i < n
            dot.create_oval(2, 2, 12, 12, outline=(GOLD if lit else "#3A4250"),
                            width=2, fill=(GOLD if lit else CARD))
            lbl.configure(fg=(TXT if lit else "#5B6472"))

    def _smart_tick(self):
        active = self.playing or self.streaming
        if active:
            if self._smart_lit == 0:
                self.smart_status.configure(text="预处理中…", fg=GOLD)
            if self._smart_lit < len(SMART_ITEMS):
                self._smart_lit += 1
                self._smart_draw()
                if self._smart_lit == len(SMART_ITEMS):
                    self.smart_status.configure(
                        text="已完成 · 随机化管线运行中（去重参数为脚本固定值）", fg=GREEN)
                self.root.after(380, self._smart_tick)
                return
        else:
            if self._smart_lit != 0:
                self._smart_lit = 0
                self._smart_draw()
            self.smart_status.configure(text="待机 · 点击「▶ 预览 / 🔴 开始推流」后开始预处理",
                                        fg=DIM)
        self.root.after(400, self._smart_tick)

    # ---------- 画面叠加（真实摄像头混入） ----------
    def _cam_card(self, parent):
        ccad = self._card(parent, "📷 画面叠加（真实摄像头）")
        ccad.pack(fill="x", pady=(10, 0))
        crow = tk.Frame(ccad, bg=CARD); crow.pack(fill="x", padx=10, pady=2)
        tk.Checkbutton(crow, text="启用", variable=self.cam_on, bg=CARD, fg=TXT,
                       selectcolor=INP, activebackground=CARD, activeforeground=GOLD,
                       font=FONT, command=lambda: self._live_restart()).pack(side="left")
        self.cam_scan_btn = self._btn(crow, "扫描设备", self._scan_cams, width=8)
        self.cam_scan_btn.pack(side="right")
        self.cam_menu = tk.OptionMenu(ccad, self.cam_var, "(先扫描)")
        self.cam_menu.configure(bg=INP, fg=TXT, activebackground=LINE, activeforeground=GOLD,
                                highlightthickness=0, bd=1, font=FONT, direction="below")
        self.cam_menu.pack(fill="x", padx=10, pady=2)
        self._slider(ccad, "叠加比例", "realcam_opacity", 0.0, 0.3)
        vrow = tk.Frame(ccad, bg=CARD); vrow.pack(fill="x", padx=10, pady=(4, 0))
        tk.Checkbutton(vrow, text="虚拟摄像头输出（开播平台选设备）", variable=self.vcam_on,
                       bg=CARD, fg=TXT, selectcolor=INP, activebackground=CARD,
                       activeforeground=GOLD, font=FONT,
                       command=self._toggle_vcam).pack(side="left")
        tk.Label(ccad, text=f"设备名：{pipeline.VCAM_NAME}（安装时自动注册驱动）",
                 bg=CARD, fg=DIM, font=("Microsoft YaHei UI", 8)).pack(anchor="w", padx=10, pady=(0, 6))
        tk.Label(ccad, text="提示：摄像头画面以低透明度混入，防录播判定",
                 bg=CARD, fg=DIM, font=("Microsoft YaHei UI", 8)).pack(anchor="w", padx=10, pady=(0, 6))

    def _scan_cams(self, prefill=None):
        if self._scanning:
            return
        self._scanning = True
        self.cam_scan_btn.configure(text="扫描中…", state="disabled")
        self._log("[摄像头] 扫描 dshow 设备…")

        def work():
            devs = pipeline.list_cameras()
            while True:
                try:
                    self.root.after(0, lambda: self._cams_done(devs, prefill))
                    break
                except RuntimeError:
                    time.sleep(0.05)
        threading.Thread(target=work, daemon=True).start()

    def _cams_done(self, devs, prefill=None):
        self._scanning = False
        self.cam_scan_btn.configure(text="扫描设备", state="normal")
        menu = self.cam_menu["menu"]
        menu.delete(0, "end")
        if not devs:
            menu.add_command(label="(未发现摄像头)", state="disabled")
            self._log("[摄像头] 未发现视频设备")
            return
        for d in devs:
            menu.add_command(label=d,
                             command=lambda v=d: (self.cam_var.set(v), self._live_restart()))
        self.cam_var.set(prefill if prefill in devs else devs[0])
        self._log(f"[摄像头] 发现 {len(devs)} 个: {', '.join(devs)}")

    def _toggle_vcam(self):
        self.vcam.log = self._log
        if self.vcam_on.get():
            m = self.current()
            if not m:
                self.vcam_on.set(False)
                messagebox.showinfo("直播工坊", "先添加素材")
                return
            if not self.vcam.start(m, self._collect_params()):
                self.vcam_on.set(False)
        else:
            self.vcam.stop()

    def _resolve_cam(self):
        if not self.cam_on.get():
            return None
        dev = self.cam_var.get()
        return dev if dev and not dev.startswith("(") else None

    # ---------- 环境助手 ----------
    def _env_card(self, parent):
        ecard = self._card(parent, "🌍 环境助手（TikTok 区域）")
        ecard.pack(fill="x", pady=(10, 0))
        self.env_region = tk.StringVar(value="美国·东部")
        env_om = tk.OptionMenu(ecard, self.env_region, *envassist.REGIONS.keys())
        env_om.configure(bg=INP, fg=TXT, activebackground=LINE, activeforeground=GOLD,
                         highlightthickness=0, bd=1, font=FONT, direction="below")
        env_om.pack(fill="x", padx=10, pady=2)
        ebtns = tk.Frame(ecard, bg=CARD); ebtns.pack(fill="x", padx=10, pady=2)
        self._btn(ebtns, "一键配置", self._env_apply, width=8).pack(side="left", expand=True, fill="x", padx=2)
        self._btn(ebtns, "扫描", self._env_scan, width=6).pack(side="left", expand=True, fill="x", padx=2)
        self._btn(ebtns, "清理", self._env_clean, width=6).pack(side="left", expand=True, fill="x", padx=2)
        self.env_status = tk.Label(ecard, text="状态：点击「扫描」读取", bg=CARD, fg=DIM,
                                   font=("Consolas", 8), anchor="w")
        self.env_status.pack(fill="x", padx=10, pady=(2, 6))

    def _env_apply(self):
        name = self.env_region.get()
        threading.Thread(target=lambda: envassist.apply_region(name, self._log),
                         daemon=True).start()

    def _env_scan(self):
        def work():
            s = envassist.scan()
            self.root.after(0, lambda: self.env_status.configure(text=f"状态：{s}"))
            envassist.clean_scan(self._log)
        threading.Thread(target=work, daemon=True).start()

    def _env_clean(self):
        threading.Thread(target=lambda: envassist.clean_purge(self._log),
                         daemon=True).start()

    # ---------- 激活/关于 ----------
    def _open_activation(self):
        ok, cur = licensing.current_info()

        def done(p):
            if p is None:
                self.act_lbl.configure(text="未激活", fg=RED)
                self._log("[激活] 已清除本机授权")
            else:
                self.act_lbl.configure(text=f"已激活：{p.get('customer', '')}", fg=GREEN)
                self._log(f"[激活] 授权已更新：{p.get('customer', '')}"
                          f"（有效期 {p.get('expires') or '永久'}）")
        ActivationDialog(self.root, done, current=(cur if ok else None))

    def _about(self):
        w = tk.Toplevel(self.root); w.title("关于 直播工坊")
        w.configure(bg=CARD); w.resizable(False, False)
        txt = (
            f"直播工坊 LiveStudio v{VERSION}\n\n"
            "自有去重推流软件：底层为自有 txt 管线引擎，\n"
            "授权为自有卡密系统（Ed25519 离线验证）。\n\n"
            "使用流程：\n"
            "  1. 勾选「自动轮播」（可选）\n"
            "  2. 选素材 → 点「🔴 开始推流」\n"
            "  3. 直播伴侣/OBS 拉取本地流或 HLS 播放\n\n"
            "去重参数为脚本固定值（无需设置）；\n"
            "高级功能（推流地址/中继/摄像头/图层）已内定。\n\n"
            f"设备码：{licensing.device_code()}"
        )
        tk.Label(w, text=txt, bg=CARD, fg=TXT, font=FONT, justify="left", anchor="w")\
            .pack(padx=24, pady=18)
        tk.Button(w, text="好", bg=GOLD, fg="#17171B", relief="flat", font=FONT_B,
                  cursor="hand2", command=w.destroy).pack(pady=(0, 14))

    # ---------- 素材 ----------
    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for p in self.materials:
            self.listbox.insert("end", p.name)
        if self.materials:
            self.listbox.selection_set(0)

    def add_files(self):
        fs = filedialog.askopenfilenames(
            filetypes=[("视频", "*.mp4 *.mov *.mkv *.flv *.ts *.avi *.webm")])
        for f in fs:
            p = pipeline.Path(f)
            if p not in self.materials:
                self.materials.append(p)
        self._refresh_list(); self.save()

    def remove_sel(self):
        sel = self.listbox.curselection()
        if sel:
            del self.materials[sel[0]]; self._refresh_list(); self.save()

    def clear_all(self):
        self.stop_all(); self.materials.clear(); self._refresh_list(); self.save()

    def scan_dir(self):
        self.materials = pipeline.scan_materials()
        self._refresh_list(); self.save()
        self._log(f"[素材] 扫描 {pipeline.MATERIAL_DIR} → {len(self.materials)} 个")

    def move(self, d):
        sel = self.listbox.curselection()
        if not sel:
            return
        i = sel[0]; j = i + d
        if 0 <= j < len(self.materials):
            self.materials[i], self.materials[j] = self.materials[j], self.materials[i]
            self._refresh_list(); self.listbox.selection_set(j); self.save()

    def current(self):
        sel = self.listbox.curselection()
        if sel:
            return self.materials[sel[0]]
        return self.materials[0] if self.materials else None

    # ---------- 走带（参数固定为脚本值，单素材模式） ----------
    def _collect_params(self):
        p = dict(SCRIPT_DEFAULTS)
        p["width"], p["height"] = 720, 1280
        p["layer_mode"] = "single"
        if "realcam_opacity" in self.vars:
            p["realcam_opacity"] = float(self.vars["realcam_opacity"].get())
        return p

    def toggle_play(self):
        self.stop_preview_side() if self.playing else self.play()

    def play(self):
        m = self.current()
        if not m:
            messagebox.showinfo("直播工坊", "先添加素材"); return
        self.params = self._collect_params()
        if self.engine.start_preview(m, self.params, cam=self._resolve_cam()):
            self.playing = True
            self.play_btn.configure(text="⏸ 停止预览", bg=RED, fg="#FFFFFF")
            self._preview_frame()

    def stop_preview_side(self):
        self.engine.stop_preview()
        self.playing = False
        self.play_btn.configure(text="▶  预  览", bg=GOLD, fg="#17171B")
        self.preview_lbl.configure(image="", text="预览已停止")

    def toggle_push(self):
        self.stop_push_side() if self.streaming else self.push()

    def push(self):
        m = self.current()
        if not m:
            messagebox.showinfo("直播工坊", "先添加素材"); return
        self.params = self._collect_params()
        if self.engine.start_push(m, self.url_var.get().strip(), self.params,
                                  cam=self._resolve_cam()):
            self.streaming = True
            self.push_btn.configure(text="🔴 停止推流", bg=RED, fg="#FFFFFF")
            if not self.playing:
                self.play()
            self.save()

    def stop_push_side(self):
        self.engine.stop_push()
        self.streaming = False
        self.push_btn.configure(text="🔴 开始推流", bg=GOLD, fg="#17171B")

    def stop_all(self):
        self.stop_push_side(); self.stop_preview_side()
        self.vcam.stop(); self.vcam_on.set(False)
        self.engine.stop_mtx()
        self.status_dot.configure(text=" ● 已停止", fg=DIM)

    def _carousel_switched(self):
        if self.carousel_on.get():
            self._log(f"[轮播] 已开启，每 {CAROUSEL_SEC}s 切换下一个素材")
        self.save()

    # ---------- 预览帧 ----------
    def _preview_frame(self):
        if not self.playing:
            return
        fb = self.engine.preview.next_frame() if self.engine.preview else None
        if fb:
            try:
                img = tk.PhotoImage(data=base64.b64encode(fb).decode())
                self.preview_lbl.configure(image=img, text="")
                self._pv_img = img
            except Exception as ex:
                self._log(f"[预览] 帧解码异常: {ex}")
        self.root.after(80, self._preview_frame)

    # ---------- 状态/日志 ----------
    def _log(self, line):
        self.logq.put(line)

    def _poll_logs(self):
        try:
            while True:
                line = self.logq.get_nowait()
                self.logtxt.configure(state="normal")
                self.logtxt.insert("end", line + "\n")
                self.logtxt.see("end")
                self.logtxt.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_logs)

    def _poll_stats(self):
        st = self.engine.stats
        if self.streaming and st["speed"] is not None:
            self.status_dot.configure(text=" ● 推流中", fg=GREEN)
            self.status_txt.configure(
                text=f"speed={st['speed']}x  frame={st['frame']}  "
                     f"bitrate={st['bitrate']}kbps  720x1280 → {self.url_var.get()}")
        elif self.streaming:
            self.status_dot.configure(text=" ● 启动中…", fg=GOLD)
        elif self.playing:
            self.status_dot.configure(text=" ● 预览中", fg=BLUE)
        else:
            self.status_dot.configure(text=" ● 就绪", fg=GREEN)
            self.status_txt.configure(
                text=f"素材 {len(self.materials)} 个  设备码 {licensing.device_code()}")
        self.root.after(1000, self._poll_stats)

    def toggle_log(self):
        if self.logf.winfo_ismapped():
            self.logf.pack_forget()
        else:
            self.logf.pack(fill="both", expand=False, padx=0, pady=0)

    def _tick_carousel(self):
        if self.carousel_on.get() and (self.streaming or self.playing) and len(self.materials) > 1:
            sel = self.listbox.curselection()
            nxt = ((sel[0] if sel else 0) + 1) % len(self.materials)
            self.listbox.selection_clear(0, "end")
            self.listbox.selection_set(nxt)
            self._log(f"[轮播] 切换素材 → {self.materials[nxt].name}")
            if self.playing:
                self.stop_preview_side()
            if self.streaming:
                self.engine.stop_push(); self.playing = False
                self.push()
            else:
                self.play()
        self.root.after(CAROUSEL_SEC * 1000, self._tick_carousel)


def main():
    root = tk.Tk()
    root.withdraw()
    ok, reason, payload = licensing.import_sibling_license()
    if not ok:
        ActivationDialog(root, lambda p: _start(root, p))
        root.mainloop()
        return
    _start(root, payload)


def _start(root, payload):
    App(root, payload)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()
