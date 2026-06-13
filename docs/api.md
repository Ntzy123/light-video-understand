# LightVideo 后端 API 接口文档

> 前端通过 `window.pywebview.api.<method>()` 与后端通信。
> 所有方法返回 JSON 字符串（除 `select_video_file` 和 `check_ollama` 外均为异步）。

---

## 一、基础接口

### 1.1 `check_ollama()`

检测 Ollama 服务是否可用。

**返回：**
```json
{
  "available": true,
  "model": "minicpm-v4.6"
}
```

### 1.2 `get_video_metadata(video_path)`

获取视频文件的基本信息。

**参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| video_path | string | 视频文件绝对路径 |

**返回：**
```json
{
  "duration_seconds": 123.45,
  "fps": 30.0,
  "total_frames": 3702,
  "width": 1920,
  "height": 1080,
  "codec": "unknown"
}
```

### 1.3 `select_video_file()`

打开系统文件选择对话框，让用户选择视频文件。

**返回：**
```json
{
  "selected": true,
  "path": "C:/videos/demo.mp4"
}
```

未选择时：
```json
{
  "selected": false,
  "path": ""
}
```

---

## 二、功能一：视频摘要 `generate_summary(video_path)`

### 请求

```javascript
const result = await api.generate_summary("/path/to/video.mp4");
```

**参数：**
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| video_path | string | — | 视频文件绝对路径 |

**返回（JSON 字符串 → 解析后）：**
```json
{
  "success": true,
  "data": {
    "title": "产品发布会记录",
    "summary": "这是一段产品发布会的视频记录...",
    "chapters": [
      {
        "timestamp": "00:00",
        "title": "开场",
        "description": "主持人登台介绍活动背景"
      },
      {
        "timestamp": "05:30",
        "title": "产品介绍",
        "description": "产品经理演示新功能介绍"
      }
    ]
  }
}
```

### 进度通知

处理过程中，后端会通过 `window.onProgress()` 推送进度：

```javascript
window.onProgress = function(data) {
  console.log(data.stage, data.progress, data.message);
  // data.stage: "extracting_metadata" | "sampling_frames" | "analyzing" | "done"
  // data.progress: 0.0 ~ 1.0
  // data.message: "可读进度描述"
};
```

### 错误响应

```json
{
  "success": false,
  "error": "视频文件不存在..."
}
```

---

## 三、功能二：文字提取 `extract_text(video_path)`

### 请求

```javascript
const result = await api.extract_text("/path/to/video.mp4");
```

**返回：**
```json
{
  "success": true,
  "data": {
    "full_text": "[00:00:00.000] (title) 新闻联播\n[00:00:15.500] (subtitle) 欢迎收看...",
    "sections": [
      {
        "timestamp": "00:00:00.000",
        "text": "新闻联播",
        "category": "title",
        "frame_index": 0
      },
      {
        "timestamp": "00:00:15.500",
        "text": "欢迎收看今天的新闻联播",
        "category": "subtitle",
        "frame_index": 15
      }
    ]
  }
}
```

### 分类说明

| 分类值 | 说明 |
|--------|------|
| `title` | 标题文字 |
| `subtitle` | 字幕/旁白文字 |
| `scene_text` | 画面中的场景文字（招牌、PPT 等） |
| `watermark` | 水印文字 |

---

## 四、功能三：事件检索 `retrieve_events(video_path, query, sensitivity)`

### 请求

```javascript
const result = await api.retrieve_events(
  "/path/to/video.mp4",
  "行人横穿马路",
  0.6
);
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| video_path | string | — | 视频文件绝对路径 |
| query | string | — | 事件查询关键词/描述 |
| sensitivity | number | 0.5 | 检索灵敏度 (0.0 ~ 1.0)，越高越容易检出 |

**返回：**
```json
{
  "success": true,
  "data": {
    "total_events": 3,
    "events": [
      {
        "timestamp": "00:12:30.000",
        "description": "一名行人从画面右侧横穿马路",
        "duration_seconds": 4.5,
        "confidence": 0.85,
        "event_type": "行人横穿马路",
        "key_frame_index": 375
      }
    ]
  }
}
```

---

## 五、功能四：场景检测 `detect_scenes(video_path)`

### 请求

```javascript
const result = await api.detect_scenes("/path/to/video.mp4");
```

**返回：**
```json
{
  "success": true,
  "data": {
    "total_scenes": 8,
    "scenes": [
      {
        "start_timestamp": "00:00:00.000",
        "end_timestamp": "00:01:23.500",
        "duration_seconds": 83.5,
        "description": "演播室场景，主持人坐在桌前播报新闻",
        "thumbnail": "/9j/4AAQ...base64...",
        "frame_index": 0
      },
      {
        "start_timestamp": "00:01:23.500",
        "end_timestamp": "00:03:45.000",
        "duration_seconds": 141.5,
        "description": "外景采访，记者在街头进行采访",
        "thumbnail": "/9j/4AAQ...base64...",
        "frame_index": 125
      }
    ]
  }
}
```

> `thumbnail` 字段为 JPEG base64 编码，前端可直接用作 `<img src="data:image/jpeg;base64,...">`。

---

## 六、功能五：目标追踪 `track_object(video_path, target)`

### 请求

```javascript
const result = await api.track_object(
  "/path/to/video.mp4",
  "红色汽车"
);
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| video_path | string | — | 视频文件绝对路径 |
| target | string | — | 目标对象描述（如 "戴帽子的人"、"红色的汽车"） |

**返回：**
```json
{
  "success": true,
  "data": {
    "total_appearances": 2,
    "appearances": [
      {
        "start_timestamp": "00:02:15.000",
        "end_timestamp": "00:02:45.000",
        "frames_with_object": [135, 136, 138, 140],
        "description": "一辆红色汽车从画面左侧驶入",
      },
      {
        "start_timestamp": "00:05:30.000",
        "end_timestamp": "00:06:10.000",
        "frames_with_object": [330, 332, 335],
        "description": "红色汽车停在路边",
      }
    ]
  }
}
```

---

## 七、进度通知协议

所有功能模块在处理过程中均会通过 `window.onProgress()` 推送进度。

### 前端注册

```javascript
// 在页面加载时注册
window.onProgress = function(data) {
  const { stage, progress, message } = data;
  // stage: 当前阶段标识
  // progress: 0.0 ~ 1.0
  // message: 可读文本
  
  // 更新进度条
  updateProgressBar(progress);
  // 显示状态信息
  showStatus(message);
};
```

### 各功能进度阶段

| 功能 | stage 值 | 说明 |
|------|----------|------|
| 视频摘要 | `extracting_metadata` → `sampling_frames` → `analyzing` → `done` | — |
| 文字提取 | `extracting_metadata` → `extracting` → `done` | extracting 会重复多次 |
| 事件检索 | `preparing` → `searching` → `done` | searching 每个分段一次 |
| 场景检测 | `scanning` → `building` → `describing` → `done` | describing 每个场景一次 |
| 目标追踪 | `sampling` → `tracking` → `done` | tracking 每批一次 |

---

## 八、错误处理

所有接口在失败时返回：
```json
{
  "success": false,
  "error": "错误描述信息"
}
```

### 常见错误

| 错误信息 | 原因 | 处理建议 |
|----------|------|----------|
| 视频文件不存在: xxx | 路径无效 | 检查文件路径 |
| 视频无有效帧 | 视频损坏或格式不支持 | 使用其他播放器验证视频 |
| 无法连接到 Ollama 服务... | Ollama 未启动 | 启动 Ollama (`ollama serve`) |
| 请求超时 | 模型处理时间过长 | 检查显存或减小帧数 |
| 无法解析模型输出的 JSON | 模型输出格式异常 | 可尝试重新运行 |
