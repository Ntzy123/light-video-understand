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
from backend.ollama_client import OllamaClient
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
        """检测 Ollama 服务状态"""
        client = OllamaClient()
        ok = client.check_connection()
        return {"available": ok, "model": config.MODEL_NAME}

    def get_video_metadata(self, video_path: str) -> dict:
        """获取视频元数据"""
        return self.processor.get_metadata(video_path)

    def select_video_file(self) -> dict:
        """打开系统文件选择对话框（由 pywebview 前端调用）"""
        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                "选择视频文件",
                filters=[("视频文件", "*.mp4 *.mov *.avi *.mkv *.webm")],
            )
            if result:
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
        url = "data:text/html,<h1>LightVideo</h1><p>前端页面尚未创建</p>"

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

    # 检测 Ollama
    client = OllamaClient()
    if not client.check_connection():
        print("⚠ 未检测到 Ollama 服务，请确保 Ollama 已启动")

    webview.start(debug=True)


if __name__ == '__main__':
    main()
