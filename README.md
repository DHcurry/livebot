# LiveBot · 直播工坊 LiveStudio

自有"无人直播"工具链：**去重推流引擎 + 图形界面 + 自研卡密授权 + 内置竖屏虚拟摄像头**，
全部为原创/合法开源组件构建，附带完整开发记忆（含 LuBot 逆向研究记录）。

## 仓库结构

```
├── 直播工坊/                     主程序（Python）
│   ├── app_v2.py                 v2.0 界面（PySide6 + QFluentWidgets + Dock + OpenGL 预览）
│   ├── app.py                    v1.2 交付界面（tkinter，稳定发货版）
│   ├── pipeline.py               推流引擎：txt 去重管线参数化 + 虚拟摄像头 + MediaMTX 托管
│   ├── licensing.py              卡密授权客户端（Ed25519 离线验签 + 云端在线兑换）
│   ├── envassist.py              环境助手（29 城市时区/区域 + 六项系统清理 + 体检）
│   ├── setup.py / assemble.py    自研安装器（用户级注册虚拟摄像头驱动，免 UAC）
│   ├── driver/                   虚拟摄像头驱动（UnityCapture MIT 改造，原生 1080x1920 竖屏）
│   └── vcam_build/               驱动源码（分辨率表头部插入竖屏规格）+ MSVC 构建脚本
├── 卡密系统/                     自研卡密授权系统（签发 CLI + Web 管理面板 + 验证器）
│   └── README.md                 三种签发方式：首激活绑定 / 绑定设备 / 不限设备
├── docs/
│   ├── 工作总览.md               项目全景与踩坑手册
│   ├── tkcore架构读取报告.md     REA+Ghidra 对 LuBot 内核的功能层逆向（含证据 ID）
│   ├── tkcore分析报告.md         Ghidra 首析证据存档
│   └── memories/                 ★ LLM 会话记忆 27 篇（LuBot 研究为主线，见 INDEX.md）
└── .gitignore
```

## 快速开始

```bash
# 运行界面（v1.2 交付版）
cd 直播工坊 && python app.py

# 运行 v2.0（需 pip install PySide6 PySide6-Fluent-Widgets pyvirtualcam）
python app_v2.py

# 卡密面板
cd 卡密系统 && python panel/server.py     # http://127.0.0.1:8777
```

依赖：Python 3.11+、`cryptography`；v2.0 另需 PySide6 栈；推流工具链（ffmpeg/MediaMTX）
放在本机自定义路径（`pipeline.py` 顶部 `TOOL_ROOT` 配置）。

## 核心能力

- **txt 去重管线**：噪点/微旋转/呼吸缩放/裁剪漂移/亮度对比色相浮动 + 音频降重中族，参数即脚本原值
- **内置虚拟摄像头**：基于 MIT 开源 UnityCapture 改造（`driver/NOTICE.txt`），原生 1080x1920 竖屏输出，
  安装器用户级注册（免管理员），开播平台直接选设备
- **卡密授权**：Ed25519 离线验签，支持短卡密在线兑换、首激活绑定防转卖；云端面板可选部署
- **环境助手**：城市级时区/区域对齐 + TikTok 环境清理六项 + 硬件体检

## 关于 LuBot 部分

`docs/` 与 `docs/memories/` 中的 LuBot/TK 相关内容是**技术研究记录**（架构逆向、驱动协议对比、
能力对齐过程）。虚拟摄像头使用 MIT 许可的 UnityCapture 改造实现，**未包含任何 LuBot 专有代码或二进制**。

## 安全说明

本仓库不含任何密钥：签发私钥（`卡密系统/data/`）、面板 Token、激活码、SSH 口令均已排除
（装配脚本内置密钥保险丝扫描，命中即中止）。

## 许可

自有代码保留所有权利；随附的 UnityCapture 组件为 MIT 许可，版权声明见
`直播工坊/driver/NOTICE.txt`。仅供自有内容直播使用。
