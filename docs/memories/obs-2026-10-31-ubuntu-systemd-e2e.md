---
type: source
title: "Observation: 卡密系统上云：Ubuntu systemd部署+远程签发本地验证E2E通过"
tags:
  - 卡密系统
  - 云端部署
  - paramiko
  - ubuntu
  - systemd
  - 面板
status: observation
created: 2026-10-31
updated: 2026-10-31
slug: obs-2026-10-31-ubuntu-systemd-e2e
relevance: high
observed_at: 2026-10-31T01:34:30.675Z
source_context: SSH 部署卡密系统到云服务器并验证签发闭环
---

# ⭐ Observation: 卡密系统上云：Ubuntu systemd部署+远程签发本地验证E2E通过

卡密系统云端部署完成（2026-10-29）：Ubuntu 22.04 服务器（154.36.130.188），paramiko SSH 部署。要点：①沿用本机同一密钥对（data/issuer.key 随包迁移）→ 已签发授权与直播工坊内置公钥 C532B594 继续有效；②服务器无 pip，用 apt 装 python3-cryptography(3.4含Ed25519)；③systemd 常驻 kms.service（KMS_HOST=0.0.0.0, KMS_PORT=8777, KMS_TOKEN随机），enable --now，Restart=always；④ufw inactive 无本地防火墙，云安全组已放行8777；⑤index.html 打补丁：URL ?token= 自动存 localStorage（否则远程API全401）。端到端实测：远程面板 GET stats ✓ → POST issue 签发(云端签发测试/2027-12-31) ✓ → 本地 licensing.verify_text 验证通过 E2E_PASS。Token 存于 Desktop\卡密系统\SERVER_TOKEN.txt。教训：给用户的远程面板必须支持 URL token 免配置；Linux 服务器部署 Python 工具优先 apt 包（无 pip 的精简镜像常见）。

*Relevance: high*
*Context: SSH 部署卡密系统到云服务器并验证签发闭环*
*Tags: 卡密系统 云端部署 paramiko ubuntu systemd 面板*

---
*Observed: 2026-10-31T01:34:30.675Z*
