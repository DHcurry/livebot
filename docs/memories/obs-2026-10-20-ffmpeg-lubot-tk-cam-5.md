---
type: source
title: "Observation: ffmpeg包装器注入LuBot内部管线成功：TK Cam自带5%摄像头合层"
tags:
  - ffmpeg包装器
  - LuBot注入
  - blend管线
  - ffmpeg.orig
  - UAC
  - 性能优化
status: observation
created: 2026-10-20
updated: 2026-10-20
slug: obs-2026-10-20-ffmpeg-lubot-tk-cam-5
relevance: critical
observed_at: 2026-10-20T13:26:17.925Z
source_context: 在LuBot软件内部实现真实摄像头5%合层
---

# 🔴 Observation: ffmpeg包装器注入LuBot内部管线成功：TK Cam自带5%摄像头合层

效果已"长进"LuBot 内部（2026-10-20，ffmpeg包装器方案）：LuBot 每次播放调用自己目录的 ffmpeg.exe 生成 rawvideo 喂 TK Cam，故用 C# 包装器(csc.exe编译,6.6KB)替换它——包装器解析 Environment.CommandLine 文本，在检测到 `-f rawvideo`+`,format=bgr24[out]` 的视频管线时：①在 -filter_complex 前插入 ` -f dshow -rtbufsize 20M -framerate 30 -video_size 1280x720 -i "video=HP Wide Vision HD Camera"` ②把 `,format=bgr24[out]` 换成 `[n];[1:v]crop=w='min(iw,ih*1080/1920)':h=ih:x='(iw-out_w)/2':y=0,scale=1080:1920:flags=bilinear,setsar=1,format=yuv420p[cam];[cam][n]blend=all_mode=normal:all_opacity=OP[m];[m]format=bgr24[out]`（标签[out]保留免改-map），然后启动 ffmpeg.orig.exe 并 WaitForExit，stdio 直通。原版备份 ffmpeg.orig.exe(550912B)，替换需 UAC（C:\Program Files\LuBot\core\runtime\ffmpeg\）。透明度在 %LOCALAPPDATA%\LuBot\cam_opacity.txt（每条管线命令启动时读取，改后需重启LuBot播放），日志 wrapper.log 显示 MODIFIED/passthrough。v1(直接scale到1080p再blend于bgr24)太贵→CPU 88%、TK Cam 只有17-24fps；v2(先裁9:16中心405x720再bilinear放大+yuv空间blend)→TK Cam 恢复29fps/0.966x。验证：50%档抓帧见房间实景与机器人素材合层，5%档干净。CPU注意：i5-9300H 上 LuBot管线+控制台转码+网页播放器三开到92%，控制台RTMP转码应按需开（source=tkcam不勾叠加，避免二次叠加）。UAC批量触发坑：Start-Process -Verb RunAs -Wait 会阻塞到用户点；含中文路径的bat必须ASCII内容或chcp65001（否则GBK误读致路径乱码复制失败）；git-bash会把 /f /im /nologo 转成路径需 MSYS_NO_PATHCONV=1。

*Relevance: critical*
*Context: 在LuBot软件内部实现真实摄像头5%合层*
*Tags: ffmpeg包装器 LuBot注入 blend管线 ffmpeg.orig UAC 性能优化*

---
*Observed: 2026-10-20T13:26:17.925Z*
