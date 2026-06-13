"""场景切换检测与关键帧描述"""

from __future__ import annotations

import io
import base64
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

from .ollama_client import OllamaClient
from .video_processor import VideoProcessor
from . import config


# ----------------------------------------------------------------
# 数据类
# ----------------------------------------------------------------

@dataclass
class Scene:
    start_timestamp: str       # 场景开始时间 HH:MM:SS.mmm
    end_timestamp: str         # 场景结束时间
    duration_seconds: float    # 持续时长
    description: str           # 场景描述
    thumbnail: str             # 代表帧 base64
    frame_index: int           # 代表帧索引


@dataclass
class SceneResult:
    scenes: list[Scene] = field(default_factory=list)
    total_scenes: int = 0


# ----------------------------------------------------------------
# 场景检测模块
# ----------------------------------------------------------------

class SceneDetector:
    """场景切换检测器（SSIM 粗筛 + 模型语义描述）"""

    def __init__(self):
        self.client = OllamaClient()
        self.processor = VideoProcessor()

    def detect(
        self,
        video_path: str,
        threshold: float = None,
        on_progress: Optional[callable] = None,
    ) -> SceneResult:
        """检测视频中的场景切换

        Args:
            video_path: 视频文件路径
            threshold: SSIM 阈值 (0-1)，低于此值判定为场景切换
            on_progress: 进度回调
        Returns:
            SceneResult 对象
        """
        threshold = threshold if threshold is not None else config.SSIM_THRESHOLD

        self._emit_progress(on_progress, "scanning", 0.0, "正在扫描场景切分点...")

        # 步骤 1：SSIM 粗筛场景切分点
        cut_points = self._find_scene_cuts(video_path, threshold)

        self._emit_progress(on_progress, "building", 0.3, "正在构建场景列表...")

        # 步骤 2：构建场景列表
        meta = self.processor.get_metadata(video_path)
        fps = meta["fps"]
        total_frames = meta["total_frames"]

        scenes = self._build_scenes(cut_points, total_frames, fps)

        if not scenes:
            # 无切分点，整个视频为一个场景
            scenes = [{
                "start_frame": 0,
                "end_frame": total_frames - 1,
                "mid_frame": total_frames // 2,
            }]

        self._emit_progress(on_progress, "describing", 0.5, "正在生成场景描述...")

        # 步骤 3：获取代表帧并生成描述
        result_scenes = []
        total_scenes = len(scenes)

        # 分批获取描述（每批最多 8 帧）
        batch_size = 8
        for batch_start in range(0, total_scenes, batch_size):
            batch_end = min(batch_start + batch_size, total_scenes)
            batch_scenes = scenes[batch_start:batch_end]

            # 获取代表帧
            timestamps = []
            for s in batch_scenes:
                ts = s["mid_frame"] / fps if fps > 0 else 0
                timestamps.append(ts)

            frames = self.processor.sample_frames_by_timestamp(video_path, timestamps)

            for idx_in_batch, s in enumerate(batch_scenes):
                progress = 0.5 + 0.4 * ((batch_start + idx_in_batch + 1) / total_scenes)
                self._emit_progress(
                    on_progress, "describing",
                    progress,
                    f"正在描述场景 {batch_start + idx_in_batch + 1}/{total_scenes}...",
                )

                frame_img = frames[idx_in_batch] if idx_in_batch < len(frames) else None

                description = ""
                if frame_img:
                    description = self._describe_scene(frame_img)

                thumbnail_b64 = ""
                if frame_img:
                    thumbnail_b64 = self._pil_to_base64_thumbnail(frame_img)

                start_ts = self.processor.frame_index_to_timestamp(s["start_frame"], fps)
                end_ts = self.processor.frame_index_to_timestamp(s["end_frame"], fps)
                duration = (s["end_frame"] - s["start_frame"]) / fps if fps > 0 else 0

                scene = Scene(
                    start_timestamp=start_ts,
                    end_timestamp=end_ts,
                    duration_seconds=round(duration, 2),
                    description=description,
                    thumbnail=thumbnail_b64,
                    frame_index=s["mid_frame"],
                )
                result_scenes.append(scene)

        self._emit_progress(on_progress, "done", 1.0, "场景检测完成")

        return SceneResult(scenes=result_scenes, total_scenes=len(result_scenes))

    # ----------------------------------------------------------------
    # SSIM 切分点检测
    # ----------------------------------------------------------------

    def _find_scene_cuts(self, video_path: str, threshold: float) -> list[int]:
        """使用 SSIM 检测场景切分帧索引"""
        try:
            from skimage.metrics import structural_similarity as ssim
        except ImportError:
            raise ImportError("需要 scikit-image: pip install scikit-image")

        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = config.SSIM_FRAME_INTERVAL
        resize_w = config.SSIM_RESIZE_WIDTH

        cut_points = []
        prev_gray = None

        for frame_idx in range(0, total_frames, interval):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            aspect = w / h
            resize_h = int(resize_w / aspect)
            gray = cv2.resize(gray, (resize_w, resize_h))

            if prev_gray is not None and gray.shape == prev_gray.shape:
                score = ssim(prev_gray, gray, data_range=255)
                if score < threshold:
                    cut_points.append(frame_idx)

            prev_gray = gray

        cap.release()
        return cut_points

    # ----------------------------------------------------------------
    # 场景构建
    # ----------------------------------------------------------------

    @staticmethod
    def _build_scenes(
        cut_points: list[int], total_frames: int, fps: float
    ) -> list[dict]:
        """根据切分点构建场景列表"""
        if not cut_points:
            return [{
                "start_frame": 0,
                "end_frame": total_frames - 1,
                "mid_frame": total_frames // 2,
            }]

        min_gap = int(config.MIN_SCENE_DURATION * fps)

        # 合并邻近切分点
        merged = []
        for pt in cut_points:
            if merged and (pt - merged[-1]) < min_gap:
                continue
            merged.append(pt)

        scenes = []
        prev = 0
        for pt in merged:
            mid = (prev + pt) // 2
            scenes.append({
                "start_frame": prev,
                "end_frame": pt,
                "mid_frame": mid,
            })
            prev = pt

        # 最后一段
        if prev < total_frames - 1:
            mid = (prev + total_frames - 1) // 2
            scenes.append({
                "start_frame": prev,
                "end_frame": total_frames - 1,
                "mid_frame": mid,
            })

        return scenes

    # ----------------------------------------------------------------
    # 场景描述
    # ----------------------------------------------------------------

    def _describe_scene(self, frame: Image.Image) -> str:
        """用模型描述单帧场景内容"""
        prompt = "描述这张图片中场景的内容。请用一句话概括画面中发生的事或场景特点。"
        try:
            return self.client.chat_with_images([frame], prompt)
        except Exception:
            return ""

    # ----------------------------------------------------------------
    # 工具
    # ----------------------------------------------------------------

    @staticmethod
    def _pil_to_base64_thumbnail(img: Image.Image, max_size: int = 320) -> str:
        """转为 base64 缩略图"""
        img = img.copy()
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    @staticmethod
    def _emit_progress(cb, stage, progress, message):
        if cb:
            cb(stage, progress, message)
