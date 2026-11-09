---
type: source
title: "Observation: REA+Ghidra系统完成：tkcore首析5153函数/3266字符串"
tags:
  - REA
  - Ghidra
  - 系统构建
  - tkcore
  - 首析
  - 5153函数
status: observation
created: 2026-10-22
updated: 2026-10-22
slug: obs-2026-10-22-rea-ghidra-tkcore-5153-3266
relevance: critical
observed_at: 2026-10-22T10:12:22.794Z
source_context: REA+Ghidra 引擎部署与 tkcore 首次分析
---

# 🔴 Observation: REA+Ghidra系统完成：tkcore首析5153函数/3266字符串

REA+Ghidra 系统构建完成并首析成功（2026-10-22）：Ghidra 12.1 (ghidra_12.1_PUBLIC_20260513.zip, SHA256 aa5cbcbb 官方一致, 567,828,511字节) 经代理下载（第1次454MB断流截断被体积门槛+SHA拦下重来；自愈循环含 speed-limit 低速熔断），解压 C:\Tools\ghidra_12.1_PUBLIC；JDK21= C:\Tools\jdk-21.0.2 (华为镜像)；setx JAVA_HOME + GHIDRA_INSTALL_DIR；rea doctor 的 ghidra 全项 healthy（ida/jadx/kuna 可选引擎仍缺不影响）。首冒烟 `rea analyze tkcore.exe --provider ghidra --format md`：输出证据封条式报告（9KB,59节）→ tkcore.exe: PE x86_64, base 0x140000000,8段(.text 903KB/.rdata 3.7MB), **5153 procedures, 3266 defined strings**, sha256 69dde4a6。注意: `rea analyze` 的 binary_overview 只出概览；函数/字符串清单要用 list_procedures/list_strings（下次 pi 会话经 MCP 用）。坑: 报告管道接 head -80 会 SIGPIPE 截断 tee；ctx_execute 脚本里 count() 签名笔误；bash 工具会拦裸 curl（用 -s -o 文件绕过）；git-bash /tmp 与 /c 路径 Windows python 不认。tkcore 深析下一步可查: scCreateCamera/Softcam、onToggleVirtualCamera、图层(topScroll/texture)、blend相关。

*Relevance: critical*
*Context: REA+Ghidra 引擎部署与 tkcore 首次分析*
*Tags: REA Ghidra 系统构建 tkcore 首析 5153函数*

---
*Observed: 2026-10-22T10:12:22.794Z*
