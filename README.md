<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

<img alt="LOGO" src="./docs/images/logo.png" width="256" height="256" />

# MaaPCR

基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 构建的公主连结 Re:Dive（Princess Connect! Re:Dive）日服自动化工具

参考项目：[Rino_PCRautomation](https://github.com/miaoyu2233/Rino_PCRautomation)

</div>

## 功能列表

以下功能按当前 `assets/interface.json` 中启用的任务整理。

### 日常任务

- [x] 行程表/日程表
- [x] 主线扫荡预设 — 支持选择预设扫荡
- [x] 领取礼物邮件
- [x] 领取日常奖励
- [x] 探险领取
- [x] 探险缩短时间 — 支持选择加速的队伍
- [x] 探险事件 — 支持概率事件选择

### 黎明界

- [x] 黎明界(基础框架) — 支持目标公会、难易度、失败策略、商店策略、完成策略配置

### 商店购买

- [x] 地下城角色碎片 — 支持刷新策略与指定角色
- [x] 竞技场角色碎片 — 支持刷新策略与指定角色
- [x] 公主竞技场角色碎片 — 支持刷新策略与指定角色

### 角色养成

- [x] 角色全部强化 — 可选是否先强化 Rank
- [x] 喂蛋糕好感

### 剧情

- [x] 角色剧情
- [x] 露娜塔剧情
- [x] 公主生日剧情
- [x] 主线剧情

### 小工具

- [x] 小工具-究极炼成(需炼成页面) — 支持目标词条、目标词条数、是否忽略词条数值配置

## 使用说明

### 下载安装

- 在右侧 [Releases](https://github.com/hitazuki/MaaPCR/releases) 页面，根据操作系统和架构下载压缩包（通常为 `windows_x86_64`）
- 首次运行需安装 .NET 和 VC++ 运行库，压缩包内含安装脚本
- 压缩包已内置 Python 环境，无需额外安装

### 快速开始

- Windows 平台运行 `MaaPCR.exe` 即可
- 首次运行或使用 DMM 端时，可能需要管理员权限

### 安卓模拟器

- 模拟器分辨率调整为 **1280×720**（DPI 240）
- 控制器类型选择「安卓端」，当前控制器选择游戏对应实例
- 目前测试过 MuMu 模拟器（其他模拟器理论上也可用）

### DMM 桌面端

- 窗口分辨率调整为 **1280×720**（拉至最大即为该分辨率）
- 控制器类型选择「桌面端」，当前控制器选择游戏窗口
- 鼠标输入方式默认 `SendMessageWithWindowPos`，可在设置中更改
- ⚠️ 已知问题：部分任务完成后因无法识别安卓返回按钮，可能阻塞后续任务

## 版本历史

| 版本 | 主要变更 |
| ---- | -------- |
| [v0.4.0](https://github.com/hitazuki/MaaPCR/releases/tag/v0.4.0) | 究极炼成新增 HP、TP上升、物理/魔法攻击力、物理防御贯通等词条选项 |
| [v0.3.2](https://github.com/hitazuki/MaaPCR/releases/tag/v0.3.2) | 重构角色全部强化流程，引入 JumpBack 循环机制 |
| [v0.3.1](https://github.com/hitazuki/MaaPCR/releases/tag/v0.3.1) | — |
| [v0.3.0](https://github.com/hitazuki/MaaPCR/releases/tag/v0.3.0) | — |
| [v0.2.0](https://github.com/hitazuki/MaaPCR/releases/tag/v0.2.0) | — |
| [v0.1.0](https://github.com/hitazuki/MaaPCR/releases/tag/v0.1.0) | 初始版本 |

## 开发相关

### 技术栈

- [MaaFramework](https://github.com/MaaXYZ/MaaFramework) v5.x — 自动化框架
- Pipeline 协议定义任务流水线（图像识别 + 动作执行）
- Python 自定义识别/动作扩展

### 项目结构

```plaintext
assets/
├── interface.json              # UI 界面与任务选项配置
├── resource/
│   ├── image/jp/               # 日服图像模板
│   ├── image/role/             # 角色图像模板
│   ├── model/                  # 深度学习模型
│   └── pipeline/               # 任务流水线定义
├── MaaCommonAssets/            # MaaFramework 公共资源
└── config/                     # 配置文件
```

### 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 pre-commit hooks（代码格式化）
pip install pre-commit
pre-commit install
```

## 免责声明

使用本辅助工具的用户（以下简称"用户"）请注意以下几点：

1. 本辅助工具仅供个人娱乐和教育目的使用。使用本工具可能违反特定游戏或应用的使用政策，请自行承担风险。
2. 开发者不对用户使用本工具所产生的任何后果负任何法律或道德责任。用户应自行承担使用工具可能带来的风险。
3. 本工具不会有任何性质盈利行为，且只在 GitHub 上发布，其他版本及其行为均与本人无关。
