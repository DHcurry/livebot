# tkcore.exe 架构读取报告（REA 逆向）

> 日期：2026-10-22 ｜ 工具：REA 6.7.0 CLI + Ghidra 12.1（快照复用）
> 目标：`C:\Program Files\LuBot\core\tkcore.exe`（PE x86_64，SHA256 `69dde4a6…00b96`，5153 过程 / 3266 字符串）
> 范围：**仅功能层**。授权/卡密模块按既定边界只记录存在、不做分析。

---

## 一、整体架构（六层）

```
┌────────────────────────────────────────────────────────┐
│ LuBot.exe（127KB 启动器）                                │
│   CreateProcessW 拉起 core\tkcore.exe → WaitForSingleObject │
├────────────────────────────────────────────────────────┤
│ tkcore.exe（4.7MB，Qt6 Widgets 单体内核）                │
│                                                          │
│  ① UI层  MainWindow（20个槽）│StreamPushDialog│          │
│          ProcessingOverlay│TutorialDialog│深色QSS主题     │
│  ② 素材层 playClips/probeAndAdd/restoreMaterialLibrary/  │
│          clipChanged/autoPlay/素材库持久化                │
│  ③ 管线层 ffmpeg 命令行构建器（防重滤镜，CUDA/CPU双路径）  │
│  ④ 进程层 QProcess：ffmpeg.exe / ffprobe.exe / mediamtx.exe│
│  ⑤ 推流层 MediaMTX 自动生成配置+自启动（relay 中继体系）   │
│  ⑥ 虚拟摄像头 TK Cam（rawvideo bgr24 → LuBotCam.dll）     │
│                                                          │
│  （另有授权事件服务 /v2/events —— 边界外，不展开）         │
├────────────────────────────────────────────────────────┤
│ 外部运行时（自动探测目录）：                               │
│   ffmpeg|ffplay|mediamtx|softcam|rawvideo                │
│   /ffmpeg/ffmpeg.exe│/FFmpeg/bin/ffmpeg.exe│/Mediamtx/... │
└────────────────────────────────────────────────────────┘
```

导入表佐证：QT6WIDGETS(815) / QT6CORE(564) / QT6GUI(156) / QT6NETWORK(41) /
KERNEL32(40) / BCRYPT(9) / WINMM(8)。纯 Qt6 原生 C++，无 Web 前端框架。

---

## 二、UI 层：MainWindow 槽全表（Qt 元对象 @0x14010af38）

```
素材: onAddMaterial │ onRemoveMaterial │ onClearMaterials │ onMoveUp │ onMoveDown
播放: onStart │ onStop │ autoPlay(QString) │ playClips() │ playbackFinished │ clipChanged
画面: onToggleVirtualCamera │ onOpenPreviewWindow │ onLayerOrderChanged
推流: onRelayToggled │ onCopyRelayUrl │ onRelayRestart │ onToggleDirectStream
设置: onSettingsChanged │ onAudioDiffToggled │ onToggleLog │ onActivate
其他: onAbout │ onCheckForUpdates │ TutorialDialog
后台: restoreMaterialLibrary │ autoScreenSwitchTest │ autoRecommendOnFirstRun
```

控件体系（QSS 命名）：`#Primary #Secondary #Ghost #WinBtn #WinBtnClose
#ThemePicker #ToolLink #ProgressPlay #ProgressStop #BadgeBtn` + `stageAction`
属性——完整的组件化按钮体系，金色高亮 `#D7A743` + 深蓝 `#172033` 主题。

---

## 三、管线层（核心 @0x140040a49，84KB 伪代码）

一个巨型滤镜图构建器，**双路径**：

### CUDA 路径（`hwupload_cuda` / `overlay_cuda`，GPU 合成）
| 节点 | 模板（字面量 @地址） |
|---|---|
| 画布 | `color=c=black:s=%1x%2:r=%3,format=yuv420p,hwupload_cuda[cvs]` |
| 素材归一 | `[0:v]fps=%1,scale=%2:%3:…increase,crop,setsar=1,%4format=yuv420p,hwupload_cuda[mc]` |
| 多素材 | `[%1:v]fps…[v%1]` + `concat=n=%1:v=1:a=0[vcat];[vcat]…hwupload_cuda[mc]` |
| 背景上传 | `[%1:v]format=yuv420p,hwupload_cuda[bgc]` |
| 滚动背景 | `[cvs][bgc]overlay_cuda=x='-mod(t*%1,%2)':y='-mod(t*%3,%4)'[c1]` |
| 素材上画布 | `[%1][mc]overlay_cuda=x=%2:y=%3[c2]` |
| 下载回CPU | `[c2]hwdownload,format=yuv420p[cmp]` |

### CPU 路径（无 CUDA 时的回退/叠加）
| 节点 | 模板 |
|---|---|
| 透明衬垫 | `fps,scale…decrease,format=rgba,pad=%4:%5:(ow-iw)/2:(oh-ih)/2:color=black@0,setsar=1` |
| 背景平移 | `[bgbig]crop=%1:%2:x='mod(t*%3,%4)':y='mod(t*%5,%6)'[bg]` |
| 居中合成 | `[bg][%1]overlay=(W-w)/2:(H-h)/2:format=auto[withbg]` |
| 跑马灯 | `[bg][sq]overlay=x='mod(t*%1,%2)':y=%3:format=auto[mix]` |

### 防重特性（配置键族，Qt 设置）
- 视频：`diff.noise.enabled/strength`、`diff.rotate.enabled/amount`、
  `diff.topScroll.opacity`（滤镜模板 `noise=alls=%1:allf=%2`、`rotate=a='%1':c=black…`）
- 音频：`audio.diff.enabled`、`audio.diff.drift.enabled/amount`、
  `audio.diff.eq.enabled/bass/treble`、`audio.diff.pitch.enabled/ratio`

> 结论：LuBot 的 CUDA 链负责"动态背景+跑马灯+素材合成"，
> 我们 wrapper v3 注入的 txt 链负责"全局微抖动降重"——**互补而非冲突**，
> wrapper 丢弃原生 CUDA 链改走 txt 的取舍此前已实测（medium 档 0.82x 会积延迟）。

---

## 四、进程与推流层

- **运行时探测**（多候选回退）：`/ffmpeg/ffmpeg.exe` → `/FFmpeg/bin/ffmpeg.exe` → …
  `|ffmpeg|ffplay|mediamtx|softcam|rawvideo`；协议白名单 `rtmp://|http://|https://|tcp://|udp://`
- **MediaMTX 自管理**（@0x140050ae8）：生成 `/mediamtx-lubot.yml`
  （`rtmp: true`、`rtmpEncryption: "no"`、`rtmpAddress: %1:%2`）→ 拉起 mediamtx.exe；
  失败提示 `MediaMTX 启动失败：%1`。支持 ` RTMP:%1 RTSP:%2 HLS:%3` 多协议地址展示。
- **推流地址**：默认 `rtmp://127.0.0.1:1935/lubot`（内部）/ `rtmp://127.0.0.1:1935/live`
  （推流对话框）；`relay.rtmpUrl` 中继可配置；分辨率预设 1080x1920/1920x1080/720x1280/1280x720。
- **日志**：`/logs/ffmpeg-last.log`，前缀 `[Pipeline]`、`[Pipeline] ffmpeg`。
- **环境管理内建**：`lubot env --apply --region=%1`、`lubot env clean --scan|--selected|--tier=basic`
  （PowerShell 内嵌——与我们自研 `环境配置.bat` 能力重叠，可考虑让位给原生）。
- **崩溃转储**：`/LuBot-%1.dmp`；调试开关 `LUBOT_ENV_DRYRUN`、`LUBOT_CRASH_TEST`。

## 五、虚拟摄像头层

- 设备名字符串 `TK Cam`；模块 `/LuBotCam.dll`、`/cam/`；
  命令行 `--install-cam` / `--uninstall-cam`。
- 管线末端 `bgr24`（两处）→ 与 rawvideo 输出约定一致：
  **1080×1920 bgr24 喂 TK Cam**，印证我们 wrapper v3 分支B的格式选择正确。

## 六、边界声明

0x140034194 处存在本地 HTTP SSE 服务（`text/event-stream`，路由 `/v2/events`，
字段 device_hash / license_id / lease / oem_id / event_generation）——属授权子系统，
**按既定边界仅记录存在，未做任何深入分析**（BCRYPT/CRYPT32 导入同理）。

---

## 七、未知与局限

1. 无 PDB 符号，内部函数均为 `FUN_xxx`；类归属来自 RTTI/Qt 元对象字符串 + 字符串交叉引用，属**高置信推断**而非编译期事实。
2. 未反编译 playClips 本体（管线调用序列细节，如输入列表如何拼装），需要时可继续（快照已持久化，约 2 分钟/函数）。
3. 虚拟摄像头与 tkcore 的进程内通信细节（LuBotCam.dll 加载方式）未展开。
4. SSE 授权服务内部逻辑（边界外）。

## 八、证据索引

| 内容 | 证据 |
|---|---|
| 总览（段/计数） | `ev_e9cdc53f7a6c…` / `rea-snapshots\inspect.json` |
| 全过程清单 | `rea-snapshots\procs.json`（5153 项） |
| 功能字符串+地址 | `rea-snapshots\strings.json`（97 项） |
| xrefs 滤镜/MTX/SSE | `xref_filter.json` / `xref_mtxyml.json`（`ev_64612e15…`）/ `xref_sse.json` |
| 反编译 | `de_pipeline.md`（84KB）/ `de_mtxcfg.md` / `de_sse.md` |
| Ghidra 快照 | `rea-snapshots\tkcore`（复用免重复导入） |
