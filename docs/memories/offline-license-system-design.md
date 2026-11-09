---
type: source
title: 离线授权系统设计：非对称签名上限与吊销分发模型
status: insight
category: security
created: 2026-10-23
updated: 2026-10-23
slug: offline-license-system-design
---

# 离线授权系统设计：非对称签名上限与吊销分发模型

离线授权系统的安全上限与设计要点（自建卡密系统实践中验证）：

1. **必须用非对称签名**（Ed25519）：私钥留签发方、公钥嵌客户端。HMAC/对称方案里验证密钥=签发密钥，客户反编译即能伪造，形同虚设。公钥只有32字节，嵌入成本极低。
2. **离线授权能保证的上限**是"不能凭空造新授权"，不能阻止"程序+授权整包拷贝到同类型硬件"——这是无服务器模式的固有边界，交付时必须向客户讲清。
3. **吊销在离线模式只能发版分发**：revocations.txt 随应用更新下发；客户端验证器应默认自动加载同目录名单文件（首次实现漏了这点，测试6暴露：API吊销了但客户端仍验证通过）。
4. **设备指纹三信号**（MachineGuid+ProcessorId+MAC混合）在实体机稳定，但虚拟机每次重装 MachineGuid 都变——VM/云手机客户要单独策略（any-device 或按VM指纹签）。
5. 防时钟回拨用本地时间锚点（记录上次成功验证时间，now < last_ok-24h 判回拨）是零依赖启发式，够用但非密码学强保证。
6. 实现坑：Python http.server 中文路径/查询必须客户端 quote()；Ed25519 签名必须签"规范化载荷文本本身"（json.dumps sort_keys separators）而非重新序列化对象，否则验证端序列化差异导致验签失败。

相关：[[TK奥德彪授权边界]]——商业软件的授权系统（如LuBot/TK奥德彪）即使停服也不克隆不接管：其校验私钥在厂商手里，客户侧无法恢复；正确做法是给自己的产品建自有授权体系。

*Category: security*

---
*Captured: 2026-10-23*

## Related

_Add links to related pages._
