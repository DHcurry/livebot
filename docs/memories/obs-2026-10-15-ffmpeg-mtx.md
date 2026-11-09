---
type: source
title: "Observation: FFmpeg完整版含MTX 项目解压并运行成功"
tags:
  - ffmpeg
  - mediamtx
  - rtmp
  - 推流
  - 直播
status: observation
created: 2026-10-15
updated: 2026-10-15
slug: obs-2026-10-15-ffmpeg-mtx
relevance: medium
observed_at: 2026-10-15T02:23:29.285Z
source_context: 解压并运行 FFmpeg完整版含MTX 项目
---

# 🔍 Observation: FFmpeg完整版含MTX 项目解压并运行成功

微信收到的压缩包 FFmpeg完整版含MTX.zip (287MB) 解压到 C:\Users\16575\FFmpeg完整版含MTX\FFmpeg完整版含MTX\，含两部分：1) Mediamtx/mediamtx.exe (MediaMTX 流媒体服务器, mediamtx.yml 开启 RTMP:1935/RTSP:8554/HLS:8888/WebRTC:8889/SRT:8890/MoQ, authMethod internal, paths: all_others)；2) ffmpeg-9.0.2-full_build，bin/ 下有三个推流脚本 bendi.bat(推127.0.0.1:1935/tklive)、myt.bat/mytzhanmei.bat(推192.168.100.100:1935/tklive)，用 -stream_loop -1 循环本地视频加 noise/微缩放/微旋转/crop/亮度色相抖动+音频 atempo 随机化去重指纹滤镜，libx264 4000k keyint=120 720x1280 推 RTMP。运行状态：mediamtx (#1) 与 bendi.bat (#3) 均在 Monitor 中运行。坑1：素材原路径 E:\jianhaodesucai\jingjing.mp4 不存在，已创建目录并放入 30fps/720x1280 测试视频。坑2：60fps 源在该机 x264 medium 只能编 ~28fps 导致 speed=0.46x 推流变慢，转成 30fps 源后按 30fps 实时推流正常（keyint=120 即按 30fps 设计）。验证：ffprobe rtmp/rtsp 均读到 h264 720x1280@30，HLS index.m3u8 正常返回。

*Relevance: medium*
*Context: 解压并运行 FFmpeg完整版含MTX 项目*
*Tags: ffmpeg mediamtx rtmp 推流 直播*

---
*Observed: 2026-10-15T02:23:29.285Z*
