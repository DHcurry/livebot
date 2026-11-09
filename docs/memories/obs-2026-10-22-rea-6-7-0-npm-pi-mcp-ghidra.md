---
type: source
title: "Observation: REA 6.7.0 经 npm 装好并注册进 pi（MCP+技能），缺 Ghidra 引擎"
tags:
  - REA
  - 逆向
  - MCP
  - pi注册
  - Ghidra
  - 镜像
status: observation
created: 2026-10-22
updated: 2026-10-22
slug: obs-2026-10-22-rea-6-7-0-npm-pi-mcp-ghidra
relevance: high
observed_at: 2026-10-22T07:18:11.099Z
source_context: clone 并接入 GitHub 爆火的 REA 工具
---

# ⭐ Observation: REA 6.7.0 经 npm 装好并注册进 pi（MCP+技能），缺 Ghidra 引擎

REA(morluto/rea) 已接入本机并注册进 pi（2026-10-22）：GitHub 35万星的逆向工程 MCP 工具。clone 被墙（gitclone/gh-proxy/ghfast 三个镜像全失败，gitclone 假成功留空壳 .git），改走官方 npm 路径：npm i -g rea-agents 成功装 6.7.0；`rea setup --client pi --yes` 把 MCP 注册进 C:\Users\16575\.pi\agent\mcp.json（node rea.mjs mcp，重启 pi 后生效，握手实测返回 207 个工具），并安装技能到 ~/.agents/skills/reverse-engineer-anything（207 tools, skill v42）。`rea doctor` 体检：node24/win32健康，但四大分析引擎全缺（ghidra 需设 GHIDRA_INSTALL_DIR + JDK21+，ida 需商业注册，jadx 需自备 jar，kuna 需自备 exe，hopper 需 --install-hopper）——分析 tkcore.exe(原生PE) 走 Ghidra 路线需装 Temurin JDK21(winget有)+Ghidra 12.1(1.3GB,GitHub源被墙需镜像)。边界约定：仅用于架构分析，不破解 LuBot 卡密。本机 winget 可用，Temurin JDK 11/17/21 在 winget 源里。

*Relevance: high*
*Context: clone 并接入 GitHub 爆火的 REA 工具*
*Tags: REA 逆向 MCP pi注册 Ghidra 镜像*

---
*Observed: 2026-10-22T07:18:11.099Z*
