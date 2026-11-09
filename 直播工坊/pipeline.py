# -*- coding: utf-8 -*-
"""
直播工坊 · 推流引擎 v1.1
底层 = 自有去重管线（2026.10.03 txt 脚本参数化）
v1.1 新增（对齐 LuBot 功能面）：
  - 图层模式：单素材 / 背景合成(平移) / 跑马灯
  - 音频降重中族：变调(pitch) / 低音(bass) / 高音(treble) / 音漂移 / 音量
  - 真实摄像头 5% 叠加（dshow 采集 + blend，透明度可调）
  - 中继双输出（同一编码流 tee 到本地+远端两个 RTMP）
  - 预览与推流同图（canvas/跑马灯模式预览所见即所得）
"""
import re
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

# 工具链位置：打包版用 exe 旁的 runtime\ 目录；开发版沿用桌面整合目录
if getattr(sys, "frozen", False):
    BUNDLE_DIR = Path(sys.executable).resolve().parent
    TOOL_ROOT = BUNDLE_DIR / "runtime"
    FFMPEG_DIR = TOOL_ROOT
    MTX_DIR = TOOL_ROOT
else:
    BUNDLE_DIR = Path(__file__).resolve().parent
    TOOL_ROOT = Path(r"C:\Users\16575\Desktop\TK奥德彪直播工具") / "FFmpeg完整版含MTX"
    FFMPEG_DIR = TOOL_ROOT / "ffmpeg-9.0.2-full_build" / "bin"
    MTX_DIR = TOOL_ROOT / "Mediamtx"
FFMPEG_EXE = FFMPEG_DIR / "ffmpeg.exe"
FFPROBE_EXE = FFMPEG_DIR / "ffprobe.exe"
MTX_EXE = MTX_DIR / "mediamtx.exe"
MTX_YML = MTX_DIR / "mediamtx.yml"
MATERIAL_DIR = Path(r"E:\jianhaodesucai")
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".flv", ".ts", ".avi", ".webm"}

LAYER_SINGLE, LAYER_CANVAS, LAYER_MARQUEE = "single", "canvas", "marquee"

# ==== txt 管线原版参数（2026.10.03最终版）+ v1.1 扩展 ====
SCRIPT_DEFAULTS = {
    # 去重（视频）
    "noise": 1.8, "scale_amp": 0.0012, "rot_amp": 0.00215, "crop_drift": 1.6,
    "eq_bright": 0.003, "eq_contrast": 0.0045, "hue_amp": 0.08, "setpts_jitter": 0.0015,
    # 去重（音频）
    "vol_amp": 0.006, "tempo_amp": 0.0008,
    "pitch_ratio": 1.0, "bass": 0.0, "treble": 0.0,
    # 输出
    "bitrate": 4000, "width": 720, "height": 1280, "preset": "fast",
    # 图层
    "layer_mode": LAYER_SINGLE, "pan_speed": 12.0,
    "marquee_speed": 40.0, "marquee_h": 0.28,
    # 摄像头
    "realcam_opacity": 0.05,
}


def scan_materials(directory: Path = MATERIAL_DIR):
    if not directory.exists():
        return []
    return sorted(p for p in directory.iterdir()
                  if p.suffix.lower() in VIDEO_EXTS and p.is_file())


def list_cameras() -> list:
    """枚举本机 dshow 视频设备（字节级容错解码，防 GBK/UTF-8 混杂炸线程）。"""
    try:
        r = subprocess.run(
            [str(FFMPEG_EXE), "-hide_banner", "-f", "dshow", "-list_devices", "true", "-i", "dummy"],
            capture_output=True, timeout=10, creationflags=CREATE_NO_WINDOW)
        raw = r.stderr or b""
        try:
            err = raw.decode("gbk")          # 中文 Windows 系统码页优先
        except UnicodeDecodeError:
            err = raw.decode("utf-8", "replace")
        return [m.group(1) for m in
                re.finditer(r'"(.+?)"\s*\(video\)', err)]
    except Exception:
        return []


def _g(x) -> str:
    return f"{float(x):.6g}"


def build_diff_body(p: dict, w: int, h: int) -> str:
    """去重抖动链主体（无输入标签）。与 txt 脚本逐参数对应。"""
    sa, ra, cd = _g(p["scale_amp"]), _g(p["rot_amp"]), _g(p["crop_drift"])
    return (
        f"noise=alls={_g(p['noise'])}:allf=t,"
        f"scale=eval=frame:w='iw*(1+{sa}*sin(2*PI*t/3.8)+{_g(p['scale_amp']/4)}*random(1))'"
        f":h='ih*(1+{sa}*sin(2*PI*t/3.8)+{_g(p['scale_amp']/4)}*random(1))',"
        f"rotate='{ra}*sin(2*PI*t/6.7)+{_g(p['rot_amp']/3.6)}*random(1)':ow=iw:oh=ih,"
        f"crop=iw:ih:x='{cd}*sin(2*PI*t/4.2)+{_g(p['crop_drift']/4)}*random(1)'"
        f":y='{cd}*cos(2*PI*t/5.5)+{_g(p['crop_drift']/4)}*random(1)',"
        f"scale={w}:{h},"
        f"eq=brightness='{_g(p['eq_bright'])}*sin(2*PI*t/8.2)+{_g(p['eq_bright']*0.4)}*random(1)'"
        f":contrast='1+{_g(p['eq_contrast'])}*sin(2*PI*t/10.3)+{_g(p['eq_contrast']*0.55)}*random(1)',"
        f"hue=h='{_g(p['hue_amp'])}*sin(2*PI*t/12.1)+{_g(p['hue_amp']*0.375)}*random(1)',"
        f"setpts=PTS+{_g(p['setpts_jitter'])}*random(2)"
    )


def build_audio(p: dict) -> str:
    """音频链：降噪→变调(变速补偿)→随机音量→随机声速→低/高音。"""
    r = float(p.get("pitch_ratio", 1.0))
    parts = ["afftdn=nf=-60"]
    if abs(r - 1.0) > 1e-6:
        parts += [f"asetrate=44100*{_g(r)}", "aresample=44100", f"atempo={_g(1/r)}"]
    parts += [f"volume='1+{_g(p['vol_amp'])}*random(2)'",
              f"atempo='1+{_g(p['tempo_amp'])}*random(2)'"]
    b, t = float(p.get("bass", 0.0)), float(p.get("treble", 0.0))
    if abs(b) > 1e-6:
        parts.append(f"bass=g={_g(b)}")
    if abs(t) > 1e-6:
        parts.append(f"treble=g={_g(t)}")
    return ",".join(parts)


def build_video_graph(p: dict, w: int, h: int, has_bg: bool) -> str:
    """构造视频滤镜图，末端标签 [vpre]。"""
    mode = p.get("layer_mode", LAYER_SINGLE)
    diff = build_diff_body(p, w, h)
    if mode == LAYER_SINGLE or not has_bg:
        return f"[0:v]{diff}[vpre]"
    if mode == LAYER_CANVAS:
        bw, bh = int(w * 1.5), int(h * 1.5)
        spd = _g(p["pan_speed"])
        return (
            f"[0:v]fps=30,scale={w}:{h}:force_original_aspect_ratio=decrease,setsar=1[mc]"
            f";[1:v]scale={bw}:{bh}:force_original_aspect_ratio=increase,setsar=1[bgbig]"
            f";[bgbig]crop={w}:{h}:x='mod(t*{spd},{bw - w})':y='mod(t*{_g(p['pan_speed']*0.6)},{bh - h})'[bg]"
            f";[bg][mc]overlay=(W-w)/2:(H-h)/2:format=auto[comp]"
            f";[comp]{diff}[vpre]"
        )
    # marquee
    mh = max(48, int(h * float(p.get("marquee_h", 0.28))))
    spd = _g(p["marquee_speed"])
    y = int(h * 0.04)
    return (
        f"[0:v]split=2[m0][m1]"
        f";[m1]scale=-2:{mh},setsar=1[sq]"
        f";[m0]fps=30,scale={w}:{h}:force_original_aspect_ratio=increase,setsar=1[bg]"
        f";[bg][sq]overlay=x='mod(t*{spd},{w}+w)-w':y={y}:format=auto[comp]"
        f";[comp]{diff}[vpre]"
    )


def _inputs(material: Path, p: dict, bg, cam) -> tuple:
    """返回 (argv输入段, bg是否启用, 摄像头输入序号)。"""
    argv = ["-re", "-stream_loop", "-1", "-i", str(material)]
    need_bg = (p.get("layer_mode", LAYER_SINGLE) != LAYER_SINGLE) and bg is not None
    if need_bg:
        argv += ["-re", "-stream_loop", "-1", "-i", str(bg)]
    cam_idx = None
    if cam:
        cam_idx = 1 if need_bg else 0
        argv += ["-f", "dshow", "-framerate", "30", "-i", f"video={cam}"]
    return argv, need_bg, cam_idx


def _finalize_graph(fc: str, p: dict, w: int, h: int, cam_idx) -> tuple:
    """按需叠加摄像头 blend，返回 (fc, 最终标签)。"""
    if cam_idx is None:
        return fc.replace("[vpre]", "[vout]"), "[vout]"
    op = _g(p.get("realcam_opacity", 0.05))
    fc += (f";[{cam_idx}:v]scale={w}:{h},setsar=1[cams]"
           f";[cams][vpre]blend=all_mode=average:all_opacity={op}[vout]")
    return fc, "[vout]"


def build_push_argv(material, target_url, p, bg=None, cam=None, preset=None) -> list:
    """主推流命令（单目标）。"""
    w, h = p["width"], p["height"]
    argv = [str(FFMPEG_EXE), "-hide_banner"]
    ins, need_bg, cam_idx = _inputs(material, p, bg, cam)
    argv += ins
    fc = build_video_graph(p, w, h, need_bg)
    fc, out_label = _finalize_graph(fc, p, w, h, cam_idx)
    argv += ["-filter_complex", fc]
    br = p["bitrate"]
    tail = ["-map", out_label, "-map", "0:a?",
            "-c:v", "libx264", "-preset", preset or p["preset"],
            "-b:v", f"{br}k", "-maxrate", f"{int(br*1.15)}k", "-minrate", f"{int(br*0.85)}k",
            "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.1",
            "-x264-params", "keyint=120:min-keyint=12:scenecut=15:bframes=2",
            "-filter:a", build_audio(p),
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
            "-f", "flv", target_url]
    argv += tail
    return argv


def build_preview_argv(material, p, bg=None, cam=None, pw=240, fps=10) -> list:
    """预览命令：与推流同图，低分辨率 PNG 帧流。"""
    w, h = p["width"], p["height"]
    ph = max(2, int(pw * h / w / 2) * 2)
    argv = [str(FFMPEG_EXE), "-hide_banner"]
    ins, need_bg, cam_idx = _inputs(material, p, bg, cam)
    argv += ins
    fc = build_video_graph(p, pw, ph, need_bg)
    fc, out_label = _finalize_graph(fc, p, pw, ph, cam_idx)
    fc += f";{out_label}fps={fps}[pv]"
    argv += ["-filter_complex", fc, "-map", "[pv]", "-an",
             "-f", "image2pipe", "-vcodec", "png", "pipe:1"]
    return argv


VCAM_NAME = "LiveStudio Cam"


def build_rawvideo_argv(material, p, w=1080, h=1920, fps=30) -> list:
    """虚拟摄像头帧流：720x1280@30 bgr24 rawvideo（喂 DirectShow 虚拟摄像头）。"""
    argv = [str(FFMPEG_EXE), "-hide_banner", "-re", "-stream_loop", "-1",
            "-i", str(material), "-an"]
    fc = build_video_graph(p, w, h, False)
    fc, out_label = _finalize_graph(fc, p, w, h, None)
    fc += f";{out_label}fps={fps}[pv]"
    argv += ["-filter_complex", fc, "-map", "[pv]",
             "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1"]
    return argv


class VirtualCam:
    """内置虚拟摄像头：ffmpeg 出帧 → pyvirtualcam(UnityCapture) → 开播平台可选设备。"""
    def __init__(self, log=None):
        self.log = log or (lambda s: None)
        self._proc = None
        self._cam = None
        self._run = False

    @property
    def running(self) -> bool:
        return self._run

    def start(self, material, params) -> bool:
        if self._run:
            return True
        try:
            import pyvirtualcam
            self._cam = pyvirtualcam.Camera(width=1080, height=1920, fps=30,
                                            backend="unitycapture")
        except Exception as ex:
            self.log(f"[虚拟摄像头] 驱动未就绪：{ex}（请确认安装时保留了驱动）")
            return False
        cmd = build_rawvideo_argv(material, params)
        try:
            self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                          stderr=subprocess.DEVNULL,
                                          stdin=subprocess.DEVNULL,
                                          creationflags=CREATE_NO_WINDOW)
        except Exception as ex:
            self.log(f"[虚拟摄像头] 启动失败：{ex}")
            self._cam.close(); self._cam = None
            return False
        self._run = True
        self.log(f"[虚拟摄像头] 已开启 → 设备「{VCAM_NAME}」，开播平台选此摄像头即可")
        threading.Thread(target=self._loop, daemon=True).start()
        return True

    def _loop(self):
        import numpy as np
        n = 1080 * 1920 * 3
        while self._run:
            if not self._proc or self._proc.poll() is not None:
                break
            buf = self._proc.stdout.read(n)
            if not buf or len(buf) < n:
                break
            frame = np.frombuffer(buf, dtype=np.uint8).reshape(1920, 1080, 3)
            try:
                self._cam.send(frame)
                self._cam.sleep_until_next_frame()
            except Exception:
                break
        self.stop()

    def stop(self):
        self._run = False
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
        if self._cam:
            try:
                self._cam.close()
            except Exception:
                pass
            self._cam = None
            self.log("[虚拟摄像头] 已关闭")


class PngReader:
    """解析 ffmpeg image2pipe 的 PNG 帧流（chunk 级走到 IEND）。"""
    def __init__(self, proc: subprocess.Popen):
        self.proc = proc
        self.buf = b""
        self.lock = threading.Lock()
        self.alive = True
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        try:
            while self.alive:
                chunk = self.proc.stdout.read(65536)
                if not chunk:
                    break
                with self.lock:
                    self.buf += chunk
        except Exception:
            pass

    def next_frame(self):
        """返回完整 PNG bytes 或 None。"""
        with self.lock:
            if not self.buf:
                return None
            idx = self.buf.find(b"\x89PNG")
            if idx < 0:
                self.buf = b""
                return None
            if idx > 0:
                self.buf = self.buf[idx:]
            pos = 8
            while True:
                if len(self.buf) < pos + 8:
                    return None
                ln = int.from_bytes(self.buf[pos:pos + 4], "big")
                typ = self.buf[pos + 4:pos + 8]
                end = pos + 12 + ln
                if len(self.buf) < end:
                    return None
                pos = end
                if typ == b"IEND":
                    frame = self.buf[:pos]
                    self.buf = self.buf[pos:]
                    return frame


class Engine:
    """推流/预览/服务器 三合一进程管理器。"""

    def __init__(self):
        self.push_proc: subprocess.Popen | None = None
        self.relay_proc: subprocess.Popen | None = None
        self.preview: PngReader | None = None
        self.preview_proc: subprocess.Popen | None = None
        self.mtx_proc: subprocess.Popen | None = None
        self._log_cb = None
        self._speed = None
        self._frame = None
        self._bitrate = None
        self.stats_lock = threading.Lock()

    # ---- 日志与统计 ----
    def set_log(self, cb):
        self._log_cb = cb

    def _log(self, line):
        if self._log_cb:
            self._log_cb(line)

    @property
    def stats(self):
        with self.stats_lock:
            return {"speed": self._speed, "frame": self._frame, "bitrate": self._bitrate}

    def _watch_push(self, proc, tag="推流"):
        tail = b""
        speed_re = re.compile(rb"speed=\s*([\d.]+)x")
        frame_re = re.compile(rb"frame=\s*(\d+)")
        br_re = re.compile(rb"bitrate=\s*([\d.]+)kbits")
        while True:
            b = proc.stdout.read(1)
            if not b:
                break
            if b in (b"\r", b"\n"):
                line = tail.decode("utf-8", "replace").strip()
                tail = b""
                if line:
                    if tag != "推流":
                        line = f"[{tag}] {line}"
                    self._log(line)
                    if tag == "推流":
                        m = speed_re.search(line.encode())
                        if m:
                            with self.stats_lock:
                                self._speed = float(m.group(1))
                        m = frame_re.search(line.encode())
                        if m:
                            with self.stats_lock:
                                self._frame = int(m.group(1))
                        m = br_re.search(line.encode())
                        if m:
                            with self.stats_lock:
                                self._bitrate = float(m.group(1))
            else:
                tail += b
                if len(tail) > 4096:
                    tail = tail[-2048:]

    # ---- MediaMTX ----
    def mtx_running(self) -> bool:
        with socket.socket() as s:
            s.settimeout(0.4)
            return s.connect_ex(("127.0.0.1", 1935)) == 0

    def start_mtx(self) -> bool:
        if self.mtx_running():
            self._log("[服务器] 1935 已有服务在监听（跳过启动）")
            return True
        if not MTX_EXE.exists():
            self._log(f"[服务器] 未找到 {MTX_EXE}")
            return False
        self.mtx_proc = subprocess.Popen(
            [str(MTX_EXE), str(MTX_YML.name)],
            cwd=str(MTX_DIR), stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        for _ in range(30):
            if self.mtx_running():
                self._log("[服务器] MediaMTX 已启动 (RTMP:1935)")
                return True
            time.sleep(0.3)
        self._log("[服务器] 启动超时")
        return False

    def stop_mtx(self):
        if self.mtx_proc and self.mtx_proc.poll() is None:
            self.mtx_proc.terminate()
            self._log("[服务器] 已停止")
        self.mtx_proc = None

    # ---- 推流 ----
    def _watch_death(self, proc, tag, cam=None):
        """启动 3 秒内死亡 → 日志给出可读原因（主要是摄像头被占用）。"""
        time.sleep(3)
        if proc.poll() is not None:
            if cam:
                self._log(f"[{tag}] ✗ 摄像头 '{cam}' 打开失败——可能被微信/会议/其他直播软件占用，"
                          "请关闭占用程序后重新启用摄像头")
            else:
                self._log(f"[{tag}] ✗ 进程启动后立即退出，请检查素材/地址/参数")

    def start_push(self, material, url, params, bg=None, cam=None, relay_url="") -> bool:
        if self.push_proc and self.push_proc.poll() is None:
            self._log("[推流] 已在运行")
            return False
        cmd = build_push_argv(material, url, params, bg=bg, cam=cam)
        self._log("[推流] $ " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
        self.push_proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        threading.Thread(target=self._watch_push, args=(self.push_proc,),
                         daemon=True).start()
        threading.Thread(target=self._watch_death, args=(self.push_proc, "推流", cam),
                         daemon=True).start()
        if relay_url:
            rcmd = build_push_argv(material, relay_url, params, bg=bg, cam=cam,
                                   preset="ultrafast")
            self._log(f"[中继] 转推 → {relay_url}（ultrafast 独立进程）")
            self.relay_proc = subprocess.Popen(
                rcmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
            threading.Thread(target=self._watch_push,
                             args=(self.relay_proc, "中继"), daemon=True).start()
        return True

    def stop_push(self):
        for proc, name in ((self.relay_proc, "中继"), (self.push_proc, "推流")):
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except Exception:
                    proc.kill()
                self._log(f"[{name}] 已停止")
        self.push_proc = None
        self.relay_proc = None
        with self.stats_lock:
            self._speed = self._frame = self._bitrate = None

    def push_alive(self) -> bool:
        return bool(self.push_proc and self.push_proc.poll() is None)

    # ---- 预览 ----
    def start_preview(self, material, params, bg=None, cam=None) -> bool:
        self.stop_preview()
        cmd = build_preview_argv(material, params, bg=bg, cam=cam)
        try:
            self.preview_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        except Exception as e:
            self._log(f"[预览] 启动失败: {e}")
            return False
        self.preview = PngReader(self.preview_proc)
        threading.Thread(target=self._watch_death,
                         args=(self.preview_proc, "预览", cam), daemon=True).start()
        return True

    def stop_preview(self):
        if self.preview_proc and self.preview_proc.poll() is None:
            self.preview_proc.terminate()
        self.preview_proc = None
        self.preview = None
