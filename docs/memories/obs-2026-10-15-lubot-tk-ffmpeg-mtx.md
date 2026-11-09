---
type: source
title: "Observation: LuBot(TK奥德彪)与FFmpeg+MTX为同一项目，已整合到桌面"
tags:
  - LuBot
  - TK奥德彪
  - 虚拟摄像头
  - tiktok
  - 无人直播
  - 整合
status: observation
created: 2026-10-15
updated: 2026-10-15
slug: obs-2026-10-15-lubot-tk-ffmpeg-mtx
relevance: medium
observed_at: 2026-10-15T03:24:47.226Z
source_context: 整合 LuBot.zip 与 FFmpeg完整版含MTX 到桌面文件夹
---

# 🔍 Observation: LuBot(TK奥德彪)与FFmpeg+MTX为同一项目，已整合到桌面

LuBot.zip (Desktop) = "TK奥德彪 v2.1.2 / TK无人防封系统"，是 FFmpeg+MediaMTX 推流套件的 Qt6 图形界面版（两者为同一项目）。结构：LuBot.exe (Qt6入口) + core/tkcore.exe (内核) + core/runtime/{ffmpeg,mediamtx,cam(LuBotCam.dll虚拟摄像头"TK Cam")} + core/tiktok_live_bridge/ (PyInstaller Python3.12 程序，websockets 连 TikTok 直播)。安装：管理员运行 install.bat → 装到 C:\Program Files\LuBot，注册虚拟摄像头，创建快捷方式；虚拟摄像头注册后目录不可移动。需要授权激活（设备码→销售方发 .lic → %LOCALAPPDATA%\LuBot\license.dat），离线激活。命令行开关：--install-cam/--play <文件>/--license-status 等。已整合到 C:\Users\16575\Desktop\TK奥德彪直播工具\（LuBot 372MB + FFmpeg完整版含MTX 718MB），ffmpeg/mediamtx 推流已从新路径重启正常（rtmp://127.0.0.1:1935/tklive, h264 720x1280@30）。

*Relevance: medium*
*Context: 整合 LuBot.zip 与 FFmpeg完整版含MTX 到桌面文件夹*
*Tags: LuBot TK奥德彪 虚拟摄像头 tiktok 无人直播 整合*

---
*Observed: 2026-10-15T03:24:47.226Z*
