---
type: source
title: "Observation: LuBot TK Cam 取流+真实摄像头5%合层完成，blend方向坑修复"
tags:
  - LuBot
  - TK
  - Cam
  - blend合层
  - dshow双摄
  - 图层方向
  - 坑
status: observation
created: 2026-10-19
updated: 2026-10-19
slug: obs-2026-10-19-lubot-tk-cam-5-blend
relevance: high
observed_at: 2026-10-19T11:43:24.752Z
source_context: 把合层画面接入 LuBot 链路（从 TK Cam 取流）
---

# ⭐ Observation: LuBot TK Cam 取流+真实摄像头5%合层完成，blend方向坑修复

LuBot取流合层模式完成（2026-10-19）：ffmpeg 可并发读取 LuBot 的 TK Cam（DirectShow 软摄，LuBot 播放时输出其处理后画面 1080x1920，但仅 ~26-29fps 发帧率=硬上限）。最终链：TK Cam(输入0, rtbufsize 20M) + HP真实摄像头(输入1,1280x720) → [0:v]scale=720:1280,format=yuv420p[b]; [1:v]scale+crop,format=yuv420p[c]; [c][b]blend=all_mode=normal:all_opacity=0.05,fps=30[v] → x264 veryfast → rtmp tklive，实测 29fps/0.95x 稳定。重大工具坑：(1) ffmpeg blend 滤镜的 all_opacity 作用于【第一个输入】（与 overlay 相反）——透明层要放前面 [c][b]，放反了会变成素材5%+摄像头100%；(2) 双 dshow 实时源加 -use_wallclock_as_timestamps/-fflags genpts 会把 overlay 同步搞死（0.5fps/11秒只出6帧，还触发 mediamtx readTimeout 10s 断开 RTMP，错误 -10053）；(3) yuva420p+colorchannelmixer 的 alpha 路径走 argb 转换慢，blend 同格式混合更省；(4) TK Cam 只支持 1080x1920 输出（720x1280 协商失败 I/O error）；(5) 末尾 fps=30 对齐时间轴防延迟累积。LuBot 窗口自身预览永远只显示内部管线（闭源无外部输入接口，图层仅 texture/main/bottomScroll），合层结果只能走 RTMP/HLS 通道。控制台 v3.2：source=tkcam 参数 + 画面来源下拉框。

*Relevance: high*
*Context: 把合层画面接入 LuBot 链路（从 TK Cam 取流）*
*Tags: LuBot TK Cam blend合层 dshow双摄 图层方向 坑*

---
*Observed: 2026-10-19T11:43:24.752Z*
