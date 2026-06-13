"""目标对象出现时间点标记"""

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
class Appearance:
    start_timestamp: str           # 首次出现时间 HH:MM:SS.mmm
    end_timestamp: str             # 最后出现时间
    frames_with_object: list[int]  # 出现帧索引列表
    description: str               # 目标描述


@dataclass
class TrackResult:
    appearances: list[Appearance] = field(default_factory=list)
    total_appearances: int = 0


# ----------------------------------------------------------------
# 目标追踪模块
# ----------------------------------------------------------------

class ObjectTracker:
    """目标对象出现时间标记器"""

    def __init__(self):
        self.client = ModelClient()
        self.processor = VideoProcessor()

    def track(
        self,
        video_path: str,
        target: str,
        batch_size: int = None,
        on_progress: Optional[callable] = None,
    ) -> TrackResult:
        """标记目标对象在视频中出现的时间段

        Args:
            video_path: 视频文件路径
            target: 目标描述（如 "红色的汽车"、"戴帽子的人"）
            batch_size: 每批帧数
            on_progress: 进度回调
        Returns:
            TrackResult 对象
        """
        batch_size = batch_size or config.TRACK_BATCH_SIZE

        self._emit_progress(on_progress, "sampling", 0.0, "正在采样视频帧...")

        meta = self.processor.get_metadata(video_path)
        fps = meta["fps"]

        # 每秒采样一帧
        total_seconds = int(meta["duration_seconds"])
        timestamps = [t for t in range(total_seconds)]
        all_frames = self.processor.sample_frames_by_timestamp(video_path, timestamps)

        if not all_frames:
            return TrackResult()

        # 分批判断目标是否出现
        batch_results = []  # list of (start_idx, end_idx, appears: bool, frame_indices, desc)
        total_batches = (len(all_frames) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            progress = 0.1 + 0.8 * ((batch_idx + 1) / total_batches)
            self._emit_progress(
                on_progress, "tracking",
                progress,
                f"正在追踪目标... ({batch_idx + 1}/{total_batches})",
            )

            start = batch_idx * batch_size
            end = min(start + batch_size, len(all_frames))
            batch_frames = all_frames[start:end]
            relative_indices = list(range(0, end - start))

            prompt = (
                f'以下是一段视频中的 {len(batch_frames)} 帧截图。请判断目标 "{target}"\n'
                f"是否出现在这些帧中。\n\n"
                f"输出 JSON：\n"
                f'{{\n'
                f'  "appears": true/false,\n'
                f'  "frame_indices": [0, 1, 3],\n'
                f'  "description": "目标出现的描述"\n'
                f'}}\n\n'
                f"如果目标没有出现，appears 设为 false，frame_indices 为空列表。"
            )

            response = self.client.chat_with_images(batch_frames, prompt)
            try:
                data = self.client._safe_parse_json(response)
            except Exception:
                data = {"appears": False, "frame_indices": [], "description": ""}

            appears = data.get("appears", False)
            rel_frames = data.get("frame_indices", [])
            desc = data.get("description", "")

            # 将相对索引转为全局索引
            global_indices = [start + idx for idx in rel_frames if (start + idx) < len(all_frames)]

            batch_results.append({
                "start_global": start,
                "end_global": end,
                "appears": appears,
                "frame_indices": global_indices,
                "description": desc,
            })

        # 聚合连续出现的时间段
        appearances = self._merge_appearances(batch_results, all_frames, fps)

        self._emit_progress(on_progress, "done", 1.0, "目标追踪完成")

        return TrackResult(appearances=appearances, total_appearances=len(appearances))

    # ----------------------------------------------------------------
    # 聚合
    # ----------------------------------------------------------------

    def _merge_appearances(
        self,
        batch_results: list[dict],
        all_frames: list,
        fps: float,
    ) -> list[Appearance]:
        """将批结果聚合为连续出现时间段"""
        if not batch_results:
            return []

        appearances = []
        current = None

        for br in batch_results:
            if br["appears"]:
                if current is None:
                    current = {
                        "start_idx": br["frame_indices"][0] if br["frame_indices"] else br["start_global"],
                        "end_idx": br["frame_indices"][-1] if br["frame_indices"] else br["end_global"] - 1,
                        "frame_indices": list(br["frame_indices"]),
                        "descriptions": [br["description"]] if br["description"] else [],
                    }
                else:
                    if br["frame_indices"]:
                        current["end_idx"] = br["frame_indices"][-1]
                        current["frame_indices"].extend(br["frame_indices"])
                    else:
                        current["end_idx"] = br["end_global"] - 1
                    if br["description"]:
                        current["descriptions"].append(br["description"])
            else:
                if current is not None:
                    # 检查是否只是短暂消失（跳过一批没出现不算结束，但最多跳过 2 批）
                    # 简化处理：立即结束当前段落
                    appearances.append(self._make_appearance(current, fps))
                    current = None

        # 收尾
        if current is not None:
            appearances.append(self._make_appearance(current, fps))

        return appearances

    def _make_appearance(self, current: dict, fps: float) -> Appearance:
        """构建 Appearance 对象"""
        start_ts = self.processor.frame_index_to_timestamp(current["start_idx"], fps)
        end_ts = self.processor.frame_index_to_timestamp(current["end_idx"], fps)
        # 去重 & 排序
        frame_indices = sorted(set(current["frame_indices"]))
        # 合并描述，取最长一段
        desc = max(current["descriptions"], key=len) if current["descriptions"] else "目标出现"

        return Appearance(
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            frames_with_object=frame_indices,
            description=desc,
        )

    @staticmethod
    def _emit_progress(cb, stage, progress, message):
        if cb:
            cb(stage, progress, message)
