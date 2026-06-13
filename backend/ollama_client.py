"""Ollama REST API 封装层"""

import base64
import io
import json
import time
from typing import Optional

import requests
from PIL import Image

from . import config


class OllamaError(Exception):
    """Ollama 调用相关异常"""
    pass


class OllamaConnectionError(OllamaError):
    """Ollama 服务连接失败"""
    pass


class OllamaClient:
    """封装 Ollama /api/chat 接口，支持图片输入"""

    def __init__(self, base_url: str = None, model: str = None, timeout: int = None):
        self.base_url = (base_url or config.OLLAMA_URL).rstrip("/")
        self.model = model or config.MODEL_NAME
        self.timeout = timeout or config.OLLAMA_TIMEOUT

    # ----------------------------------------------------------------
    # 公开方法
    # ----------------------------------------------------------------

    def check_connection(self) -> bool:
        """检测 Ollama 服务是否可用"""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def get_available_models(self) -> list:
        """获取 Ollama 上已拉取的模型列表"""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                raw_names = [m.get("name", "") for m in data.get("models", [])]
                # 标准化：去掉 :latest 后缀
                return [n.replace(":latest", "") for n in raw_names]
            return []
        except Exception:
            return []

    def check_model_available(self, model_name: str = None) -> bool:
        """检查指定模型是否在已拉取的模型列表中"""
        target = (model_name or self.model).replace(":latest", "")
        models = self.get_available_models()
        # 精确匹配或前缀匹配（用户可能只写主名）
        return any(m == target or m.startswith(target + ":") for m in models)

    def chat_with_images(
        self,
        images: list,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = None,
        max_slice_nums: int = None,
    ) -> str:
        """发送多张图片 + 文本提示到 Ollama，返回模型回复文本。

        Args:
            images: PIL.Image 对象列表
            prompt: 用户文本提示
            system: 可选的 system prompt
            temperature: 生成温度
            max_slice_nums: MiniCPM-V 切片数
        Returns:
            模型回复的文本
        """
        # 构造消息：Ollama 原生 /api/chat 接口使用 images 字段传递图片
        images_b64 = [self._pil_to_base64(img) for img in images]
        user_msg = {"role": "user", "content": prompt}
        if images_b64:
            user_msg["images"] = images_b64

        messages = [user_msg]
        if system:
            messages.insert(0, {"role": "system", "content": system})

        options = {
            "temperature": temperature if temperature is not None else config.TEMPERATURE,
        }
        if max_slice_nums is not None:
            options["max_slice_nums"] = max_slice_nums

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        text = self._request_with_retry(payload)
        return text

    def chat_text_only(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = None,
    ) -> str:
        """纯文本对话，不含图片"""
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature if temperature is not None else config.TEMPERATURE,
            },
        }

        text = self._request_with_retry(payload)
        return text

    # ----------------------------------------------------------------
    # 内部方法
    # ----------------------------------------------------------------

    def _pil_to_base64(self, img: Image.Image) -> str:
        """将 PIL.Image 转为 base64 字符串"""
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")

    def _request_with_retry(self, payload: dict) -> str:
        """带重试机制的 API 请求"""
        last_error = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("message", {}).get("content", "")
                else:
                    err_msg = f"Ollama 返回错误 (HTTP {resp.status_code}): {resp.text}"
                    last_error = OllamaError(err_msg)
            except requests.Timeout:
                last_error = OllamaError(f"请求超时 (尝试 {attempt}/{config.MAX_RETRIES})")
            except requests.ConnectionError:
                raise OllamaConnectionError(
                    "无法连接到 Ollama 服务，请确保 Ollama 已启动 (默认 http://localhost:11434)"
                )

            if attempt < config.MAX_RETRIES:
                time.sleep(config.RETRY_DELAY * attempt)

        raise last_error or OllamaError("请求失败，已达最大重试次数")

    def _safe_parse_json(self, text: str) -> dict:
        """安全解析模型输出中的 JSON"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # 用正则提取 ```json ... ``` 区块
        import re
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 提取第一个 { ... } 区块（非贪婪、跨行）
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        raise OllamaError(f"无法解析模型输出的 JSON:\n{text[:300]}")
