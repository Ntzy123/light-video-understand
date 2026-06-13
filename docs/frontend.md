# 前端设计文档

## 一、技术选型

- **框架**：无框架，纯 HTML5 + CSS3 + ES6
- **桌面容器**：pywebview (Python → 本地 WebView)
- **通信方式**：`window.pywebview.api.<method>()` JS Bridge
- **图标**：Material Icons (Google Fonts) 或 Unicode 符号

## 二、色彩与视觉风格

### 色彩系统（白色主题）

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景主色 | `#FFFFFF` | 纯白背景 |
| 卡片/面板背景 | `#F5F5F7` | 极浅灰，柔和 |
| 侧边栏背景 | `#1A1A1A` | 深黑，突出导航 |
| 主文字 | `#1D1D1F` | 几乎纯黑 |
| 次要文字 | `#6E6E73` | 浅灰 |
| 强调色 / 按钮 | `#0071E3` | Apple 蓝，干净现代 |
| 强调色 Hover | `#0077ED` | 略亮 |
| 强调色 Active | `#005BB5` | 略暗 |
| 分割线 | `#D2D2D7` | 浅灰 |
| 成功 | `#34C759` | 绿色 |
| 警告 | `#FF9500` | 橙色 |
| 进度条 | `#0071E3 → #34C759` | 渐变 |

### 排版

- 字体：`-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif`
- 标题：`font-weight: 700`
- 正文：`font-weight: 400`
- 字号层级：`12px / 14px / 16px / 20px / 24px`

### 圆角与阴影

- 卡片圆角：`12px`
- 按钮圆角：`8px`
- 卡片阴影：`0 2px 10px rgba(0,0,0,0.06)`
- 悬浮阴影：`0 4px 20px rgba(0,0,0,0.1)`

## 三、布局结构

```
┌────────────────────────────────────────────────────┐
│                    标题栏 (标题+最小化/关闭)          │
├────────┬───────────────────────────────────────────┤
│        │                                           │
│ 侧边栏  │           主内容区域                        │
│  Logo  │  ┌──────────────────────────────┐         │
│        │  │   页面标题 + 功能描述          │         │
│ 功能1  │  ├──────────────────────────────┤         │
│ 功能2  │  │                               │         │
│ 功能3  │  │   功能特定内容区               │         │
│ 功能4  │  │                               │         │
│ 功能5  │  └──────────────────────────────┘         │
│        │                                           │
│        │  ┌──────────────────────────────┐         │
│        │  │   状态栏 (进度/日志)          │         │
│        │  └──────────────────────────────┘         │
├────────┴───────────────────────────────────────────┤
│                    状态栏 (Ollama 状态/版本)         │
└────────────────────────────────────────────────────┘
```

### 侧边栏 (240px)

- 固定宽度，深色背景
- 顶部：应用 Logo + 名称 "LightVideo"
- 导航项：5 个功能 + 分隔线 + "关于"
- 每个导航项包含：图标 + 文字
- 当前激活项有左侧白条指示器
- 底部：应用版本号

### 主内容区

- 可滚动，padding: 32px
- 顶部页面标题 + 简短说明
- 中间功能卡片/内容
- 底部状态栏（进度条 + 日志输出框）

## 四、组件设计

### 4.1 导航按钮 (侧边栏)

```css
/* 3D 立体感按钮 */
.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: rgba(255,255,255,0.7);
  border-radius: 8px;
  margin: 2px 8px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  /* 3D 效果通过 box-shadow 实现 */
  box-shadow: 0 1px 0 rgba(255,255,255,0.05);
}

.nav-item:hover {
  background: rgba(255,255,255,0.1);
  color: #FFFFFF;
  transform: translateX(4px);
}

.nav-item.active {
  background: rgba(255,255,255,0.15);
  color: #FFFFFF;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  background: #0071E3;
  border-radius: 0 3px 3px 0;
}
```

### 4.2 主要操作按钮

```css
/* 3D 蓝底白字按钮 */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: #0071E3;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  /* 3D 立体感 */
  box-shadow: 0 4px 0 #0055A4, 0 2px 8px rgba(0,113,227,0.3);
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary:hover {
  background: #0077ED;
  transform: translateY(-1px);
  box-shadow: 0 5px 0 #0055A4, 0 4px 12px rgba(0,113,227,0.4);
}

.btn-primary:active {
  transform: translateY(3px);
  box-shadow: 0 1px 0 #0055A4, 0 2px 4px rgba(0,113,227,0.2);
}
```

### 4.3 功能卡片 (通用)

```css
.card {
  background: #FFFFFF;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.06);
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}

.card:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  transform: translateY(-1px);
}
```

### 4.4 时间轴组件 (场景检测 / 目标追踪)

- 水平滚动条，标记时间点
- 每个标记点 hover 显示缩略图 + 描述
- 点击跳转到对应帧
- 使用 CSS `scroll-snap` 实现平滑滚动

### 4.5 章节卡片 (视频摘要)

- 垂直列表
- 每项：时间戳徽章 + 章节标题 + 描述文字
- 时间戳使用 `code` 样式，蓝底白字

### 4.6 文字列表 (文字提取)

- 分组展示：标题 / 字幕 / 场景文字 / 水印
- 使用标签(tag)区分不同类别
- 可点击复制

### 4.7 场景画廊 (场景检测)

- 网格布局，`grid-template-columns: repeat(auto-fill, minmax(200px, 1fr))`
- 每项：缩略图 + 时间戳 + 描述
- 缩略图有轻微缩放动画

### 4.8 进度条

```css
.progress-bar {
  width: 100%;
  height: 4px;
  background: #E5E5EA;
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #0071E3, #34C759);
  border-radius: 2px;
  transition: width 0.3s ease;
  width: 0%;
}
```

## 五、页面功能设计

### 5.1 首页 / 视频选择

- 拖拽/点击上传视频区域（大虚线框）
- 支持 `.mp4`, `.mov`, `.avi`, `.mkv`
- 选择后显示视频基本信息（时长、分辨率、大小）
- 五个功能卡片预览，点击进入对应功能

### 5.2 视频摘要 (功能一)

1. 选择视频 (或从首页带入)
2. 点击"生成摘要"按钮
3. 进度条显示处理进度 (采样中 → 分析中 → 完成)
4. 结果展示：
   - 标题 (大号字体)
   - 摘要正文 (多段落)
   - 章节列表 (时间戳 + 标题 + 描述)

### 5.3 文字提取 (功能二)

1. 选择视频
2. 点击"提取文字"
3. 进度反馈
4. 结果展示：
   - 按类别分 Tab (标题/字幕/场景文字/水印)
   - 每项显示时间戳 + 文字内容
   - 底部"复制全部"按钮

### 5.4 事件检索 (功能三)

1. 选择视频
2. 输入查询关键词 (文本框)
3. 选择灵敏度 (滑块: 低/中/高)
4. 可选：事件类型筛选 (下拉)
5. 点击"检索"
6. 结果展示：
   - 事件列表 (时间戳 + 描述 + 置信度进度条)
   - 点击事件可预览对应帧

### 5.5 场景检测 (功能四)

1. 选择视频
2. 点击"检测场景"
3. 进度反馈
4. 结果展示：
   - 顶部：场景总数 + 时间轴
   - 主体：场景画廊 (缩略图网格)
   - 每项 hover 显示描述
   - 点击展开详情

### 5.6 目标追踪 (功能五)

1. 选择视频
2. 输入目标描述 (例如 "红色的汽车"、"戴帽子的人")
3. 点击"追踪"
4. 进度反馈
5. 结果展示：
   - 出现时间段列表 (开始 → 结束)
   - 每个时间段可展开查看帧预览
   - 时间轴标记出现区间

## 六、JS Bridge 通信协议

### API 调用

所有后端功能通过 `window.pywebview.api` 调用：

```javascript
// 视频元数据
await api.get_video_metadata(videoPath);

// 功能一：视频摘要
await api.generate_summary(videoPath);

// 功能二：文字提取
await api.extract_text(videoPath);

// 功能三：事件检索
await api.retrieve_events(videoPath, query, sensitivity);

// 功能四：场景检测
await api.detect_scenes(videoPath, threshold);

// 功能五：目标追踪
await api.track_object(videoPath, target);
```

### 进度回调

后端通过 `api.on_progress(data)` 推送进度：

```javascript
// Python 端调用 (JS Bridge)
window.on_progress({
    stage: "sampling_frames",  // 当前阶段
    progress: 0.5,             // 0.0 ~ 1.0
    message: "正在采样帧...",   // 可读文本
    status: "running"          // running / completed / error
});
```

### 文件选择

通过 pywebview 的 file dialog：

```python
# Python 端
result = await window.create_file_dialog(
    pywebview.DIALOG.OPEN_FILE,
    "选择视频文件",
    filters=[("视频文件", "*.mp4 *.mov *.avi *.mkv")]
)
```

## 七、动画规范

| 场景 | 属性 | 时长 | 缓动函数 |
|------|------|------|----------|
| 按钮 hover | transform, box-shadow | 0.15s | ease |
| 按钮 active | transform | 0.1s | ease |
| 页面切换 | opacity | 0.3s | ease |
| 卡片 hover | box-shadow, transform | 0.3s | ease |
| 进度条 | width | 0.3s | ease |
| 导航项 hover | transform | 0.25s | cubic-bezier(0.4,0,0.2,1) |
| 缩略图 hover | transform: scale(1.05) | 0.2s | ease |
| 日志出现 | opacity | 0.2s | ease |

## 八、全局状态管理

使用 `window.AppState` 对象 (纯 JS)：

```javascript
window.AppState = {
    currentPage: 'home',
    currentVideo: null,
    videoMetadata: null,
    isProcessing: false,
    processingStage: '',
    progress: 0,
    logs: [],
    
    // 各功能结果缓存
    summaryResult: null,
    textResult: null,
    eventResult: null,
    sceneResult: null,
    trackResult: null
};
```

## 九、错误提示

- 使用 Toast 通知（右上角弹出，3 秒自动消失）
- 错误类型颜色：红色 (error) / 橙色 (warning)
- 严重错误显示模态确认框

```css
.toast {
  position: fixed;
  top: 16px;
  right: 16px;
  padding: 12px 20px;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  animation: slideIn 0.3s ease, slideOut 0.3s ease 2.7s forwards;
  z-index: 1000;
}

.toast-error { background: #FF3B30; }
.toast-warning { background: #FF9500; }
.toast-success { background: #34C759; }
```

## 十、首页示例布局

```
┌─────────────────────────────────────────────┐
│  LightVideo  —  轻量化视频理解工具           │
├─────────────────────────────────────────────┤
│  ┌───────────────────────────────────────┐  │
│  │      拖拽视频到此处，或点击选择文件      │  │
│  │      📁 选择视频文件                   │  │
│  │      支持 MP4 / MOV / AVI / MKV       │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐ │
│  │ 📝  │  │ 📄  │  │ 🔍  │  │ 🎬  │  │ 🎯  │ │
│  │视频  │  │文字  │  │事件  │  │场景  │  │目标  │ │
│  │摘要  │  │提取  │  │检索  │  │检测  │  │追踪  │ │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘ │
└─────────────────────────────────────────────┘
```
