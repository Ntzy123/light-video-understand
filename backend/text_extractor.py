"""画面文字提取与结构化解析"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Optional

from .model_client import ModelClient
from .video_processor import VideoProcessor
from . import config


# ----------------------------------------------------------------
# 数据类
# ----------------------------------------------------------------

@dataclass
class TextSection:
    timestamp: str       # 出现时间 HH:MM:SS.mmm
    text: str            # 文字内容
    category: str        # 分类: "title" / "subtitle" / "scene_text" / "watermark"
    frame_index: int     # 来源帧索引


@dataclass
class TextExtractResult:
    sections: list[TextSection] = field(default_factory=list)
    full_text: str = ""


# ----------------------------------------------------------------
# 文字提取模块
# ----------------------------------------------------------------

class TextExtractor:
    """画面文字提取器"""

    def __init__(self):
        self.client = ModelClient()
        self.processor = VideoProcessor()

    def extract_all(
        self,
        video_path: str,
        batch_size: int = None,
        on_progress: Optional[callable] = None,
    ) -> TextExtractResult:
        """提取视频中所有可见文字

        Args:
            video_path: 视频文件路径
            batch_size: 每批帧数
            on_progress: 进度回调
        Returns:
            TextExtractResult 对象
        """
        batch_size = batch_size or min(
            config.TEXT_BATCH_SIZE,
            max(1, VideoProcessor.calculate_max_frames(config.TEXT_BATCH_SIZE)),
        )

        self._emit_progress(on_progress, "extracting_metadata", 0.0, "正在读取视频信息...")
        meta = self.processor.get_metadata(video_path)
        fps = meta["fps"]

        # 以约 1 fps 采样，但控制总帧数不过大
        total_seconds = int(meta["duration_seconds"])
        max_total_frames = min(total_seconds, 120)  # 最多 120 帧
        frames = self.processor.sample_frames_uniform_by_count(video_path, max_total_frames)

        if not frames:
            return TextExtractResult()

        # 分批处理
        all_sections = []
        total_batches = (len(frames) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            progress = 0.1 + 0.8 * ((batch_idx + 1) / total_batches)
            self._emit_progress(
                on_progress, "extracting",
                progress,
                f"正在提取文字... ({batch_idx + 1}/{total_batches})",
            )

            start = batch_idx * batch_size
            end = min(start + batch_size, len(frames))
            batch_frames = frames[start:end]
            batch_indices = list(range(start, end))

            prompt = (
                f"分析以下视频帧中的文字内容。请提取所有可见文字（包括标题、字幕、画面文字、水印等）。\n"
                f"以 JSON 格式输出：\n\n"
                f'{{\n'
                f'  "frames": [\n'
                f'    {{\n'
                f'      "frame_index": 0,\n'
                f'      "texts": [\n'
                f'        {{"text": "...", "category": "scene_text"}},\n'
                f'        {{"text": "...", "category": "subtitle"}}\n'
                f'      ]\n'
                f'    }}\n'
                f'  ]\n'
                f'}}\n\n'
                f'categories: "title"(标题), "subtitle"(字幕), "scene_text"(场景文字), "watermark"(水印)\n'
                f'如果没有文字，返回 {{"frames": []}}'
            )

            response = self.client.chat_with_images(batch_frames, prompt)
            try:
                data = self.client._safe_parse_json(response)
            except Exception:
                continue

            frames_data = data.get("frames", [])
            for fd in frames_data:
                rel_idx = fd.get("frame_index", 0)
                global_idx = batch_indices[rel_idx] if rel_idx < len(batch_indices) else batch_indices[-1]
                timestamp = self.processor.frame_index_to_timestamp(global_idx, fps)

                for text_item in fd.get("texts", []):
                    section = TextSection(
                        timestamp=timestamp,
                        text=text_item.get("text", ""),
                        category=text_item.get("category", "scene_text"),
                        frame_index=global_idx,
                    )
                    all_sections.append(section)

        # 全局去重（基于文本相似度简单去重：相同文本只保留第一个）
        seen_texts = set()
        unique_sections = []
        for s in all_sections:
            key = s.text.strip().lower()
            if key and key not in seen_texts:
                seen_texts.add(key)
                unique_sections.append(s)

        self._emit_progress(on_progress, "done", 1.0, "文字提取完成")

        full_text = "\n".join(
            f"[{s.timestamp}] ({s.category}) {s.text}" for s in unique_sections
        )

        return TextExtractResult(sections=unique_sections, full_text=full_text)

    @staticmethod
    def _emit_progress(cb, stage, progress, message):
        if cb:
            cb(stage, progress, message)
