"""统一模型客户端：支持 Ollama 本地 / MiniCPM 官方 API / 自定义 OpenAI 兼容 API"""

import base64
import io
import json
import re
import time
from typing import Optional

import requests
from PIL import Image

from . import config


class ModelError(Exception):
    """模型调用相关异常"""
    pass


class ModelConnectionError(ModelError):
    """服务连接失败"""
    pass


class ModelClient:
    """统一模型客户端，根据 config.API_BACKEND 自动选择合适的后端

    后端模式:
        - "ollama":    本地 Ollama 服务
        - "minicpm_api": MiniCPM 官方 API (api.modelbest.cn)
        - "custom_api":  自定义 OpenAI 兼容 API
    """

    def __init__(self, backend: str = None):
        self.backend = backend or config.API_BACKEND
        self.timeout = config.OLLAMA_TIMEOUT

    # ----------------------------------------------------------------
    # 公开方法
    # ----------------------------------------------------------------

    def check_connection(self) -> bool:
        """检测当前后端服务是否可用"""
        if self.backend == "ollama":
            return self._check_ollama()
        else:
            return self._check_api()

    def check_model_available(self, model_name: str = None) -> bool:
        """检查指定模型是否可用"""
        if self.backend == "ollama":
            return self._check_ollama_model(model_name)
        else:
            # API 模式：只要连接成功就算可用
            return self.check_connection()

    def get_available_models(self) -> list:
        """获取可用模型列表"""
        if self.backend == "ollama":
            return self._get_ollama_models()
        elif self.backend == "minicpm_api":
            return ["MiniCPM-V-4.6-Instruct", "MiniCPM-V-4.6-Thinking", "MiniCPM-o-4.5"]
        else:
            return []

    def chat_with_images(
        self,
        images: list,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = None,
        max_slice_nums: int = None,
    ) -> str:
        """发送多张图片 + 文本提示，返回回复文本"""
        if self.backend == "ollama":
            return self._ollama_chat_with_images(images, prompt, system, temperature, max_slice_nums)
        else:
            return self._api_chat_with_images(images, prompt, system, temperature)

    def chat_text_only(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = None,
    ) -> str:
        """纯文本对话"""
        if self.backend == "ollama":
            return self._ollama_chat_text_only(prompt, system, temperature)
        else:
            return self._api_chat_text_only(prompt, system, temperature)

    def _safe_parse_json(self, text: str) -> dict:
        """安全解析模型输出中的 JSON（含自动修复）"""

        def _try_parse(raw: str) -> dict | None:
            """尝试解析一段文本的 JSON，失败返回 None"""
            raw = raw.strip()
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                pass
            # 尝试修复常见 JSON 格式问题后再解析
            try:
                return json.loads(self._repair_json(raw))
            except json.JSONDecodeError:
                return None

        text = text.strip()
        if not text:
            raise ModelError("模型返回空内容，无法解析")

        # 1) 全文本直接尝试
        if text.startswith("{"):
            result = _try_parse(text)
            if result is not None:
                return result

        # 2) 从 ```json ``` 代码块中提取
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            result = _try_parse(match.group(1))
            if result is not None:
                return result

        # 3) 贪婪提取最外层 { ... }
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            result = _try_parse(match.group(1))
            if result is not None:
                return result

        raise ModelError(f"无法解析模型输出的 JSON:\n{text[:300]}")

    @staticmethod
    def _repair_json(text: str) -> str:
        """尝试修复常见的 JSON 格式错误（缺失逗号、尾随逗号等）"""
        # 对象/数组间缺失逗号: }{ → },{   ][ → ],[   }[ → },[   ]{ → ],{
        text = re.sub(r"(\})\s*(\{|\[)", r"\1,\2", text)
        text = re.sub(r"(\])\s*(\{|\[)", r"\1,\2", text)
        # 尾随逗号: ,} → }   ,] → ]
        text = re.sub(r",\s*([}\]])", r"\1", text)
        return text

    # ----------------------------------------------------------------
    # Ollama 后端
    # ----------------------------------------------------------------

    def _check_ollama(self) -> bool:
        try:
            resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
            return resp.status_code == 200
        except requests.ConnectionError:
            return False

    def _check_ollama_model(self, model_name: str = None) -> bool:
        target = (model_name or config.MODEL_NAME).replace(":latest", "")
        models = self._get_ollama_models()
        return any(m == target or m.startswith(target + ":") for m in models)

    def _get_ollama_models(self) -> list:
        try:
            resp = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m.get("name", "").replace(":latest", "") for m in resp.json().get("models", [])]
            return []
        except Exception:
            return []

    def _ollama_chat_with_images(
        self, images, prompt, system=None, temperature=None, max_slice_nums=None
    ) -> str:
        images_b64 = [self._pil_to_base64(img) for img in images]
        user_msg = {"role": "user", "content": prompt}
        if images_b64:
            user_msg["images"] = images_b64
        messages = [user_msg]
        if system:
            messages.insert(0, {"role": "system", "content": system})

        options = {"temperature": temperature if temperature is not None else config.TEMPERATURE}
        if max_slice_nums is not None:
            options["max_slice_nums"] = max_slice_nums

        payload = {
            "model": config.MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": options,
        }
        return self._ollama_request(payload)

    def _ollama_chat_text_only(self, prompt, system=None, temperature=None) -> str:
        messages = [{"role": "user", "content": prompt}]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        payload = {
            "model": config.MODEL_NAME,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature if temperature is not None else config.TEMPERATURE},
        }
        return self._ollama_request(payload)

    def _ollama_request(self, payload: dict) -> str:
        last_error = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    f"{config.OLLAMA_URL}/api/chat",
                    json=payload,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    return resp.json().get("message", {}).get("content", "")
                else:
                    last_error = ModelError(f"Ollama 返回错误 (HTTP {resp.status_code}): {resp.text}")
            except requests.Timeout:
                last_error = ModelError(f"请求超时 (尝试 {attempt}/{config.MAX_RETRIES})")
            except requests.ConnectionError:
                raise ModelConnectionError(
                    "无法连接到 Ollama 服务，请确保 Ollama 已启动 (默认 http://localhost:11434)"
                )
            if attempt < config.MAX_RETRIES:
                time.sleep(config.RETRY_DELAY * attempt)
        raise last_error or ModelError("请求失败，已达最大重试次数")

    # ----------------------------------------------------------------
    # API 后端 (OpenAI Chat Completions 兼容)
    # ----------------------------------------------------------------

    def _check_api(self) -> bool:
        """通过一次轻量文本请求检测 API 是否可用（单次8秒超时，不重试）"""
        try:
            model_name = config.API_MODEL_NAME
            api_url = config.API_BASE_URL.rstrip("/") + "/chat/completions"
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "ping"}],
                "temperature": 0.1,
                "max_tokens": 1,
            }
            headers = {
                "Authorization": f"Bearer {config.API_KEY}",
                "Content-Type": "application/json",
            }
            resp = requests.post(api_url, json=payload, headers=headers, timeout=8)
            return resp.status_code == 200
        except Exception:
            return False

    def _api_chat_with_images(
        self, images, prompt, system=None, temperature=None
    ) -> str:
        content = [{"type": "text", "text": prompt}]
        for img in images:
            b64 = self._pil_to_base64(img)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        return self._api_request(messages, temperature)

    def _api_chat_text_only(self, prompt, system=None, temperature=None, _check_timeout=None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self._api_request(messages, temperature, _check_timeout=_check_timeout)

    def _api_request(self, messages: list, temperature: float = None, _check_timeout: int = None) -> str:
        model_name = config.API_MODEL_NAME
        api_url = config.API_BASE_URL.rstrip("/") + "/chat/completions"

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else config.TEMPERATURE,
            "max_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {config.API_KEY}",
            "Content-Type": "application/json",
        }

        # 连接检测使用短超时，正常请求使用配置超时
        req_timeout = _check_timeout if _check_timeout is not None else self.timeout

        last_error = None
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                resp = requests.post(
                    api_url,
                    json=payload,
                    headers=headers,
                    timeout=req_timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    err_detail = resp.text[:300]
                    last_error = ModelError(f"API 返回错误 (HTTP {resp.status_code}): {err_detail}")
            except requests.Timeout:
                last_error = ModelError(f"API 请求超时 (尝试 {attempt}/{config.MAX_RETRIES})")
            except requests.ConnectionError:
                raise ModelConnectionError(
                    f"无法连接到 API 服务 ({config.API_BASE_URL})"
                )
            except Exception as e:
                last_error = ModelError(f"API 请求异常: {e}")

            if attempt < config.MAX_RETRIES:
                time.sleep(config.RETRY_DELAY * attempt)

        raise last_error or ModelError("API 请求失败，已达最大重试次数")

    # ----------------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------------

    @staticmethod
    def _pil_to_base64(img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")


# 向后兼容导出
OllamaError = ModelError
OllamaConnectionError = ModelConnectionError
__all__ = ["ModelClient", "ModelError", "ModelConnectionError"]
