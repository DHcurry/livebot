---
type: source
title: "Observation: VBot(天寅直播助手)tkcore.exe 内嵌与用户脚本同构的 ffmpeg 模板"
tags:
  - VBot
  - 天寅直播助手
  - 侵权取证
  - ffmpeg
  - tkcore
  - LuBot
status: observation
created: 2026-11-01
updated: 2026-11-01
slug: obs-2026-11-01-vbot-tkcore-exe-ffmpeg
relevance: high
observed_at: 2026-11-01T14:27:46.440Z
source_context: VBot.zip 侵权比对取证与文档产出
---

# ⭐ Observation: VBot(天寅直播助手)tkcore.exe 内嵌与用户脚本同构的 ffmpeg 模板

用户怀疑收到的 VBot（天寅直播助手 1.6.5，微信传的 VBot.zip，336MB）搬运了其 ffmpeg 防检测推流脚本。取证：解压后核心逻辑在 VBot\core\tkcore.exe（Qt内核，PE编译时间 2026-10-21 11:15:04 UTC，sha256 0241638f…）。该 exe 内字符串为 UTF-16LE 编码，按 UTF-16 搜索命中与用户 2026-10-02/03 txt 脚本逐字或同构的模板：afftdn=nf=-60 @0x248228（完全相同）、0.00215*sin(%1*0.937) @0x247B80（幅度=用户 rotate 0.00215*sin(2πt/6.7)，频率 0.937≈2π/6.7）、crop x='8+1.6*(%3)' @0x247F80（漂移幅度=用户 1.6）、noise=alls=%1:allf=%2 @0x248040、keyint:min-keyint:scenecut 参数化 @0x24BB42、-stream_loop/128k/flv/rtmp 等。用户文件时间线（10-02/03 txt → 10-20 server.py → 10-31 pipeline.py）早于 tkcore 编译。旁证：tkcore 含 "LuBot V2 license"、LuBotCam.dll、tiktok_live_bridge、"找不到 ffmpeg: %1"。产物：E:\vbot_evidence\VBot侵权比对说明文档.docx + figs\fig1-5 + make_evidence.py（全部可复现）。

*Relevance: high*
*Context: VBot.zip 侵权比对取证与文档产出*
*Tags: VBot 天寅直播助手 侵权取证 ffmpeg tkcore LuBot*

---
*Observed: 2026-11-01T14:27:46.440Z*
