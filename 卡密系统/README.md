# 卡密授权系统（自建）

> 为自有产品/设备打造的**离线授权体系**：设备指纹 → 本地签发 → 离线验证 → 网页面板管理。
> 不依赖任何云端服务，签发方完全掌控。

## 安全模型（为什么可靠）

| 设计 | 说明 |
|---|---|
| **Ed25519 非对称签名** | 私钥只在你机器上签发授权；客户端只嵌 32 字节公钥。**客户机被反编译也无法伪造新授权**（没有私钥签不出合法签名） |
| **设备指纹绑定** | MachineGuid + CPU ID + MAC 三信号混合，改一个不影响、换主板才失效 |
| **离线验证** | 验证不需要网络，厂商跑路/断网不影响已授权客户 |
| **吊销名单** | `data/revocations.txt` 随应用更新分发（离线模式的固有限制：需发版才能生效） |
| **防时钟回拨** | 客户端本地锚点，检测到系统时间被倒拨会拒绝（启发式，可关） |

## 目录

```
卡密系统\
├── core\              密钥/指纹/授权/卡密 四个核心模块
├── issuer\gen.py      签发命令行（init/issue/batch/revoke/embed）
├── client\verify.py   ★ 独立验证器（嵌入公钥后随你的产品分发）
├── panel\             Web 管理面板（127.0.0.1:8777）
├── data\              issuer.key 私钥 + licenses.db + revocations.txt（运行时生成）
├── 启动面板.bat
└── 查看本机设备码.bat
```

## 快速开始

```bat
:: 1. 首次：生成密钥对（私钥 data\issuer.key 务必备份三处！）
python issuer\gen.py init

:: 2. 把公钥嵌入客户端验证器
python issuer\gen.py embed

:: 3. 看本机设备码（客户报给你）
python issuer\gen.py device

:: 4. 给客户签发（绑定设备、有效期）
python issuer\gen.py issue --customer 张三 --hwid 1E1AF8AC-AD102F61 --expires 2027-10-22 --out 张三.lic

:: 5. 批量卡密（渠道销售，导出 CSV）
python issuer\gen.py batch --customer 渠道A --count 50 --expires 2027-12-31

:: 6. 验证测试
python client\verify.py 张三.lic
```

**管理面板**：双击 `启动面板.bat` → 浏览器开 `http://127.0.0.1:8777`
（签发/批量/搜索/下载lic/复制激活码/吊销恢复/CSV导出 全可视化）

## 客户激活流程

1. 客户运行你的程序 → 显示**设备码**（如 `1E1AF8AC-AD102F61`）
2. 你收到设备码 → 面板签发（或 CLI）→ 得到激活码（`LIC1.xxxx.yyyy` 长字符串）
3. 客户把激活码粘贴进程序 → 本地验证通过 → 写入客户机授权文件
4. 之后**全程离线**，不再依赖任何服务器

## 在你的程序里集成验证

**Python（最简）**：
```python
from client.verify import verify_license_text, local_hwid
res = verify_license_text(lic_text, hwid=local_hwid())
if res.ok:
    ...  # 授权有效，res.payload 里有客户/有效期/功能点
```

**命令行（C#/C++/任何语言 subprocess 调用）**：
```bat
python client\verify.py 授权文件.lic --json
:: 退出码 0=有效 1=无效；--json 输出 {ok,reason,payload}
```

**功能点控制**：
```python
res = verify_license_text(text, require_feature="export")   # 按功能点放行
```

## CLI 命令一览

| 命令 | 作用 |
|---|---|
| `gen.py init` | 生成密钥对（首次） |
| `gen.py device` | 本机设备码 + 原始信号 |
| `gen.py issue --customer X [--hwid 码\|--any-device] [--expires 日期\|--permanent]` | 签发单个授权 |
| `gen.py batch --customer X --count N --expires 日期 --csv out.csv` | 批量卡密 |
| `gen.py verify 文件.lic [--hwid 码]` | 命令行验证 |
| `gen.py revoke --id 授权ID` / `unrevoke` | 吊销/恢复 |
| `gen.py embed` | 公钥写入 client\verify.py |

## 安全须知（必读）

1. **`data\issuer.key` = 你的授权命根**。丢失 = 已发授权全部作废；泄露 = 别人可给你客户发真授权。备份到 U盘/网盘私密空间。
2. 面板默认只监听 `127.0.0.1`。**不要**随意设 `KMS_HOST=0.0.0.0` 暴露局域网；确需远程管理时设 `KMS_TOKEN=强口令` 并走 SSH 隧道。
3. 私钥签名的服务端不联外网最好；至少不要和下载站/客户反馈渠道混在同一台暴露机器。
4. 设备指纹三信号在虚拟机里可能不稳定（虚拟机每装一次 MachineGuid 都会变）——云手机/虚拟机客户建议签 `--any-device` 或按其 VM 指纹单独签。
5. 离线授权的固有边界：客户把你的程序+授权一起打包拷给别人（同硬件类型）无法从密码学上阻止——本系统保证的是"**不能凭空造新授权**"，这是离线授权能做到的上限。

## 与 LuBot/TK奥德彪 的关系

**无关**。这是给**你自己的产品**用的系统。LuBot 的授权是它厂商的，本系统不涉及也不替代它——
我们没有也没有去逆向它的授权协议；它停服的云校验只能由它的私钥恢复，而那个私钥不在任何客户手里。
