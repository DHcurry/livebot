# -*- coding: utf-8 -*-
"""
直播工坊 LiveStudio v2.0 —— 正式重构版
技术栈：PySide6 + QFluentWidgets + FramelessWindow + QOpenGLWidget 预览
        + QDockWidget 可拖拽面板 + 独立底层推流服务（ffmpeg 子进程）
复用：pipeline.py（txt管线引擎/虚拟摄像头）licensing.py（卡密授权）
      envassist.py（城市级环境助手）
"""
import base64
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPainter, QColor, QFont
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import (
    QApplication, QDockWidget, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QPushButton, QPlainTextEdit, QSlider, QCheckBox, QComboBox,
    QStackedWidget, QVBoxLayout, QWidget, QDialog, QFormLayout, QSpinBox,
)
from qfluentwidgets import (
    SubtitleLabel, CaptionLabel, PushButton, PrimaryPushButton, SwitchButton,
    BodyLabel, InfoBar, InfoBarPosition, setTheme, Theme,
)
from qframelesswindow import FramelessMainWindow

import licensing
import envassist
import pipeline
from pipeline import Engine, SCRIPT_DEFAULTS, VirtualCam, VCAM_NAME, scan_materials

VERSION = "2.0"
BG = "#0F1115"; CARD = "#171A21"; LINE = "#262B36"
TXT = "#E7EAF0"; DIM = "#8A93A6"; GOLD = "#D7A743"
RED = "#EF4444"; GREEN = "#34D399"; BLUE = "#60A5FA"; INP = "#0C0E12"
CAROUSEL_SEC = 120

CONFIG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LiveStudio" / "config_v2.json"
SMART_ITEMS = [
    "关键帧间隔", "前后帧对比", "动态哈希值", "光流运动重构", "骨骼点位位移",
    "音频感知指纹", "音频能量时序", "音色特征提取", "帧时间戳", "像素方差",
    "画面熵值", "DTS 时序异常", "分区运动密度检测", "VAD 语音活动检测",
]


def load_cfg():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    except Exception:
        return {}


def save_cfg(cfg):
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


# ============ OpenGL 预览 ============
class GLPreview(QOpenGLWidget):
    def __init__(self):
        super().__init__()
        self._img = QImage()
        self.setMinimumSize(270, 480)
        self.setStyleSheet("background:#000;border:1px solid #262B36;")

    def show_png(self, fb: bytes):
        img = QImage.fromData(fb, "PNG")
        if not img.isNull():
            self._img = img
            self.update()

    def paintGL(self):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#000000"))
        if not self._img.isNull():
            p.setRenderHint(QPainter.SmoothPixmapTransform, True)
            p.drawImage(self.rect(), self._img)


# ============ 智能处理面板 ============
class SmartCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("smartCard")
        self.setStyleSheet(
            f"#smartCard{{background:{CARD};border:1px solid {LINE};border-radius:10px;}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.addWidget(SubtitleLabel("✨ 智能处理"))
        lay.addWidget(CaptionLabel("点击「开始推流」后自动逐项预处理，无需任何设置。"))
        self.dots = []
        for name in SMART_ITEMS:
            row = QHBoxLayout()
            dot = QLabel("○"); dot.setFixedWidth(16)
            dot.setStyleSheet(f"color:#3A4250;font-size:13px;")
            lbl = QLabel(name); lbl.setStyleSheet(f"color:#5B6472;font-size:13px;")
            row.addWidget(dot); row.addWidget(lbl); row.addStretch()
            lay.addLayout(row)
            self.dots.append((dot, lbl))
        self.status = CaptionLabel("待机 · 点击「🔴 开始推流」后开始预处理")
        self.status.setStyleSheet(f"color:{DIM};")
        lay.addWidget(self.status)
        self._lit = 0

    def set_active(self, active: bool):
        if active:
            if self._lit == 0:
                self.status.setText("预处理中…")
                self.status.setStyleSheet(f"color:{GOLD};")
            if self._lit < len(SMART_ITEMS):
                self._lit += 1
                d, l = self.dots[self._lit - 1]
                d.setText("●"); d.setStyleSheet(f"color:{GOLD};font-size:13px;")
                l.setStyleSheet(f"color:{TXT};font-size:13px;")
                if self._lit == len(SMART_ITEMS):
                    self.status.setText("已完成 · 随机化管线运行中（脚本固定参数）")
                    self.status.setStyleSheet(f"color:{GREEN};")
        else:
            if self._lit:
                for d, l in self.dots:
                    d.setText("○"); d.setStyleSheet("color:#3A4250;font-size:13px;")
                    l.setStyleSheet("color:#5B6472;font-size:13px;")
                self._lit = 0
            self.status.setText("待机 · 点击「🔴 开始推流」后开始预处理")
            self.status.setStyleSheet(f"color:{DIM};")


# ============ 画面叠加面板 ============
class OverlayCard(QFrame):
    scanned = Signal(list)   # 跨线程回传扫描结果（线程安全）

    def __init__(self, log):
        super().__init__()
        self.setObjectName("ovCard")
        self.setStyleSheet(
            f"#ovCard{{background:{CARD};border:1px solid {LINE};border-radius:10px;}}")
        self.log = log
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.addWidget(SubtitleLabel("📷 画面叠加"))
        self.cam_sw = SwitchButton("真实摄像头 5% 叠加")
        lay.addWidget(self.cam_sw)
        crow = QHBoxLayout()
        self.cam_combo = QComboBox(); self.cam_combo.setPlaceholderText("先扫描设备")
        self.scan_btn = PushButton("扫描设备")
        crow.addWidget(self.cam_combo, 1); crow.addWidget(self.scan_btn)
        lay.addLayout(crow)
        self.vcam_sw = SwitchButton(f"虚拟摄像头输出（{VCAM_NAME}）")
        self.vcam_sw.setToolTip("开播平台直接选此设备，无需 RTMP 中转")
        lay.addWidget(self.vcam_sw)
        srow = QHBoxLayout()
        srow.addWidget(BodyLabel("叠加比例"))
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 30); self.opacity.setValue(5)
        self.pct = BodyLabel("5%")
        self.opacity.valueChanged.connect(lambda v: self.pct.setText(f"{v}%"))
        srow.addWidget(self.opacity, 1); srow.addWidget(self.pct)
        lay.addLayout(srow)
        lay.addWidget(CaptionLabel("提示：摄像头画面以低透明度混入，防录播判定"))

    def scan(self):
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("扫描中…")

        def work():
            try:
                devs = pipeline.list_cameras()
            except Exception:
                devs = []
            self.scanned.emit(devs)   # 信号自动排队到GUI线程执行
        threading.Thread(target=work, daemon=True).start()


# ============ 环境助手面板 ============
class EnvCard(QFrame):
    def __init__(self, log, status_cb):
        super().__init__()
        self.setObjectName("envCard")
        self.setStyleSheet(
            f"#envCard{{background:{CARD};border:1px solid {LINE};border-radius:10px;}}")
        self.log = log
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.addWidget(SubtitleLabel("🌍 环境助手（城市级）"))
        lay.addWidget(CaptionLabel("选好目标城市 → 一键配置（时区/区域/清理）"))
        self.city = QComboBox()
        self.city.addItems(list(envassist.REGIONS.keys()))
        lay.addWidget(self.city)
        row = QHBoxLayout()
        self.apply_btn = PrimaryPushButton("一键配置")
        self.scan_btn = PushButton("体检")
        self.clean_btn = PushButton("清理")
        row.addWidget(self.apply_btn, 2); row.addWidget(self.scan_btn, 1)
        row.addWidget(self.clean_btn, 1)
        lay.addLayout(row)
        self.info = CaptionLabel("状态：点击「体检」读取本机")
        self.info.setStyleSheet(f"color:{DIM};")
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        lay.addWidget(CaptionLabel("清理六项：TikTok进程/缓存/注册表 + DNS刷新 + WSearch停用 + 系统区域"))

    def run(self, kind, fn):
        self.info.setText("执行中…")
        def work():
            try:
                fn()
            except Exception as ex:
                self.log(f"[环境助手] 异常: {ex}")
        threading.Thread(target=work, daemon=True).start()


# ============ 激活对话框 ============
class ActivateDialog(QDialog):
    def __init__(self, parent, on_ok):
        super().__init__(parent)
        self.on_ok = on_ok
        self.setWindowTitle("激活 / 更换激活码")
        self.setFixedSize(620, 460)
        self.setStyleSheet(f"background:{CARD};")
        lay = QVBoxLayout(self)
        lay.addWidget(SubtitleLabel("🔑 激活 / 更换激活码"))
        ok, cur = licensing.current_info()
        if ok:
            lab = BodyLabel(f"当前授权：{cur.get('customer','')} · "
                            f"有效期 {cur.get('expires') or '永久'}")
            lab.setStyleSheet(f"color:{GREEN};")
            lay.addWidget(lab)
        lay.addWidget(CaptionLabel("本机设备码（发给软件作者换取激活码）"))
        dev = licensing.device_code()
        dev_row = QHBoxLayout()
        self.dev = QLineEdit(dev); self.dev.setReadOnly(True)
        self.dev.setStyleSheet(f"background:{INP};color:{GOLD};border:1px solid {LINE};")
        copy = PushButton("复制")
        copy.clicked.connect(lambda: (QApplication.clipboard().setText(dev),
                                      InfoBar.success("设备码已复制", parent=self,
                                                      position=InfoBarPosition.TOP)))
        dev_row.addWidget(self.dev); dev_row.addWidget(copy)
        lay.addLayout(dev_row)

        lay.addWidget(CaptionLabel("① 输入短卡密在线激活（推荐，19位，可电话报读）"))
        ck_row = QHBoxLayout()
        self.ck = QLineEdit("KM-")
        self.ck.setPlaceholderText("KM-XXXX-XXXX-XXXX-XXXX")
        self.ck.setStyleSheet(f"background:{INP};color:{GOLD};border:1px solid {LINE};padding:6px;")
        self.ck_btn = PrimaryPushButton("在线获取")
        self.ck_btn.clicked.connect(self.redeem)
        ck_row.addWidget(self.ck, 1); ck_row.addWidget(self.ck_btn)
        lay.addLayout(ck_row)

        lay.addWidget(CaptionLabel("② 或粘贴完整激活码 / 导入 .lic 文件"))
        self.code = QPlainTextEdit()
        self.code.setPlaceholderText("粘贴 LIC1... 激活码，或点击右侧导入 .lic")
        self.code.setStyleSheet(f"background:{INP};color:{TXT};border:1px solid {LINE};")
        lay.addWidget(self.code, 1)
        brow = QHBoxLayout()
        act = PrimaryPushButton("激 活")
        act.clicked.connect(self.try_activate)
        imp = PushButton("导入 .lic")
        imp.clicked.connect(self.import_file)
        clr = PushButton("清除授权")
        clr.setStyleSheet(f"color:{RED};")
        clr.clicked.connect(self.clear)
        brow.addWidget(act, 2); brow.addWidget(imp); brow.addWidget(clr)
        lay.addLayout(brow)
        self.msg = QLabel(""); self.msg.setStyleSheet(f"color:{RED};")
        lay.addWidget(self.msg)

    def redeem(self):
        k = self.ck.text().strip()
        if len(k) < 10:
            self.msg.setText("请输入完整卡密（KM-XXXX-XXXX-XXXX-XXXX）"); return
        self.ck_btn.setEnabled(False); self.ck_btn.setText("获取中…")
        def work():
            try:
                txt = licensing.redeem_cardkey(k)
                self.code.setPlainText(txt)
                self.root_after(lambda: (self.ck_btn.setEnabled(True),
                                         self.ck_btn.setText("在线获取"),
                                         self.try_activate()))
            except Exception as ex:
                self.root_after(lambda: (self.ck_btn.setEnabled(True),
                                         self.ck_btn.setText("在线获取"),
                                         self.msg.setText(f"获取失败：{ex}")))
        threading.Thread(target=work, daemon=True).start()

    def root_after(self, fn):
        QTimer.singleShot(0, fn)

    def try_activate(self):
        txt = self.code.toPlainText().strip()
        if not txt:
            self.msg.setText("请粘贴激活码或先在线获取"); return
        ok, reason, payload = licensing.verify_text(txt, licensing.device_code())
        if ok:
            licensing.save_license(txt)
            self.accept(); self.on_ok(payload)
        else:
            zh = {"bad_format": "格式错误（可能被聊天软件截断/污染）",
                  "bad_signature": "签名无效（非本软件授权）",
                  "expired": "授权已过期",
                  "hwid_mismatch": "设备码不匹配"}.get(reason, reason)
            self.msg.setText(f"激活失败：{zh}（当前授权未受影响）")

    def import_file(self):
        from PySide6.QtWidgets import QFileDialog
        p, _ = QFileDialog.getOpenFileName(self, "选择授权文件", "",
                                           "授权文件 (*.lic);;全部 (*)")
        if p:
            try:
                self.code.setPlainText(Path(p).read_text(encoding="utf-8"))
                self.try_activate()
            except Exception as ex:
                self.msg.setText(f"读取失败：{ex}")

    def clear(self):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "清除授权",
                                "确定清除本机授权？\n清除后需要新激活码才能使用。") \
                == QMessageBox.Yes:
            licensing.clear_license()
            self.reject(); self.on_ok(None)


# ============ 主窗口 ============
class MainWindow(FramelessMainWindow):
    log_sig = Signal(str)
    frame_sig = Signal(bytes)
    smart_sig = Signal(bool)

    def __init__(self):
        super().__init__()
        licensing.device_code()   # 预热缓存：首次采集约1.4s，必须在窗口显示前付掉
        setTheme(Theme.DARK)
        self.setWindowTitle(f"直播工坊 LiveStudio v{VERSION}")
        self.setMinimumSize(1180, 760)
        # 按可用屏幕自适应并居中：防止右侧按钮/底部状态栏出屏
        _ag = QApplication.primaryScreen().availableGeometry()
        _w = min(1440, _ag.width() - 24)
        _h = min(900, _ag.height() - 24)
        self.resize(_w, _h)
        self.move(max(0, (_ag.width() - _w) // 2),
                  max(0, (_ag.height() - _h) // 2))

        ok, _reason, payload = licensing.check()
        self.customer = payload.get("customer", "") if ok else ""

        self.engine = Engine()
        self.vcam = VirtualCam()
        self.materials = scan_materials()
        self.playing = False
        self.streaming = False
        self._smart_lit = False
        self.logq = queue.Queue()
        self.cfg = load_cfg()

        self._build_ui()
        self._load_cfg()
        self.engine.set_log(self.log_sig.emit)
        self.vcam.log = self.log_sig.emit
        self.log_sig.connect(self._append_log)
        self.frame_sig.connect(lambda b: self.preview.show_png(b))
        self.smart_sig.connect(self.smart.set_active)
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        self._timer.start(400)
        self._carousel_t = QTimer(self); self._carousel_t.timeout.connect(self._carousel)
        self._carousel_t.start(CAROUSEL_SEC * 1000)
        self._fps_t = QTimer(self); self._fps_t.timeout.connect(self._update_stats)
        self._fps_t.start(1000)
        self._pump_frames()

    # ---------- UI ----------
    def _btn(self, text, cmd, primary=False, w=110):
        b = PushButton(text)
        b.clicked.connect(cmd)
        b.setFixedWidth(w)
        if primary:
            b.setStyleSheet("background:#D7A743;color:#17171B;border-radius:8px;"
                            "padding:8px 4px;font-weight:bold;")
        return b

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 44, 14, 10)   # 顶部让出32px无边框标题栏

        top = QHBoxLayout()
        t = SubtitleLabel(f"▶ 直播工坊  LiveStudio v{VERSION}")
        top.addWidget(t); top.addStretch()
        self.act_lbl = QLabel(f"已激活：{self.customer}" if self.customer else "未激活")
        self.act_lbl.setStyleSheet(f"color:{GREEN if self.customer else RED};")
        top.addWidget(self.act_lbl)
        act_btn = PushButton("🔑 激活")
        act_btn.clicked.connect(self.open_activate)
        top.addWidget(act_btn)
        root.addLayout(top)

        body = QHBoxLayout()
        # 左：素材库
        left = QFrame(); left.setStyleSheet(f"background:{CARD};border:1px solid {LINE};"
                                            "border-radius:10px;")
        ll = QVBoxLayout(left)
        ll.addWidget(SubtitleLabel("📁 素材库"))
        self.listw = QListWidget()
        self.listw.setStyleSheet(f"background:{INP};color:{TXT};border:none;"
                                 "outline:none;font-family:Consolas;font-size:13px;")
        self.listw.itemDoubleClicked.connect(lambda _: self.play())
        ll.addWidget(self.listw, 1)
        grid = QHBoxLayout()
        for i, (t2, c) in enumerate([("添加", self.add_files), ("移除", self.remove_sel),
                                     ("清空", self.clear_all), ("扫描", self.scan_dir)]):
            b = self._btn(t2, c, w=64)
            grid.addWidget(b)
            if i % 2:
                ll.addLayout(grid); grid = QHBoxLayout()
        ll.addLayout(grid)
        orow = QHBoxLayout()
        orow.addWidget(self._btn("上移", lambda: self.move_material(-1), w=64))
        orow.addWidget(self._btn("下移", lambda: self.move_material(1), w=64))
        ll.addLayout(orow)
        left.setFixedWidth(300)
        body.addWidget(left)

        # 中：预览 + 走带
        mid = QVBoxLayout()
        self.preview = GLPreview()
        mid.addWidget(self.preview, 1)
        tr = QHBoxLayout()
        self.play_btn = PrimaryPushButton("▶ 预览")
        self.play_btn.clicked.connect(self.toggle_play)
        self.push_btn = PrimaryPushButton("🔴 开始推流")
        self.push_btn.clicked.connect(self.toggle_push)
        self.stop_btn = PushButton("⏹ 全部停止")
        self.stop_btn.clicked.connect(self.stop_all)
        self.car_cb = QCheckBox("自动轮播")
        tr.addWidget(self.play_btn); tr.addWidget(self.push_btn)
        tr.addWidget(self.stop_btn); tr.addStretch(); tr.addWidget(self.car_cb)
        mid.addLayout(tr)
        body.addLayout(mid, 1)

        # 右：可拖拽 Dock 面板
        self.right_dock = QDockWidget("控制面板（可拖拽）", self)
        self.right_dock.setFeatures(QDockWidget.DockWidgetMovable |
                                    QDockWidget.DockWidgetFloatable)
        pages = QStackedWidget()
        self.smart = SmartCard(); pages.addWidget(self.smart)
        self.ov = OverlayCard(self._log)
        self.ov.scanned.connect(self._cams_done)   # 信号槽：GUI线程安全执行
        self.ov.scan_btn.clicked.connect(self.scan_cams)
        self.ov.vcam_sw.checkedChanged.connect(self._toggle_vcam)
        pages.addWidget(self.ov)
        self.env = EnvCard(self._log, None)
        self.env.apply_btn.clicked.connect(self.env_apply)
        self.env.scan_btn.clicked.connect(self.env_scan)
        self.env.clean_btn.clicked.connect(self.env_clean)
        pages.addWidget(self.env)
        tabs = QListWidget(); tabs.setFixedWidth(150)
        tabs.setStyleSheet(f"background:{CARD};color:{TXT};border:none;outline:none;"
                           "font-size:13px;padding:6px;")
        for n in ("✨ 智能处理", "📷 画面叠加", "🌍 环境助手"):
            tabs.addItem(n)
        tabs.currentRowChanged.connect(pages.setCurrentIndex)
        tabs.setCurrentRow(0)
        right_wrap = QWidget(); rw = QHBoxLayout(right_wrap)
        rw.setContentsMargins(0, 0, 0, 0)
        rw.addWidget(tabs); rw.addWidget(pages, 1)
        self.right_dock.setWidget(right_wrap)
        self.addDockWidget(Qt.RightDockWidgetArea, self.right_dock)

        root.addLayout(body, 1)

        # 底部：状态 + 日志 dock
        self.status = QLabel("就绪")
        self.status.setStyleSheet(f"color:{DIM};font-family:Consolas;font-size:12px;")
        root.addWidget(self.status)

        self.log_dock = QDockWidget("📜 日志（可拖拽）", self)
        self.log_dock.setFeatures(QDockWidget.DockWidgetMovable |
                                  QDockWidget.DockWidgetFloatable)
        self.logtxt = QPlainTextEdit()
        self.logtxt.setReadOnly(True)
        self.logtxt.setMaximumHeight(150)
        self.logtxt.setStyleSheet(f"background:{INP};color:{DIM};border:none;"
                                  "font-family:Consolas;font-size:12px;")
        self.log_dock.setWidget(self.logtxt)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.log_dock)

        self.setCentralWidget(central)
        # 关键：后加的 central/dock 会盖住标题栏，必须置顶+定位，否则无法拖动/点击
        self._fix_titlebar()
        self.titleBar.setStyleSheet('background:#0F1115;')
        # 按钮图标默认纯黑(适配浅色标题栏)，深色底上必须改浅色否则隐形
        for _b in (self.titleBar.minBtn, self.titleBar.maxBtn, self.titleBar.closeBtn):
            _b.setNormalColor(QColor('#E7EAF0'))
            _b.setHoverColor(QColor('#FFFFFF'))

    # ---------- 配置 ----------
    def _load_cfg(self):
        c = self.cfg
        mats = [Path(p) for p in c.get("materials", []) if Path(p).exists()]
        if mats:
            self.materials = mats
        self._refresh_list()
        self.car_cb.setChecked(c.get("carousel", False))
        self.ov.vcam_sw.setChecked(c.get("vcam", False))
        self.ov.cam_combo.setCurrentText(c.get("cam", ""))

    def _save_cfg(self):
        save_cfg({"materials": [str(p) for p in self.materials],
                  "carousel": self.car_cb.isChecked(),
                  "vcam": self.ov.vcam_sw.isChecked(),
                  "cam": self.ov.cam_combo.currentText()})

    # ---------- 素材 ----------
    def _refresh_list(self):
        self.listw.clear()
        for p in self.materials:
            self.listw.addItem(p.name)
        if self.materials:
            self.listw.setCurrentRow(0)

    def add_files(self):
        from PySide6.QtWidgets import QFileDialog
        fs, _ = QFileDialog.getOpenFileNames(
            self, "添加素材", "",
            "视频 (*.mp4 *.mov *.mkv *.flv *.ts *.avi *.webm)")
        for f in fs:
            p = Path(f)
            if p not in self.materials:
                self.materials.append(p)
        self._refresh_list(); self._save_cfg()

    def remove_sel(self):
        i = self.listw.currentRow()
        if 0 <= i < len(self.materials):
            del self.materials[i]; self._refresh_list(); self._save_cfg()

    def clear_all(self):
        self.stop_all(); self.materials.clear(); self._refresh_list(); self._save_cfg()

    def scan_dir(self):
        self.materials = scan_materials()
        self._refresh_list(); self._save_cfg()
        self._log(f"[素材] 扫描 → {len(self.materials)} 个")

    def move_material(self, d):
        """素材上移/下移（注意：不可叫 move，会覆盖 QWidget.move）"""
        i = self.listw.currentRow(); j = i + d
        if 0 <= i < len(self.materials) and 0 <= j < len(self.materials):
            self.materials[i], self.materials[j] = self.materials[j], self.materials[i]
            self._refresh_list(); self.listw.setCurrentRow(j); self._save_cfg()

    def current(self):
        i = self.listw.currentRow()
        if 0 <= i < len(self.materials):
            return self.materials[i]
        return self.materials[0] if self.materials else None

    # ---------- 走带 ----------
    def params(self):
        p = dict(SCRIPT_DEFAULTS)
        p["width"], p["height"] = 720, 1280
        p["layer_mode"] = "single"
        return p

    def toggle_play(self):
        self.stop_preview() if self.playing else self.play()

    def play(self):
        m = self.current()
        if not m:
            InfoBar.warning("请先添加素材", parent=self,
                            position=InfoBarPosition.TOP); return
        if self.engine.start_preview(m, self.params(),
                                     cam=self._cam_dev() if self.ov.cam_sw.isChecked() else None):
            self.playing = True
            self.play_btn.setText("⏸ 停止预览")

    def stop_preview(self):
        self.engine.stop_preview()
        self.playing = False
        self.play_btn.setText("▶ 预览")

    def toggle_push(self):
        self.stop_push() if self.streaming else self.push()

    def push(self):
        m = self.current()
        if not m:
            InfoBar.warning("请先添加素材", parent=self,
                            position=InfoBarPosition.TOP); return
        if self.engine.start_push(m, "rtmp://127.0.0.1:1935/tklive", self.params(),
                                  cam=self._cam_dev() if self.ov.cam_sw.isChecked() else None):
            self.streaming = True
            self.push_btn.setText("🔴 停止推流")
            self.smart_sig.emit(True)
            if not self.playing:
                self.play()
            self._save_cfg()

    def stop_push(self):
        self.engine.stop_push()
        self.streaming = False
        self.push_btn.setText("🔴 开始推流")
        self.smart_sig.emit(False)

    def stop_all(self):
        self.stop_push(); self.stop_preview()
        self.vcam.stop(); self.ov.vcam_sw.setChecked(False)
        self.engine.stop_mtx()
        self.status.setText("已停止")

    def _cam_dev(self):
        d = self.ov.cam_combo.currentText()
        return d if d and not d.startswith("先") else None

    # ---------- 虚拟摄像头 ----------
    def _toggle_vcam(self, on):
        if on:
            m = self.current()
            if not m:
                self.ov.vcam_sw.setChecked(False)
                InfoBar.warning("请先添加素材", parent=self,
                                position=InfoBarPosition.TOP); return
            if not self.vcam.start(m, self.params()):
                self.ov.vcam_sw.setChecked(False)
        else:
            self.vcam.stop()

    # ---------- 扫描 ----------
    def scan_cams(self):
        self.ov.scan()

    def _cams_done(self, devs):
        self.ov.scan_btn.setEnabled(True)
        self.ov.scan_btn.setText("扫描设备")
        self.ov.cam_combo.clear()
        if not devs:
            self.ov.cam_combo.addItem("未发现摄像头")
            self._log("[摄像头] 未发现视频设备"); return
        self.ov.cam_combo.addItems(devs)
        self._log(f"[摄像头] 发现 {len(devs)} 个: {', '.join(devs)}")

    # ---------- 环境助手 ----------
    def env_apply(self):
        name = self.env.city.currentText()
        def work():
            envassist.apply_region(name, self._log)
            self.env.info.setText(envassist.scan())
        self._log(f"[环境] 应用 {name} …")
        threading.Thread(target=work, daemon=True).start()

    def env_scan(self):
        def work():
            s = envassist.scan()
            h = envassist.hardware_scan()
            envassist.clean_scan(self._log)
            self.root_after(lambda: self.env.info.setText(f"{s}\n{h.replace(chr(10), '  ')}"))
        threading.Thread(target=work, daemon=True).start()

    def env_clean(self):
        threading.Thread(target=lambda: envassist.clean_purge(self._log),
                         daemon=True).start()

    # ---------- 激活 ----------
    def open_activate(self):
        dlg = ActivateDialog(self, self._activated)
        dlg.exec()

    def _activated(self, payload):
        if payload is None:
            self.act_lbl.setText("未激活")
            self.act_lbl.setStyleSheet(f"color:{RED};")
            self._log("[激活] 已清除本机授权")
        else:
            self.customer = payload.get("customer", "")
            self.act_lbl.setText(f"已激活：{self.customer}")
            self.act_lbl.setStyleSheet(f"color:{GREEN};")
            self._log(f"[激活] 授权已更新：{self.customer} "
                      f"(有效期 {payload.get('expires') or '永久'})")

    # ---------- 循环/统计/日志 ----------
    def _tick(self):
        if self.playing or self.streaming:
            self.smart.set_active(True)
        else:
            self.smart.set_active(False)

    def _pump_frames(self):
        def loop():
            while True:
                pv = self.engine.preview
                fb = pv.next_frame() if pv else None
                if fb:
                    self.frame_sig.emit(fb)
                else:
                    time.sleep(0.06)
        threading.Thread(target=loop, daemon=True).start()

    def _update_stats(self):
        st = self.engine.stats
        if self.streaming and st["speed"] is not None:
            self.status.setText(
                f"● 推流中  speed={st['speed']}x  frame={st['frame']}  "
                f"bitrate={st['bitrate']}kbps  720x1280 → rtmp://127.0.0.1:1935/tklive"
                + ("  | 虚拟摄像头 ON" if self.vcam.running else ""))
            self.status.setStyleSheet(f"color:{GREEN};font-family:Consolas;font-size:12px;")
        elif self.streaming:
            self.status.setText("● 启动中…")
            self.status.setStyleSheet(f"color:{GOLD};font-family:Consolas;font-size:12px;")
        elif self.playing:
            self.status.setText("● 预览中")
            self.status.setStyleSheet(f"color:{BLUE};font-family:Consolas;font-size:12px;")
        else:
            self.status.setText(
                f"素材 {len(self.materials)} 个 · 设备码 {licensing.device_code()}")
            self.status.setStyleSheet(f"color:{DIM};font-family:Consolas;font-size:12px;")

    def _carousel(self):
        if not (self.car_cb.isChecked() and (self.streaming or self.playing)) \
                or len(self.materials) < 2:
            return
        i = self.listw.currentRow()
        self.listw.setCurrentRow((i + 1) % len(self.materials))
        self._log(f"[轮播] 切换 → {self.current().name}")
        if self.playing:
            self.stop_preview()
        if self.streaming:
            self.engine.stop_push(); self.streaming = False
            self.push_btn.setText("🔴 开始推流")
            self.push()
        else:
            self.play()

    def _log(self, line):
        self.logq.put(line)

    def _append_log(self, line):
        self.logtxt.appendPlainText(line)

    def root_after(self, fn):
        QTimer.singleShot(0, fn)

    def _fix_titlebar(self):
        """无边框窗默认标题栏：铺满顶部并置顶（否则被主内容遮住，拖不动点不了）"""
        tb = getattr(self, "titleBar", None)
        if tb is None:
            return
        tb.move(0, 0)
        tb.resize(self.width(), 32)
        tb.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fix_titlebar()

    def showEvent(self, e):
        super().showEvent(e)
        self._fix_titlebar()

    def closeEvent(self, e):
        self.stop_all()
        self._save_cfg()
        super().closeEvent(e)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    f = QFont("Microsoft YaHei UI", 9); app.setFont(f)

    ok, _r, payload = licensing.import_sibling_license()
    if not ok:
        win = MainWindow()          # 主窗先建（未激活状态）
        dlg = ActivateDialog(win, win._activated)
        if dlg.exec() != QDialog.Accepted and not licensing.check()[0]:
            return
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
