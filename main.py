"""LightVideo - 轻量化视频理解工具入口"""

import os
import sys
import threading
import json
import webview

from backend.video_processor import VideoProcessor
from backend.video_summarizer import VideoSummarizer
from backend.text_extractor import TextExtractor
from backend.event_retriever import EventRetriever
from backend.scene_detector import SceneDetector
from backend.object_tracker import ObjectTracker
from backend.model_client import ModelClient
from backend import config


class Api:
    """pywebview JS Bridge 接口类"""

    def __init__(self):
        self.processor = VideoProcessor()
        self.summarizer = VideoSummarizer()
        self.extractor = TextExtractor()
        self.retriever = EventRetriever()
        self.detector = SceneDetector()
        self.tracker = ObjectTracker()
        self._progress_callback = None

    # ================================================================
    # 基础功能
    # ================================================================

    def check_ollama(self) -> dict:
        """检测模型后端服务状态及模型可用性"""
        client = ModelClient()
        ok = client.check_connection()
        model_name = config.MODEL_NAME if config.API_BACKEND == "ollama" else config.API_MODEL_NAME
        if not ok:
            return {"available": False, "model": model_name, "model_available": False, "backend": config.API_BACKEND}
        model_ok = client.check_model_available()
        return {
            "available": True,
            "model": model_name,
            "model_available": model_ok,
            "backend": config.API_BACKEND,
        }

    def get_config(self) -> dict:
        """获取当前配置"""
        return {
            "api_backend": config.API_BACKEND,
            "ollama_url": config.OLLAMA_URL,
            "model_name": config.MODEL_NAME,
            "ollama_timeout": config.OLLAMA_TIMEOUT,
            "temperature": config.TEMPERATURE,
            "max_num_frames": config.MAX_NUM_FRAMES,
            "context_size": config.CONTEXT_SIZE,
            "tokens_per_frame": config.TOKENS_PER_FRAME,
            "api_key": config.API_KEY,
            "api_base_url": config.API_BASE_URL,
            "api_model_name": config.API_MODEL_NAME,
        }

    def save_config(self, cfg: str) -> dict:
        """保存配置（接收 JSON 字符串）"""
        try:
            data = json.loads(cfg)
            config.save_settings(data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_video_metadata(self, video_path: str) -> dict:
        """获取视频元数据"""
        return self.processor.get_metadata(video_path)

    def select_video_file(self) -> dict:
        """打开系统文件选择对话框（由 pywebview 前端调用）"""
        try:
            w = self._window if hasattr(self, '_window') and self._window else webview.active_window()
            result = w.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=('Video Files (*.mp4;*.mov;*.avi;*.mkv;*.webm)',),
            )
            if result and len(result) > 0:
                return {"selected": True, "path": result[0]}
            return {"selected": False, "path": ""}
        except Exception:
            return {"selected": False, "path": ""}

    # ================================================================
    # 功能一：视频摘要
    # ================================================================

    def generate_summary(self, video_path: str) -> str:
        """生成视频摘要（返回 JSON 字符串）"""
        result = self.summarizer.summarize(
            video_path,
            on_progress=self._on_progress,
        )
        return json.dumps({
            "success": True,
            "data": {
                "title": result.title,
                "summary": result.summary,
                "chapters": [
                    {"timestamp": c.timestamp, "title": c.title, "description": c.description}
                    for c in result.chapters
                ],
            },
        })

    # ================================================================
    # 功能二：文字提取
    # ================================================================

    def extract_text(self, video_path: str) -> str:
        """提取画面文字（返回 JSON 字符串）"""
        result = self.extractor.extract_all(
            video_path,
            on_progress=self._on_progress,
        )
        return json.dumps({
            "success": True,
            "data": {
                "full_text": result.full_text,
                "sections": [
                    {
                        "timestamp": s.timestamp,
                        "text": s.text,
                        "category": s.category,
                        "frame_index": s.frame_index,
                    }
                    for s in result.sections
                ],
            },
        })

    # ================================================================
    # 功能三：事件检索
    # ================================================================

    def retrieve_events(self, video_path: str, query: str, sensitivity: float = 0.5) -> str:
        """检索关键事件（返回 JSON 字符串）"""
        result = self.retriever.retrieve(
            video_path,
            query=query,
            sensitivity=sensitivity,
            on_progress=self._on_progress,
        )
        return json.dumps({
            "success": True,
            "data": {
                "total_events": result.total_events,
                "events": [
                    {
                        "timestamp": e.timestamp,
                        "description": e.description,
                        "duration_seconds": e.duration_seconds,
                        "confidence": e.confidence,
                        "event_type": e.event_type,
                        "key_frame_index": e.key_frame_index,
                    }
                    for e in result.events
                ],
            },
        })

    # ================================================================
    # 功能四：场景检测
    # ================================================================

    def detect_scenes(self, video_path: str) -> str:
        """检测场景切换（返回 JSON 字符串）"""
        result = self.detector.detect(
            video_path,
            on_progress=self._on_progress,
        )
        return json.dumps({
            "success": True,
            "data": {
                "total_scenes": result.total_scenes,
                "scenes": [
                    {
                        "start_timestamp": s.start_timestamp,
                        "end_timestamp": s.end_timestamp,
                        "duration_seconds": s.duration_seconds,
                        "description": s.description,
                        "thumbnail": s.thumbnail,
                        "frame_index": s.frame_index,
                    }
                    for s in result.scenes
                ],
            },
        })

    # ================================================================
    # 功能五：目标追踪
    # ================================================================

    def track_object(self, video_path: str, target: str) -> str:
        """追踪目标对象（返回 JSON 字符串）"""
        result = self.tracker.track(
            video_path,
            target=target,
            on_progress=self._on_progress,
        )
        return json.dumps({
            "success": True,
            "data": {
                "total_appearances": result.total_appearances,
                "appearances": [
                    {
                        "start_timestamp": a.start_timestamp,
                        "end_timestamp": a.end_timestamp,
                        "frames_with_object": a.frames_with_object,
                        "description": a.description,
                    }
                    for a in result.appearances
                ],
            },
        })

    # ================================================================
    # 进度回调（由后端模块调用 -> 推送给前端）
    # ================================================================

    def _on_progress(self, stage: str, progress: float, message: str):
        """后端模块的进度回调，通过 JS Bridge 推送给前端"""
        try:
            if hasattr(self, '_window') and self._window:
                self._window.evaluate_js(
                    f'window.onProgress({json.dumps({"stage": stage, "progress": progress, "message": message})})'
                )
        except Exception:
            pass

    def set_window(self, w):
        """设置窗口引用，用于推送进度"""
        self._window = w


def get_resource_path(relative_path: str) -> str:
    """获取资源文件路径（支持 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def main():
    """启动 LightVideo 应用"""
    api = Api()

    # 从本地加载前端页面
    frontend_path = get_resource_path("frontend")
    index_url = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_url):
        url = index_url
    else:
        # 打包后 frontend 目录缺失时的应急 fallback（内联完整页面）
        url = "data:text/html,<h1>LightVideo</h1><div>前端页面尚未创建，请确认打包时已包含 frontend 目录</div>"

    window = webview.create_window(
        title="LightVideo - 轻量化视频理解",
        url=url,
        js_api=api,
        width=1200,
        height=800,
        min_size=(900, 600),
        resizable=True,
    )

    api.set_window(window)

    # 打包版不启动 devtools，python 直跑时启动
    is_packaged = getattr(sys, 'frozen', False)
    webview.start(debug=not is_packaged)


if __name__ == '__main__':
    main()
