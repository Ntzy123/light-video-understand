# 后端设计文档

## 一、全局配置 (`backend/config.py`)

```python
# Ollama 配置
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "minicpm-v4.6"
OLLAMA_TIMEOUT = 120  # 秒

# 视频采样
MAX_NUM_FRAMES = 32    # 最大采样帧数
SAMPLE_FPS_DIVISOR = 1  # 采样间隔 = avg_fps / divisor

# 文字提取
TEXT_BATCH_SIZE = 8    # 每批帧数

# 事件检索
EVENT_SEGMENT_MINUTES = 5  # 每段视频长度（分钟）

# 场景检测
SSIM_THRESHOLD = 0.7   # SSIM 场景切换阈值

# 目标追踪
TRACK_BATCH_SIZE = 8   # 每批帧数

# 重试
MAX_RETRIES = 3
RETRY_DELAY = 2        # 秒
```

## 二、Ollama 通信层 (`backend/ollama_client.py`)

### `OllamaClient` 类

核心职责：封装 Ollama REST API 调用，处理图片编码与错误重试。

#### 方法

**`chat_with_images(images: list[PIL.Image], prompt: str, system: str = None) -> str`**

- 将图片列表转为 base64 格式
- 构造 Ollama `/api/chat` 请求体
- 支持 `max_slice_nums` 参数传递
- 自动重试（最多 3 次，间隔 2 秒）
- 返回模型生成的文本

**`chat_text_only(prompt: str, system: str = None) -> str`**

- 纯文本对话，不含图片
- 用于某些不需要视觉输入的场景

#### 通信协议

```
POST /api/chat
{
  "model": "minicpm-v4.6",
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "image", "image": "<base64>"},
        {"type": "text",  "text": "<prompt>"}
      ]
    }
  ],
  "stream": false,
  "options": {
    "max_slice_nums": 2,
    "temperature": 0.1
  }
}
```

#### 错误处理

- `requests.Timeout` → 重试，超时递增
- `requests.ConnectionError` → 提示用户检查 Ollama 是否启动
- 非 200 响应 → 解析错误信息并抛出 `OllamaError`
- 图片编码异常 → 跳过问题帧

## 三、视频处理 (`backend/video_processor.py`)

### `VideoProcessor` 类

核心职责：视频解码、元数据提取、帧采样。

#### 方法

**`get_metadata(video_path: str) -> dict`**

返回：
```json
{
  "duration_seconds": 123.4,
  "fps": 30.0,
  "total_frames": 3702,
  "width": 1920,
  "height": 1080,
  "codec": "h264"
}
```

**`sample_frames(video_path: str, max_frames: int = 32) -> list[PIL.Image]`**

- 使用 decord 打开视频
- 计算采样间隔：`step = max(1, total_frames // max_frames)`
- 均匀采样 `max_frames` 帧
- 返回 PIL.Image 列表
- 若 decord 失败，回退到 opencv

**`sample_frames_by_timestamp(video_path: str, timestamps: list[float]) -> list[PIL.Image]`**

- 根据时间戳列表精确采样帧
- 用于场景检测和目标追踪中对特定时间点的帧获取

**`frame_index_to_timestamp(frame_idx: int, fps: float) -> str`**

- 将帧号转换为 `HH:MM:SS.mmm` 格式
- 辅助函数

**`video_to_segments(video_path: str, segment_minutes: int) -> list[dict]`**

- 将长视频切分为多个时间段
- 返回：每段开始时间戳、结束时间戳、帧列表

## 四、视频摘要与章节划分 (`backend/video_summarizer.py`)

### `VideoSummarizer` 类

依赖 `OllamaClient` 和 `VideoProcessor`。

#### `SummarizeResult` 数据类

```python
@dataclass
class SummarizeResult:
    title: str          # 视频标题
    summary: str        # 内容摘要（2-3 段）
    chapters: list[Chapter]  # 章节列表

@dataclass
class Chapter:
    timestamp: str      # HH:MM:SS 格式
    title: str          # 章节标题
    description: str    # 章节内容描述
```

#### `summarize(video_path: str, max_frames: int = 32) -> SummarizeResult`

处理流程：
1. 调用 `VideoProcessor.sample_frames()` 获取帧序列
2. 判断是否分段：若视频 > 10 分钟，分段处理
3. 构造 prompt，要求输出 JSON 格式
4. 调用 `OllamaClient.chat_with_images()`
5. 解析 JSON 响应 → `SummarizeResult`

**Prompt 设计**：

```
你是一个视频分析助手。以下是一段视频的 {n} 个关键帧图片。
请分析视频内容，用中文输出 JSON 格式：

{{
  "title": "视频标题（简短）",
  "summary": "视频内容摘要（2-3段话，覆盖主要内容）",
  "chapters": [
    {{"timestamp": "00:00", "title": "开场", "description": "..."}},
    {{"timestamp": "02:30", "title": "...", "description": "..."}}
  ]
}}

注意：
- timestamp 使用 MM:SS 或 HH:MM:SS 格式
- chapters 按时间顺序排列，时间戳基于帧对应的时间位置
- 不要输出 JSON 之外的额外文本
```

## 五、画面文字提取 (`backend/text_extractor.py`)

### `TextExtractor` 类

#### `TextExtractResult` 数据类

```python
@dataclass
class TextExtractResult:
    sections: list[TextSection]  # 文字段落列表
    full_text: str               # 合并后的完整文本

@dataclass
class TextSection:
    timestamp: str       # 出现时间
    text: str            # 文字内容
    category: str        # 分类: "title" / "subtitle" / "scene_text" / "watermark"
    frame_index: int     # 来源帧索引
```

#### `extract_all(video_path: str, batch_size: int = 8) -> TextExtractResult`

处理流程：
1. 均匀采样帧（按 `batch_size` 控制总批次数）
2. 每 8 帧一批发送到模型
3. 收集各批结果，全局去重（编辑距离 > 0.85 判相似）
4. 结构化分类

**Prompt**：

```
分析以下视频帧中的文字内容。请提取所有可见文字（包括标题、字幕、画面文字、水印等）。
以 JSON 格式输出，按时间顺序排列：

{{
  "frames": [
    {{
      "frame_index": 0,
      "texts": [
        {{"text": "...", "category": "scene_text"}},
        {{"text": "...", "category": "subtitle"}}
      ]
    }}
  ]
}}

categories: "title"(标题), "subtitle"(字幕), "scene_text"(场景文字), "watermark"(水印)
如果没有文字，返回 {{"frames": []}}
```

## 六、关键事件检索 (`backend/event_retriever.py`)

### `EventRetriever` 类

#### `EventResult` 数据类

```python
@dataclass
class EventResult:
    events: list[Event]        # 事件列表
    total_events: int          # 总事件数

@dataclass
class Event:
    timestamp: str             # 事件发生时间
    description: str           # 事件描述
    duration_seconds: float    # 持续时长
    confidence: float          # 置信度 0-1
    event_type: str            # 事件类型（根据 query 自动推断）
    key_frame_index: int       # 代表帧索引
```

#### `retrieve(video_path: str, query: str, sensitivity: float = 0.5, event_type: str = None) -> EventResult`

处理流程：
1. 将视频切分为 5 分钟段
2. 每段均匀采样 16 帧
3. 对每段发送模型询问是否有匹配事件
4. 聚合跨段事件，合并邻近事件
5. 输出结果

**Prompt**：

```
你正在监控视频中检索特定事件。
查询关键词：{query}

以下是一段 {duration} 秒视频的 16 个关键帧。
请判断这些帧中是否出现了与 "{query}" 相关的事件。

输出 JSON：
{{
  "has_event": true/false,
  "events": [
    {{
      "description": "事件描述",
      "timestamp_in_segment": 12.5,
      "confidence": 0.85,
      "event_type": "{query}",
      "key_frame_index": 3
    }}
  ]
}}

如果没有相关事件，has_event 设为 false，events 为空列表。
```

## 七、场景切换检测 (`backend/scene_detector.py`)

### `SceneDetector` 类

#### `SceneResult` 数据类

```python
@dataclass
class SceneResult:
    scenes: list[Scene]
    total_scenes: int

@dataclass
class Scene:
    start_timestamp: str       # 场景开始时间
    end_timestamp: str         # 场景结束时间
    duration_seconds: float    # 持续时长
    description: str           # 场景描述（由模型生成）
    thumbnail: str             # 代表帧 base64 (供前端直接显示)
    frame_index: int           # 代表帧索引
```

#### `detect(video_path: str, threshold: float = 0.7) -> SceneResult`

处理流程：
1. 使用 `opencv` 逐帧读取，每 5 帧计算一次 SSIM
2. 相邻帧 SSIM < threshold 标记为场景切分点
3. 合并相邻切分点（间隔 < 0.5 秒视为同一场景切换）
4. 对每个场景选取中间帧作为代表帧
5. 将代表帧发送到模型获取语义描述
   - 若场景数量 > 10，分批发送，每批最多 8 帧
6. 聚合结果

**CV 粗筛说明**：

```python
# 使用 scikit-image 的 structural_similarity
from skimage.metrics import structural_similarity as ssim
# 转灰度 → resize 到固定尺寸 → ssim 计算
# 比直方图更准确，比深度学习更轻量
```

**模型 prompt**：

```
描述这张图片中场景的内容。请用一句话概括画面中发生的事或场景特点。
```

## 八、目标对象出现时间标记 (`backend/object_tracker.py`)

### `ObjectTracker` 类

#### `TrackResult` 数据类

```python
@dataclass
class TrackResult:
    appearances: list[Appearance]
    total_appearances: int

@dataclass
class Appearance:
    start_timestamp: str       # 首次出现时间
    end_timestamp: str         # 最后出现时间
    frames_with_object: list[int]  # 出现帧索引列表
    description: str           # 模型描述
```

#### `track(video_path: str, target: str, batch_size: int = 8) -> TrackResult`

处理流程：
1. 均匀采样帧（密度 = 1 fps）
2. 每 8 帧一批发送到模型
3. 询问每批中目标对象是否出现
4. 聚合连续出现时间段
5. 去重相邻帧出现的重复描述

**Prompt**：

```
以下是一段视频中的 8 帧截图。请判断目标 "{target}" 
是否出现在这些帧中。

输出 JSON：
{{
  "appears": true/false,
  "frame_indices": [0, 1, 3],  # 出现该目标的帧索引（相对本批）
  "description": "目标出现的描述"
}}

如果目标没有出现，appears 设为 false，frame_indices 为空列表。
```

## 九、异常处理统一规范

| 异常类型 | 检测方式 | 处理方式 |
|----------|----------|----------|
| 视频文件损坏 | decord/opencv 打开失败 | 抛出 `VideoError`，前端提示 |
| Ollama 未启动 | `requests.ConnectionError` | 抛出 `OllamaConnectionError`，前端提示 |
| 模型响应超时 | requests 超时 | 重试 3 次，间隔递增；失败后回退 |
| GPU OOM | 模型返回错误 / 进程 crash | 减少帧数重试 |
| JSON 解析失败 | `json.JSONDecodeError` | 使用正则提取 JSON，失败则返回原始文本 |
| 空视频 / 零帧 | 帧数为 0 | 抛出 `VideoError("视频无有效帧")` |

所有业务模块均继承自定义 `BaseModule`：

```python
class BaseModule:
    def __init__(self):
        self.client = OllamaClient()
        self.processor = VideoProcessor()
    
    def _safe_parse_json(self, text: str) -> dict:
        """安全解析模型输出的 JSON"""
        ...
```
