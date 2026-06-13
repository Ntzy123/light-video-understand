"""视频解码与帧采样"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
from PIL import Image

from . import config


class VideoError(Exception):
    """视频处理相关异常"""
    pass


class VideoProcessor:
    """视频解码、元数据提取、帧采样"""

    # ----------------------------------------------------------------
    # 元数据
    # ----------------------------------------------------------------

    def get_metadata(self, video_path: str) -> dict:
        """获取视频基本信息"""
        if not os.path.isfile(video_path):
            raise VideoError(f"视频文件不存在: {video_path}")

        vr = self._open_video(video_path)
        try:
            fps = float(vr.get_avg_fps())
            total_frames = len(vr)
            duration = total_frames / fps if fps > 0 else 0
            width, height = 0, 0
            if len(vr) > 0:
                frame = vr[0]
                if hasattr(frame, "shape"):
                    h, w = frame.shape[:2]
                    width, height = w, h

            return {
                "duration_seconds": round(duration, 2),
                "fps": round(fps, 2),
                "total_frames": total_frames,
                "width": int(width),
                "height": int(height),
                "codec": "unknown",  # decord 不直接提供 codec
            }
        finally:
            self._close_video(vr)

    # ----------------------------------------------------------------
    # 帧采样
    # ----------------------------------------------------------------

    def sample_frames(
        self, video_path: str, max_frames: int = None
    ) -> list[Image.Image]:
        """均匀采样视频帧

        Args:
            video_path: 视频路径
            max_frames: 最多采样帧数，默认 config.MAX_NUM_FRAMES
        Returns:
            PIL.Image 列表
        """
        max_frames = max_frames or config.MAX_NUM_FRAMES
        vr = self._open_video(video_path)
        try:
            total = len(vr)
            if total == 0:
                raise VideoError("视频无有效帧")

            # 计算采样索引
            if total <= max_frames:
                indices = list(range(total))
            else:
                step = total / max_frames
                indices = [min(int(i * step + step / 2), total - 1) for i in range(max_frames)]

            return self._get_frames(vr, indices)
        finally:
            self._close_video(vr)

    def sample_frames_by_timestamp(
        self, video_path: str, timestamps: list[float]
    ) -> list[Image.Image]:
        """根据时间戳列表精确采样帧

        Args:
            video_path: 视频路径
            timestamps: 秒为单位的时间戳列表
        Returns:
            PIL.Image 列表
        """
        vr = self._open_video(video_path)
        try:
            fps = float(vr.get_avg_fps())
            indices = [min(int(ts * fps), len(vr) - 1) for ts in timestamps if ts >= 0]
            indices = sorted(set(indices))
            return self._get_frames(vr, indices)
        finally:
            self._close_video(vr)

    def sample_frames_uniform_by_count(
        self, video_path: str, count: int
    ) -> list[Image.Image]:
        """均匀采样指定数量的帧（严格 count 帧）"""
        vr = self._open_video(video_path)
        try:
            total = len(vr)
            if total == 0:
                raise VideoError("视频无有效帧")
            if count <= 0:
                return []

            step = max(1, total // count)
            indices = [min(i * step, total - 1) for i in range(count)]
            indices = indices[:count]

            return self._get_frames(vr, indices)
        finally:
            self._close_video(vr)

    # ----------------------------------------------------------------
    # 分段
    # ----------------------------------------------------------------

    def video_to_segments(
        self, video_path: str, segment_minutes: int = None
    ) -> list[dict]:
        """将视频切分为多个时间段（返回元信息，不含帧数据）"""
        segment_minutes = segment_minutes or config.EVENT_SEGMENT_MINUTES
        meta = self.get_metadata(video_path)
        total_seconds = meta["duration_seconds"]
        segment_seconds = segment_minutes * 60
        segments = []

        start = 0.0
        idx = 0
        while start < total_seconds:
            end = min(start + segment_seconds, total_seconds)
            segments.append({
                "index": idx,
                "start_seconds": round(start, 2),
                "end_seconds": round(end, 2),
                "duration": round(end - start, 2),
            })
            start = end
            idx += 1

        return segments

    # ----------------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------------

    @staticmethod
    def calculate_max_frames(user_max_frames: int = None) -> int:
        """根据上下文窗口自动计算单次能发送的最大帧数"""
        import math
        ctx = config.CONTEXT_SIZE
        tokens_per_frame = config.TOKENS_PER_FRAME
        prompt_budget = 500  # 预留 prompt + 回复 token
        frame_budget = max(1, ctx - prompt_budget)
        ctx_limit = max(1, frame_budget // tokens_per_frame)
        user_limit = user_max_frames or config.MAX_NUM_FRAMES
        return min(user_limit, ctx_limit)

    @staticmethod
    def estimate_segment_duration(total_seconds: float, max_frames: int) -> float:
        """估算小上下文下每段视频应裁切的时长（秒），保证每段帧数 ≤ max_frames"""
        frames_needed = min(max_frames * 3, max_frames + 10)  # 每段想放约 max_frames 帧
        if total_seconds <= 0:
            return 600
        seg_seconds = max(30, total_seconds / max(1, frames_needed) * max_frames)
        return min(seg_seconds, 600)  # 最长不超过 10 分钟
        """将帧号转为 HH:MM:SS.mmm 格式"""
        if fps <= 0:
            return "00:00:00.000"
        total_seconds = frame_idx / fps
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        millis = int((total_seconds - int(total_seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    @staticmethod
    def seconds_to_timestamp(seconds: float) -> str:
        """将秒数转为 HH:MM:SS.mmm 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    # ----------------------------------------------------------------
    # 内部：decord / opencv 双引擎
    # ----------------------------------------------------------------

    def _open_video(self, path: str):
        """尝试用 decord 打开视频，失败回退 opencv"""
        # 优先 decord
        try:
            from decord import VideoReader, cpu
            return VideoReader(path, ctx=cpu(0))
        except Exception:
            pass
        # 回退 opencv
        try:
            import cv2
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                raise VideoError(f"无法打开视频文件: {path}")
            return _OpenCVVideoReader(cap)
        except Exception as e:
            raise VideoError(f"视频解码失败 (decord + opencv 均失败): {e}")

    def _close_video(self, vr):
        """关闭视频读取器"""
        if hasattr(vr, "release"):
            vr.release()

    def _get_frames(self, vr, indices: list[int]) -> list[Image.Image]:
        """根据索引列表获取帧并转为 PIL.Image"""
        if hasattr(vr, "get_batch"):
            batch = vr.get_batch(indices)
            if hasattr(batch, "asnumpy"):
                # decord NDArray
                batch = batch.asnumpy()
                return [Image.fromarray(f.astype("uint8")) for f in batch]
            # OpenCV _OpenCVVideoReader.get_batch 已返回 list[Image.Image]
            return batch
        else:
            # 兼容无 get_batch 的读取器（逐个读取）
            return [vr.get_frame(i) for i in indices]


class _OpenCVVideoReader:
    """OpenCV 视频读取器包装（兼容 decord 的基本接口）"""

    def __init__(self, cap):
        import cv2
        self._cap = cap
        self._total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._fps = cap.get(cv2.CAP_PROP_FPS)

    def get_avg_fps(self):
        return self._fps

    def __len__(self):
        return self._total_frames

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return self.get_batch(range(idx.start or 0, idx.stop or len(self), idx.step or 1))
        return self.get_batch([idx])

    def get_batch(self, indices):
        import cv2
        frames = []
        for i in indices:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = self._cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(Image.fromarray(rgb))
            else:
                # 读取失败时补空白帧
                frames.append(Image.new("RGB", (640, 480), (0, 0, 0)))
        return frames

    def get_frame(self, idx):
        frames = self.get_batch([idx])
        return frames[0] if frames else None

    def release(self):
        self._cap.release()
