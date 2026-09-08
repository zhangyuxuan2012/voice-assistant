# -*- coding: utf-8 -*-
"""AI 模型调用：兼容 OpenAI Chat Completions 接口的本地 / 云端模型。

支持：
  - 本地模型：Ollama、LM Studio（本机运行，无需 API Key）
  - 云端模型：OpenAI、硅基流动、DeepSeek 或任意 OpenAI 兼容接口（只需 API Key）
"""
from openai import OpenAI

from config import MODEL_PRESETS


class LLMError(Exception):
    """模型调用相关的业务错误，带用户可读的中文信息。"""


class LLMClient:
    def __init__(self, model_type="ollama", api_key="", base_url="", model_name=""):
        self.model_type = model_type or "custom"

        # 未填写时按类型自动补全默认接口地址与模型名
        preset = MODEL_PRESETS.get(self.model_type, {})
        self.base_url = (base_url or "").strip() or preset.get("base_url", "")
        self.model_name = (model_name or "").strip() or preset.get("model_name", "")

        if not self.base_url:
            raise LLMError("未填写接口地址（Base URL），请打开“设置”检查。")
        if not self.model_name:
            raise LLMError("未填写模型名称，请打开“设置”检查。")

        try:
            self.client = OpenAI(
                api_key=(api_key or "").strip() or "not-needed",
                base_url=self.base_url,
                timeout=60,
            )
        except Exception as e:
            raise LLMError(f"初始化 AI 客户端失败：{e}")

    def chat(self, messages, temperature=0.7):
        """发送多轮对话，返回助手回复文本。"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=float(temperature),
                stream=False,
            )
            content = resp.choices[0].message.content
            if not content or not content.strip():
                raise LLMError("模型返回了空内容（可能被内容策略拦截）。")
            return content.strip()
        except LLMError:
            raise
        except Exception as e:
            raise LLMError(f"模型调用失败：{e}")

    def test(self, timeout=30):
        """发一条最短请求验证连接是否可用。返回 (ok, 说明)。"""
        try:
            resp = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "你好"}],
                temperature=0.1,
                timeout=timeout,
            )
            content = (resp.choices[0].message.content or "").strip()
            return True, f"连接成功，模型已响应：{content[:40]}"
        except Exception as e:
            return False, str(e)
