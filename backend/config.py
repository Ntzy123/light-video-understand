"""全局配置 + 用户设置持久化"""

import os
import json

# ===== 后端模式 =====
API_BACKEND = "ollama"          # "ollama" | "minicpm_api" | "custom_api"

# ===== Ollama 配置 =====
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "minicpm-v4.6"
OLLAMA_TIMEOUT = 120  # 单次请求超时（秒）

# ===== API 配置 (MiniCPM 官方 API / 自定义 OpenAI 兼容 API) =====
API_KEY = "sk-pQ8L2zF3XmR5kY9wV4jB7hN1tC6vM0xG3aD5sH2bJ9lK4cZ8"  # MiniCPM 免费测试 Key
API_BASE_URL = "https://api.modelbest.cn/v1"
API_MODEL_NAME = "MiniCPM-V-4.6-Instruct"

# ===== 视频采样 =====
MAX_NUM_FRAMES = 12      # 最大采样帧数
CONTEXT_SIZE = 4096      # 模型上下文窗口大小（tokens），控制单次能发送的帧数
TOKENS_PER_FRAME = 600   # 每帧估算消耗的 token 数（含 base64 + 描述）
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

# ===== 用户设置持久化 =====
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lightvideo_settings.json")


def _cast(value, type_hint):
    """将值转换为指定类型"""
    if type_hint is bool:
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    if type_hint is int:
        return int(float(value)) if isinstance(value, str) else int(value)
    if type_hint is float:
        return float(value) if isinstance(value, str) else float(value)
    return value


def load_settings():
    """从 JSON 文件加载用户覆盖配置"""
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in data.items():
            if key in globals():
                orig = globals()[key]
                globals()[key] = _cast(value, type(orig))
    except Exception:
        pass


def save_settings(overlay: dict):
    """保存用户覆盖配置到 JSON 文件并更新内存"""
    allowed_keys = {"OLLAMA_URL", "MODEL_NAME", "OLLAMA_TIMEOUT", "TEMPERATURE",
                    "MAX_NUM_FRAMES", "CONTEXT_SIZE",
                    "API_BACKEND", "API_KEY", "API_BASE_URL", "API_MODEL_NAME"}
    to_persist = {}
    for key, value in overlay.items():
        if key in allowed_keys and key in globals():
            orig = globals()[key]
            casted = _cast(value, type(orig))
            globals()[key] = casted
            to_persist[key] = casted
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_persist, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# 模块导入时自动加载持久化设置
load_settings()
