---
type: source
title: "Observation: LuBot底层已替换为txt脚本管线：RTMP双输出+TK Cam保住，fast档1.0x实时"
tags:
  - wrapper-v3
  - txt底层替换
  - 双输出
  - TK
  - Cam
  - fast档
  - ghidra断点续传
  - REA
status: observation
created: 2026-10-21
updated: 2026-10-21
slug: obs-2026-10-21-lubot-txt-rtmp-tk-cam-fast-1-0x
relevance: critical
observed_at: 2026-10-21T15:08:55.909Z
source_context: 把LuBot底层管线替换为txt脚本
---

# 🔴 Observation: LuBot底层已替换为txt脚本管线：RTMP双输出+TK Cam保住，fast档1.0x实时

LuBot底层管线已替换为txt脚本（wrapper v3, 2026-10-21）：ffmpeg_cam_wrapper.cs 重写——检测到LuBot的rawvideo管线命令后，抛弃其原生CUDA差异化filter_complex，重建为：①素材取自LuBot的-i参数(如素材3)；②2026.10.03txt的完整去重滤镜链(noise/scale-eval/rotate/crop/720x1280/eq/hue/setpts)+setsar+format=yuv420p；③可选真实摄像头5% blend(cam_opacity.txt>0时注入dshow输入,[cam][txt]blend透明层在前)；④split双输出：分支A x264推rtmp://127.0.0.1:1935/tklive(txt编码参数,-preset fast——medium实测仅0.82x实时,CPU100%,fast=1.03x)，分支B scale到1080x1920 bgr24 rawvideo写stdout维持LuBot软相机契约(TK Cam验证1080x1920继续出画)。前缀flags剥离 -hwaccel auto/-init_hw_device cuda/-filter_hw_device cu(改纯软解)。安全阀：包装器先Tcp探测127.0.0.1:1935，MediaMTX不在线则回退LuBot原管线(LuBot日志仍打印它原始命令但那是它自己的记录，实际子进程被改写；wrapper.log记录V3 TXT-pipeline applied)。依赖：控制台的MediaMTX必须运行。副作用：LuBot的智能处理/图层不再作用于输出。Ghidra 12.1.4下载：SF断在566.8/569.6MB(SHA不符)，已开curl -C -断点续传+SHA校验(ddac49f9...)；JDK21.0.2就绪(Huawei镜像)，GHIDRA_INSTALL_DIR待设。REA已装(npm rea-agents@6.7.0绕GitHub墙)+注册pi MCP(207工具)。

*Relevance: critical*
*Context: 把LuBot底层管线替换为txt脚本*
*Tags: wrapper-v3 txt底层替换 双输出 TK Cam fast档 ghidra断点续传 REA*

---
*Observed: 2026-10-21T15:08:55.909Z*
