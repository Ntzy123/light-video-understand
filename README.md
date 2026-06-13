<div align="center">
  <h1>🎬 LightVideo</h1>
  <p><strong>轻量化视频理解工具</strong> — 基于视觉大模型，让机器看懂视频</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey" alt="Platform">
  </p>
</div>

---

## 📖 简介

**LightVideo** 是一款跨平台桌面应用，借助本地的 **多模态大语言模型（Ollama + LLaVA / MiniCPM-v）**，对视频进行智能理解与分析。无需联网、无需 GPU（CPU 即可运行），隐私安全。

> 💡 核心思路：利用视觉语言模型逐帧"读懂"视频内容，提供摘要、检索、追踪等高级功能。

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 📝 **视频摘要** | 自动生成视频概要、章节划分与时间戳 |
| 🔍 **文字提取** | 提取视频画面中的文字信息（字幕、标题、路牌等） |
| 🎯 **事件检索** | 通过自然语言描述，检索视频中的关键事件 |
| 🎬 **场景检测** | 基于 SSIM 的镜头切换检测与场景描述 |
| 👁️ **目标追踪** | 追踪指定目标（人/物）在视频中的出现位置与时间 |

## 🏗️ 项目结构

```
light-video-understand/
├── backend/
│   ├── config.py              # 全局配置
│   ├── video_processor.py     # 视频文件处理 & 元数据提取
│   ├── video_summarizer.py    # 📝 视频摘要
│   ├── text_extractor.py      # 🔍 文字提取
│   ├── event_retriever.py     # 🎯 事件检索
│   ├── scene_detector.py      # 🎬 场景检测
│   ├── object_tracker.py      # 👁️ 目标追踪
│   ├── ollama_client.py       # Ollama API 封装
│   └── __init__.py
├── frontend/
│   ├── index.html             # 主页面
│   ├── favicon.ico             # 网站图标
│   ├── css/style.css           # 样式
│   └── js/
│       ├── app.js              # 应用逻辑
│       ├── api.js              # JS Bridge 通信
│       └── components.js       # UI 组件
├── docs/
│   ├── api.md                  # API 文档
│   ├── backend.md              # 后端架构说明
│   ├── frontend.md             # 前端架构说明
│   └── dev-plan.md             # 开发计划
├── main.py                     # 应用入口 & JS Bridge API
├── run.py                      # 启动脚本
├── setup.bat                   # Windows 一键安装脚本
├── requirements.txt            # Python 依赖
└── README.md
```

## 🚀 快速开始

### 前置条件

- **Python 3.9+**
- **[Ollama](https://ollama.ai)** 已安装并启动
- 拉取多模态模型（推荐）：
  ```bash
  ollama pull minicpm-v4.6
  # 或
  ollama pull llava:7b
  ```

### 安装与运行

#### Windows 🪟

双击 `setup.bat` 一键安装，或手动执行：

```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python run.py
```

#### macOS / Linux 🍎🐧

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动应用
python run.py
```

### 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --name=LightVideo --add-data "frontend;frontend" run.py
```

> Windows 下也可直接运行 `setup.bat` 并选择打包选项。

## ⚙️ 配置说明

所有配置集中在 `backend/config.py`，主要参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `OLLAMA_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `MODEL_NAME` | `minicpm-v4.6` | 使用的多模态模型 |
| `MAX_NUM_FRAMES` | `32` | 最大采样帧数 |
| `SSIM_THRESHOLD` | `0.7` | 场景切换检测敏感度 |
| `TEMPERATURE` | `0.1` | 模型生成温度 |

## 📚 文档

- [API 文档](docs/api.md) — JS Bridge 接口说明
- [后端架构](docs/backend.md) — 后端模块设计与原理
- [前端架构](docs/frontend.md) — 前端页面结构与交互
- [开发计划](docs/dev-plan.md) — 路线图与待办事项

## 🔧 技术栈

- **前端**：原生 HTML5 + CSS3 + JavaScript（Material Icons）
- **后端**：Python 3.9+
- **桌面框架**：[pywebview](https://github.com/r0x0r/pywebview)（轻量级 WebView 桌面应用）
- **视频处理**：OpenCV + decord
- **AI 引擎**：[Ollama](https://ollama.ai)（本地多模态大模型）
- **视觉计算**：scikit-image（SSIM 场景检测）

## 🤝 贡献

欢迎提交 Issue 和 PR！如果你有好的想法或发现了 Bug，请先查看已有的 [Issues](https://github.com/your-username/light-video-understand/issues)。

## 📄 许可

[MIT License](LICENSE)

---

<p align="center">Made with ❤️ by LightVideo Team</p>

