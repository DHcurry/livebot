---
type: source
title: "Observation: v2.0卡顿根因：device_code每秒起PowerShell卡1.36秒，缓存后VERDICT=OK"
tags:
  - 性能
  - 卡顿
  - powershell
  - device_code
  - 缓存
  - gui
status: observation
created: 2026-11-03
updated: 2026-11-03
slug: obs-2026-11-03-v2-0-device-code-powershell-1-36-verdict-ok
relevance: high
observed_at: 2026-11-03T03:43:31.824Z
source_context: 直播工坊v2.0 GUI卡顿根因定位与修复
---

# ⭐ Observation: v2.0卡顿根因：device_code每秒起PowerShell卡1.36秒，缓存后VERDICT=OK

v2.0卡顿根因修复（2026-11-02）：GUI每秒冻结1.36秒的元凶=licensing.device_code()在_update_stats空闲分支被每秒调用，而原始实现每次都subprocess起PowerShell取ProcessorId（冷启动1.35-1.45s）且阻塞GUI线程——空闲/预览边界必卡、推流期因走别的分支反而流畅（反直觉现象的解释）。v1.2同样中招（同一licensing模块）。修复三件套：①device_code模块级缓存（首采1450ms→后续0ms）；②app_v2 MainWindow.__init__开头预热（窗口显示前付掉首采代价）；③测量方法论：QTimer16ms节拍漂移仪（lag_meter.py，预热4s后分阶段采样max/avg/P95）+回调耗时探针（lag_probe.py，>40ms记录）双工具定位。复测：三阶段max=16ms/avg<0.9ms/VERDICT=OK。排查中排除的假嫌疑：Python GC（gc.disable复测仍有冻结）、DWM阴影（标准DwmExtendFrame实现）、PNG帧解码、setStyleSheet样式抖动（实测<1ms不足以致卡）。教训：GUI热路径严禁同步subprocess，进程类采集必须缓存。

*Relevance: high*
*Context: 直播工坊v2.0 GUI卡顿根因定位与修复*
*Tags: 性能 卡顿 powershell device_code 缓存 gui*

---
*Observed: 2026-11-03T03:43:31.824Z*
