"""全局配置"""

# ===== Ollama 配置 =====
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "minicpm-v4.6"
OLLAMA_TIMEOUT = 120  # 单次请求超时（秒）

# ===== 视频采样 =====
MAX_NUM_FRAMES = 32      # 最大采样帧数
SAMPLE_FPS_DIVISOR = 1   # 采样间隔 = avg_fps / divisor

# ===== 文字提取 =====
TEXT_BATCH_SIZE = 8      # 每批帧数

# ===== 事件检索 =====
EVENT_SEGMENT_MINUTES = 5   # 每段视频长度（分钟）
EVENT_FRAMES_PER_SEGMENT = 16  # 每段采样帧数

# ===== 场景检测 =====
SSIM_THRESHOLD = 0.7     # SSIM 场景切换阈值
SSIM_FRAME_INTERVAL = 5  # 每隔 N 帧计算一次 SSIM
SSIM_RESIZE_WIDTH = 320  # SSIM 计算时缩放的宽度
MIN_SCENE_DURATION = 0.5 # 最小场景持续时长（秒）

# ===== 目标追踪 =====
TRACK_BATCH_SIZE = 8     # 每批帧数
TRACK_FPS = 1            # 目标追踪采样帧率

# ===== 重试 =====
MAX_RETRIES = 3
RETRY_DELAY = 2          # 重试间隔（秒）

# ===== 模型参数 =====
TEMPERATURE = 0.1
MAX_SLICE_NUMS = 2
