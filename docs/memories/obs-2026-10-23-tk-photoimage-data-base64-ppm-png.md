---
type: source
title: "Observation: 直播工坊预览黑屏修复：Tk PhotoImage data=不认base64 PPM，换PNG帧流"
tags:
  - bug修复
  - tkinter
  - photoimage
  - png
  - ppm
  - 预览
  - 直播工坊
status: observation
created: 2026-10-23
updated: 2026-10-23
slug: obs-2026-10-23-tk-photoimage-data-base64-ppm-png
relevance: medium
observed_at: 2026-10-23T03:42:21.739Z
source_context: 修复直播工坊预览黑屏（tk PhotoImage PPM data不支持）
---

# 🔍 Observation: 直播工坊预览黑屏修复：Tk PhotoImage data=不认base64 PPM，换PNG帧流

直播工坊预览黑屏bug修复（2026-10-23）：症状=点▶预览按钮状态变了但画面永远不出来。排查过程：引擎层裸测3/3次正常(6秒18.6MB PNG字节)，GUI层复现时缓冲区有数据、帧也被消费但PhotoImage从未成功——app.py里 except Exception: pass 吞掉了真实错误。最终定位：tk.PhotoImage(data=base64(PPM)) 报 TclError "couldn't recognize image data"，而 data=base64(PNG) 和 file=PPM 都正常——Tk的photo -data对base64 PPM不支持（file=才认PPM）。修复：build_preview_cmd -vcodec ppm→png；PpmReader→PngReader（PNG chunk级解析：sig+循环读len/type/data/crc直到IEND）；_preview_frame 直接用PNG bytes base64传data=，异常改为写日志不再吞。教训：1)GUI显示层报错绝不能except pass——这次吞错让排查走了4轮弯路；2)tkinter PhotoImage data= 只可靠支持 GIF/PNG（8.6），PPM/PGM走 file=；3)排查要对比"裸引擎成功 vs GUI失败"的差异面。复测：_pv_img=(240,426)，截图确认画面正常。

*Relevance: medium*
*Context: 修复直播工坊预览黑屏（tk PhotoImage PPM data不支持）*
*Tags: bug修复 tkinter photoimage png ppm 预览 直播工坊*

---
*Observed: 2026-10-23T03:42:21.739Z*
