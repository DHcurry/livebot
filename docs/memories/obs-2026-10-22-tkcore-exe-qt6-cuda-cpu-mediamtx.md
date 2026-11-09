---
type: source
title: "Observation: tkcore.exe 架构读取完成：Qt6六层结构+CUDA/CPU双管线+MediaMTX自管理"
tags:
  - rea
  - ghidra
  - tkcore
  - 逆向
  - 架构
  - luBot
status: observation
created: 2026-10-22
updated: 2026-10-22
slug: obs-2026-10-22-tkcore-exe-qt6-cuda-cpu-mediamtx
relevance: high
observed_at: 2026-10-22T11:10:00.202Z
source_context: REA 读取 tkcore.exe 功能层架构
---

# ⭐ Observation: tkcore.exe 架构读取完成：Qt6六层结构+CUDA/CPU双管线+MediaMTX自管理

tkcore.exe (TK奥德彪 v2.1.2 内核) 功能层架构已用 REA+Ghidra 12.1 完整读取（2026-10-22），报告在 Desktop\TK奥德彪直播工具\tkcore架构读取报告.md。架构：LuBot.exe(127KB启动器,CreateProcessW)→tkcore.exe(Qt6 Widgets, 5153函数)。六层：UI(MainWindow 20槽: onAddMaterial/onToggleVirtualCamera/onRelayToggled/onAudioDiffToggled等+StreamPushDialog/ProcessingOverlay/QSS主题)、素材(playClips/probeAndAdd/restoreMaterialLibrary)、管线构建器@0x140040a49(CUDA路径: color画布+hwupload_cuda+overlay_cuda滚动背景+concat多素材; CPU路径: rgba pad+crop平移+overlay居中+跑马灯)、进程层(QProcess ffmpeg/ffprobe/mediamtx, 目录多候选探测)、推流(MediaMTX自生成mediamtx-lubot.yml自启动, 默认rtmp://127.0.0.1:1935/lubot, relay.rtmpUrl中继)、虚拟摄像头(TK Cam, bgr24 rawvideo, /LuBotCam.dll)。防重配置族: diff.noise/rotate/topScroll + audio.diff.drift/eq/pitch。内建 lubot env 区域环境命令(与自研环境配置.bat重叠)。授权: /v2/events SSE服务(device_hash/license_id/lease)——按边界未深入。方法坑: pi进程早于setx启动导致MCP拿不到GHIDRA_INSTALL_DIR，用rea CLI内export绕过；--snapshot持久化快照免重复Ghidra导入(~2分钟/次)。wrapper v3 与原生CUDA链互补关系获静态证实，TK Cam bgr24 约定获证实。

*Relevance: high*
*Context: REA 读取 tkcore.exe 功能层架构*
*Tags: rea ghidra tkcore 逆向 架构 luBot*

---
*Observed: 2026-10-22T11:10:00.202Z*
