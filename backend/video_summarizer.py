"""视频内容摘要与章节划分"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from typing import Optional

from .ollama_client import OllamaClient, OllamaError
from .video_processor import VideoProcessor, VideoError
from . import config


# ----------------------------------------------------------------
# 数据类
# ----------------------------------------------------------------

@dataclass
class Chapter:
    timestamp: str      # HH:MM:SS 格式
    title: str          # 章节标题
    description: str    # 章节内容描述


@dataclass
class SummarizeResult:
    title: str                          # 视频标题
    summary: str                        # 内容摘要
    chapters: list[Chapter] = field(default_factory=list)  # 章节列表


# ----------------------------------------------------------------
# 摘要模块
# ----------------------------------------------------------------

class VideoSummarizer:
    """视频摘要生成器"""

    def __init__(self):
        self.client = OllamaClient()
        self.processor = VideoProcessor()

    def summarize(
        self,
        video_path: str,
        max_frames: int = None,
        on_progress: Optional[callable] = None,
    ) -> SummarizeResult:
        """生成视频摘要与章节划分

        Args:
            video_path: 视频文件路径
            max_frames: 最大采样帧数
            on_progress: 进度回调函数(stage: str, progress: float, message: str)
        Returns:
            SummarizeResult 对象
        """
        self._emit_progress(on_progress, "extracting_metadata", 0.0, "正在读取视频信息...")
        meta = self.processor.get_metadata(video_path)
        duration = meta["duration_seconds"]

        max_frames = max_frames or config.MAX_NUM_FRAMES

        # 长视频分段处理
        if duration > 600:  # >10 分钟
            return self._summarize_long(video_path, meta, max_frames, on_progress)

        self._emit_progress(on_progress, "sampling_frames", 0.2, "正在采样帧...")
        frames = self.processor.sample_frames(video_path, max_frames)

        if not frames:
            raise VideoError("视频无有效帧，无法生成摘要")

        self._emit_progress(on_progress, "analyzing", 0.4, "正在分析视频内容...")

        prompt = (
            f"你是一个视频分析助手。以下是一段视频的 {len(frames)} 个关键帧图片。\n"
            f"请分析视频内容，用中文输出 JSON 格式：\n\n"
            f'{{\n'
            f'  "title": "视频标题（简短，10字以内）",\n'
            f'  "summary": "视频内容摘要（2-3段话，覆盖主要内容）",\n'
            f'  "chapters": [\n'
            f'    {{"timestamp": "00:00", "title": "开场", "description": "..."}},\n'
            f'    {{"timestamp": "02:30", "title": "...", "description": "..."}}\n'
            f'  ]\n'
            f'}}\n\n'
            f'注意：\n'
            f'- timestamp 使用 MM:SS 或 HH:MM:SS 格式\n'
            f'- chapters 按时间顺序排列，时间戳基于帧对应的时间位置\n'
            f'- 不要输出 JSON 之外的额外文本'
        )

        response = self.client.chat_with_images(frames, prompt)
        data = self.client._safe_parse_json(response)

        self._emit_progress(on_progress, "done", 1.0, "摘要生成完成")

        return self._parse_summarize_result(data)

    def _summarize_long(
        self,
        video_path: str,
        meta: dict,
        max_frames: int,
        on_progress: Optional[callable],
    ) -> SummarizeResult:
        """长视频分段摘要"""
        segments = self.processor.video_to_segments(video_path, 10)  # 10分钟一段
        segment_results = []
        total = len(segments)

        for i, seg in enumerate(segments):
            progress = 0.2 + 0.6 * (i / total)
            self._emit_progress(
                on_progress, "analyzing",
                progress,
                f"正在分析第 {i+1}/{total} 段 ({seg['start_seconds']}s - {seg['end_seconds']}s)...",
            )

            frames_per_seg = max(4, max_frames // total)
            indices = self._segment_frame_indices(
                video_path, seg["start_seconds"], seg["end_seconds"], frames_per_seg,
            )
            frames = self.processor.sample_frames_by_timestamp(video_path, indices)

            prompt = (
                f"以下是视频中 {self.processor.seconds_to_timestamp(seg['start_seconds'])} "
                f"到 {self.processor.seconds_to_timestamp(seg['end_seconds'])} 段的 {len(frames)} 个关键帧。\n"
                f"请用中文 JSON 格式总结这一小段的内容：\n"
                f'{{"summary": "段落内容描述", "chapters": [{{"timestamp": "相对本段开始的时间", "title": "...", "description": "..."}}]}}'
            )
            resp = self.client.chat_with_images(frames, prompt)
            try:
                seg_data = self.client._safe_parse_json(resp)
                segment_results.append(seg_data)
            except OllamaError:
                segment_results.append({"summary": "", "chapters": []})

        # 合并结果
        all_chapters = []
        summaries = []
        for i, seg_data in enumerate(segment_results):
            if seg_data.get("summary"):
                summaries.append(
                    f"【第 {i+1} 段】{seg_data['summary']}"
                )
            for ch in seg_data.get("chapters", []):
                # 调整时间戳为全局时间
                base_seconds = segments[i]["start_seconds"]
                ch_seconds = self._parse_timestamp_to_seconds(ch.get("timestamp", "00:00"))
                global_seconds = base_seconds + ch_seconds
                ch["timestamp"] = self.processor.seconds_to_timestamp(global_seconds)
                all_chapters.append(Chapter(**ch))

        self._emit_progress(on_progress, "done", 1.0, "摘要生成完成")

        return SummarizeResult(
            title=f"视频摘要（共{total}段）",
            summary="\n\n".join(summaries),
            chapters=all_chapters,
        )

    # ----------------------------------------------------------------
    # 辅助
    # ----------------------------------------------------------------

    def _parse_summarize_result(self, data: dict) -> SummarizeResult:
        """解析模型返回的 JSON 为 SummarizeResult"""
        title = data.get("title", "视频摘要")
        summary = data.get("summary", "")
        chapters_raw = data.get("chapters", [])
        chapters = []
        for ch in chapters_raw:
            if isinstance(ch, dict):
                chapters.append(Chapter(
                    timestamp=ch.get("timestamp", "00:00"),
                    title=ch.get("title", ""),
                    description=ch.get("description", ""),
                ))
        return SummarizeResult(title=title, summary=summary, chapters=chapters)

    def _segment_frame_indices(
        self, video_path: str, start_sec: float, end_sec: float, n: int,
    ) -> list[float]:
        """在段内均匀生成 n 个时间戳"""
        if n <= 1:
            return [(start_sec + end_sec) / 2]
        step = (end_sec - start_sec) / n
        return [start_sec + i * step + step / 2 for i in range(n)]

    @staticmethod
    def _parse_timestamp_to_seconds(ts: str) -> float:
        """解析 HH:MM:SS 或 MM:SS 为秒数"""
        parts = ts.replace(".", ":").split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return 0

    @staticmethod
    def _emit_progress(cb, stage, progress, message):
        if cb:
            cb(stage, progress, message)


# 导出
__all__ = ["VideoSummarizer", "SummarizeResult", "Chapter"]
