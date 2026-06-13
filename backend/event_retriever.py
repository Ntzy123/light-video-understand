"""长时监控视频关键事件检索"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from .model_client import ModelClient
from .video_processor import VideoProcessor
from . import config


# ----------------------------------------------------------------
# 数据类
# ----------------------------------------------------------------

@dataclass
class Event:
    timestamp: str             # 事件发生时间 HH:MM:SS.mmm
    description: str           # 事件描述
    duration_seconds: float    # 持续时长（估计值）
    confidence: float          # 置信度 0-1
    event_type: str            # 事件类型
    key_frame_index: int       # 代表帧索引
    key_frame_base64: str = "" # 代表帧 base64（由外部填充）


@dataclass
class EventResult:
    events: list[Event] = field(default_factory=list)
    total_events: int = 0


# ----------------------------------------------------------------
# 事件检索模块
# ----------------------------------------------------------------

class EventRetriever:
    """关键事件检索器"""

    def __init__(self):
        self.client = ModelClient()
        self.processor = VideoProcessor()

    def retrieve(
        self,
        video_path: str,
        query: str,
        sensitivity: float = 0.5,
        event_type: Optional[str] = None,
        on_progress: Optional[callable] = None,
    ) -> EventResult:
        """检索视频中与查询匹配的关键事件

        Args:
            video_path: 视频文件路径
            query: 查询关键词/描述
            sensitivity: 灵敏度 (0.0-1.0)，越高越容易检出事件
            event_type: 可选的事件类型过滤
            on_progress: 进度回调
        Returns:
            EventResult 对象
        """
        self._emit_progress(on_progress, "preparing", 0.0, "正在准备视频分段...")

        meta = self.processor.get_metadata(video_path)
        fps = meta["fps"]
        segments = self.processor.video_to_segments(video_path, config.EVENT_SEGMENT_MINUTES)

        all_events = []
        total = len(segments)

        for i, seg in enumerate(segments):
            progress = (i + 1) / total
            self._emit_progress(
                on_progress, "searching",
                progress,
                f"正在检索第 {i+1}/{total} 段...",
            )

            # 采样帧
            seg_duration = seg["end_seconds"] - seg["start_seconds"]
            n_frames = min(config.EVENT_FRAMES_PER_SEGMENT, max(4, int(seg_duration)))
            timestamps = [
                seg["start_seconds"] + (seg_duration / (n_frames + 1)) * (j + 1)
                for j in range(n_frames)
            ]
            frames = self.processor.sample_frames_by_timestamp(video_path, timestamps)

            if not frames:
                continue

            # 构造 prompt
            sensitivity_desc = self._sensitivity_to_text(sensitivity)
            prompt = (
                f"你正在监控视频中检索特定事件。\n"
                f"查询关键词：{query}\n"
                f"检索灵敏度：{sensitivity_desc}\n"
                f"{'(事件类型：' + event_type + ')' if event_type else ''}\n\n"
                f"以下是一段 {seg_duration:.0f} 秒视频的 {len(frames)} 个关键帧。\n"
                f"请判断这些帧中是否出现了与 \"{query}\" 相关的事件。\n\n"
                f"输出 JSON：\n"
                f'{{\n'
                f'  "has_event": true/false,\n'
                f'  "events": [\n'
                f'    {{\n'
                f'      "description": "事件描述",\n'
                f'      "timestamp_in_segment": 12.5,\n'
                f'      "confidence": 0.85,\n'
                f'      "event_type": "{query}",\n'
                f'      "key_frame_index": 3\n'
                f'    }}\n'
                f'  ]\n'
                f'}}\n\n'
                f'如果没有相关事件，has_event 设为 false，events 为空列表。'
            )

            response = self.client.chat_with_images(frames, prompt)
            try:
                data = self.client._safe_parse_json(response)
            except Exception:
                continue

            if not data.get("has_event"):
                continue

            for evt in data.get("events", []):
                ts_in_seg = evt.get("timestamp_in_segment", 0)
                global_seconds = seg["start_seconds"] + ts_in_seg
                frame_idx = evt.get("key_frame_index", 0)
                # 映射到全局帧索引
                if frame_idx < len(timestamps):
                    global_ts = timestamps[frame_idx]
                    global_frame_idx = int(global_ts * fps)
                else:
                    global_frame_idx = int(global_seconds * fps)

                event = Event(
                    timestamp=self.processor.seconds_to_timestamp(global_seconds),
                    description=evt.get("description", ""),
                    duration_seconds=seg_duration / len(frames) * 2,  # 粗略估计
                    confidence=min(1.0, max(0.0, evt.get("confidence", 0.5))),
                    event_type=evt.get("event_type", query),
                    key_frame_index=global_frame_idx,
                )
                all_events.append(event)

        # 合并邻近事件（时间间隔 < 3 秒的合并为一个）
        merged = self._merge_events(all_events)

        self._emit_progress(on_progress, "done", 1.0, "事件检索完成")

        return EventResult(events=merged, total_events=len(merged))

    # ----------------------------------------------------------------
    # 辅助
    # ----------------------------------------------------------------

    @staticmethod
    def _sensitivity_to_text(s: float) -> str:
        if s >= 0.8:
            return "非常高（尽量检出所有可能事件）"
        elif s >= 0.6:
            return "高"
        elif s >= 0.4:
            return "中等"
        elif s >= 0.2:
            return "低"
        return "非常低（只检明确匹配的事件）"

    @staticmethod
    def _merge_events(events: list[Event]) -> list[Event]:
        """合并时间上邻近的事件"""
        if not events:
            return []

        # 按时间排序
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        merged = [sorted_events[0]]

        for evt in sorted_events[1:]:
            last = merged[-1]
            # 解析时间差（秒）
            last_sec = _ts_to_seconds(last.timestamp)
            cur_sec = _ts_to_seconds(evt.timestamp)
            if cur_sec - last_sec < 3.0:
                # 合并：保留置信度更高的
                if evt.confidence > last.confidence:
                    last.description = evt.description
                    last.confidence = evt.confidence
                    last.key_frame_index = evt.key_frame_index
                last.duration_seconds = cur_sec - last_sec + last.duration_seconds
            else:
                merged.append(evt)

        return merged

    @staticmethod
    def _emit_progress(cb, stage, progress, message):
        if cb:
            cb(stage, progress, message)


def _ts_to_seconds(ts: str) -> float:
    """HH:MM:SS.mmm → 秒"""
    parts = ts.replace(".", ":").split(":")
    if len(parts) == 4:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) + float(parts[3]) / 1000
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    return 0
