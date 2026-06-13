# 轻量化视频理解工具 - 开发计划

## 一、项目概述

基于 **MiniCPM-V 4.6**（Ollama 本地部署）的轻量化视频理解桌面工具，提供五大核心功能模块：

1. 视频内容摘要与章节划分
2. 画面文字提取与结构化解析
3. 长时监控视频关键事件检索
4. 场景切换检测与关键帧描述
5. 目标对象出现时间点标记

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | pywebview + HTML/CSS/JS (白黑简约风) |
| 后端 | Python 3.10+ |
| 模型 | Ollama 部署 minicpm-v4.6 (localhost:11434) |
| 视频解码 | decord + opencv-python |
| 场景检测 | scikit-image (SSIM) |

### 架构图

```
┌──────────────────────────────────────────────────┐
│                   pywebview 窗口                   │
│  ┌────────────────────────────────────────────┐  │
│  │               Web 前端 (SPA)                │  │
│  │  侧边导航 │ 功能页面 │ 状态栏               │  │
│  │         window.pywebview.api.*              │  │
│  └───────────────┬────────────────────────────┘  │
│                  │  JS Bridge                     │
├──────────────────┼───────────────────────────────┤
│  ▼               ▼                               │
│  ┌────────────────────────────────────────────┐  │
│  │               Python 后端                    │  │
│  │  ┌───────────┐ ┌─────────────────────────┐ │  │
│  │  │ config.py │ │ ollama_client.py        │ │  │
│  │  └───────────┘ │  (Ollama REST API 封装)  │ │  │
│  │                └─────────────────────────┘ │  │
│  │  ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │video_processor│ │video_summarizer.py│  │  │
│  │  │.py           │ │(视频摘要与章节)    │  │  │
│  │  └──────────────┘ └────────────────────┘  │  │
│  │  ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │text_extractor│ │event_retriever.py  │  │  │
│  │  │.py           │ │(事件检索)          │  │  │
│  │  └──────────────┘ └────────────────────┘  │  │
│  │  ┌──────────────┐ ┌────────────────────┐  │  │
│  │  │scene_detector│ │object_tracker.py   │  │  │
│  │  │.py           │ │(目标追踪)          │  │  │
│  │  └──────────────┘ └────────────────────┘  │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
          │
          ▼
┌──────────────────┐
│ Ollama (localhost)│
│  minicpm-v4.6    │
│  REST API :11434  │
└──────────────────┘
```

## 二、项目目录结构

```
light-video-understand/
├── backend/
│   ├── __init__.py
│   ├── config.py              # 全局配置 (Ollama URL, 模型名, 采样参数等)
│   ├── ollama_client.py       # Ollama REST API 封装
│   ├── video_processor.py     # 视频解码与帧采样
│   ├── video_summarizer.py    # 视频摘要与章节划分
│   ├── text_extractor.py      # 画面文字提取与结构化解析
│   ├── event_retriever.py     # 关键事件检索
│   ├── scene_detector.py      # 场景切换检测与关键帧描述
│   └── object_tracker.py      # 目标对象出现时间点标记
├── frontend/
│   ├── index.html             # SPA 主页面
│   ├── css/
│   │   └── style.css          # 白黑简约风样式
│   └── js/
│       ├── app.js             # 主应用逻辑与路由
│       ├── api.js             # JS Bridge 通信封装
│       └── components.js      # UI 组件 (时间轴/卡片/列表等)
├── docs/
│   ├── 1.md                   # MiniCPM-V 4.6 官方文档
│   ├── dev-plan.md            # 本项目 (开发计划)
│   ├── backend.md             # 后端设计文档
│   └── frontend.md            # 前端设计文档
├── assets/                    # 测试用视频/图片
├── main.py                    # pywebview 入口 (窗口初始化 + JS Bridge 注册)
├── requirements.txt           # 依赖清单
├── setup.bat                  # Windows 一键安装脚本
└── README.md                  # 项目说明
```

## 三、开发阶段

### 阶段一：项目脚手架 (1天)
- [ ] 创建目录结构
- [ ] 编写 `requirements.txt`
- [ ] 实现 `config.py` 全局配置
- [ ] 实现 `ollama_client.py` Ollama 通信封装
- [ ] 编写 `main.py` pywebview 窗口骨架 + JS Bridge 注册
- [ ] 创建 `frontend/index.html` 空壳页面

### 阶段二：视频处理与第一个功能 (1天)
- [ ] 实现 `video_processor.py` (解码、采样、元数据提取)
- [ ] 实现 `video_summarizer.py` (摘要 + 章节划分)
- [ ] 前端：功能一「视频摘要」页面 + JS Bridge 对接
- [ ] 端到端联调：选择视频 → 后端处理 → 前端展示

### 阶段三：文字提取与事件检索 (1.5天)
- [ ] 实现 `text_extractor.py` (逐帧/分段文字提取 + 去重)
- [ ] 前端：功能二「文字提取」页面
- [ ] 实现 `event_retriever.py` (关键事件检测)
- [ ] 前端：功能三「事件检索」页面

### 阶段四：场景检测与目标追踪 (1.5天)
- [ ] 实现 `scene_detector.py` (SSIM + 模型语义描述)
- [ ] 前端：功能四「场景检测」页面 (画廊 + 时间轴)
- [ ] 实现 `object_tracker.py` (目标出现时间标记)
- [ ] 前端：功能五「目标追踪」页面

### 阶段五：打磨与打包 (1天)
- [ ] 全局状态管理 (进度条、日志输出)
- [ ] 错误处理增强 (视频损坏、Ollama 未启动等)
- [ ] CSS 动画细节调整
- [ ] 测试全功能流程
- [ ] PyInstaller 打包配置

## 四、关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 帧采样策略 | 均匀采样 (默认 32 帧) | 控制显存/Ollama 负载，平衡质量与速度 |
| 图片传输 | Base64 编码 | Ollama REST API 原生支持 |
| 场景检测 | CV 粗筛 (SSIM) + 模型精描 | 减少模型调用次数，SSIM 快速识别切分点 |
| 长视频处理 | 分段处理 (每 5 分钟一批) | 避免单次请求帧数过多导致 OOM |
| 文字提取 | 分批 (每批 8 帧) + 全局去重 | 减少模型幻觉，提高识别准确率 |
| 前端通信 | window.pywebview.api | pywebview 原生 JS Bridge |
| 样式方案 | 纯 CSS (无框架依赖) | 轻量化，无额外依赖 |

## 五、依赖清单

```
pywebview>=4.4           # 桌面窗口
decord>=0.4.0            # 视频解码
opencv-python>=4.8       # 视频处理辅助
Pillow>=10.0             # 图像处理
requests>=2.31           # Ollama HTTP 通信
scikit-image>=0.21       # SSIM 场景检测
numpy>=1.24              # 数值计算
pyinstaller>=6.0         # 打包 (dev 依赖)
```

## 六、风险与应对

| 风险 | 应对方案 |
|------|----------|
| Ollama vision API 限制 | 降级到纯文本模式，或提示用户检查 Ollama 配置 |
| 长视频 OOM | 动态调小 `max_slice_nums` 和 `MAX_NUM_FRAMES` |
| Ollama 未启动 | 启动时检测连通性，友好提示 |
| 视频格式不支持 | 尝试 opencv 回退解码 |
| 模型输出非 JSON | prompt 强约束 + 解析失败时 fallback 提示 |
