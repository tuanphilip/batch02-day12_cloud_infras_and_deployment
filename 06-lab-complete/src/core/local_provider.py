import time
import os
from typing import Dict, Any, Optional, Generator
from llama_cpp import Llama
from src.core.llm_provider import LLMProvider


# ---------------------------------------------------------------------------
# Chat template per model family
# ---------------------------------------------------------------------------
def _detect_chat_format(model_name: str) -> str:
    """
    Tự động nhận diện chat template dựa trên tên file model.

    Returns:
        "chatml"  - Qwen2.5, Qwen2, SmolLM2, ...
        "phi3"    - Phi-3-mini, Phi-3.5-mini
        "gemma"   - Gemma-2
        "llama3"  - Llama-3.x
        "chatml"  - fallback mặc định
    """
    name = model_name.lower()
    if "phi-3" in name or "phi3" in name:
        return "phi3"
    if "gemma-2" in name or "gemma2" in name:
        return "gemma"
    if "llama-3" in name or "llama3" in name:
        return "llama3"
    # Qwen2.5, Qwen2, SmolLM2, Mistral-7B-Instruct-v0.3+, etc.
    return "chatml"


def _build_prompt(prompt: str, system_prompt: Optional[str], fmt: str) -> tuple[str, list[str]]:
    """
    Trả về (full_prompt_string, stop_tokens) theo đúng chat template.
    """
    sp = system_prompt or ""

    if fmt == "phi3":
        # Phi-3-mini / Phi-3.5-mini
        if sp:
            full = f"<|system|>\n{sp}<|end|>\n<|user|>\n{prompt}<|end|>\n<|assistant|>"
        else:
            full = f"<|user|>\n{prompt}<|end|>\n<|assistant|>"
        stops = ["<|end|>", "Observation:"]

    elif fmt == "gemma":
        # Gemma-2-it  (<start_of_turn> / <end_of_turn>)
        if sp:
            full = (
                f"<start_of_turn>user\n{sp}\n\n{prompt}<end_of_turn>\n"
                f"<start_of_turn>model\n"
            )
        else:
            full = f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
        stops = ["<end_of_turn>", "Observation:"]

    elif fmt == "llama3":
        # Llama-3.x  (<|begin_of_text|> ... <|eot_id|>)
        if sp:
            full = (
                "<|begin_of_text|>"
                f"<|start_header_id|>system<|end_header_id|>\n\n{sp}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n\n"
            )
        else:
            full = (
                "<|begin_of_text|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|>"
                "<|start_header_id|>assistant<|end_header_id|>\n\n"
            )
        stops = ["<|eot_id|>", "Observation:"]

    else:
        # ChatML  (Qwen2.5, SmolLM2, Mistral v0.3+, ...)
        if sp:
            full = (
                f"<|im_start|>system\n{sp}<|im_end|>\n"
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )
        else:
            full = (
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )
        stops = ["<|im_end|>", "Observation:"]

    return full, stops


class LocalProvider(LLMProvider):
    """
    LLM Provider cho các model local dạng GGUF qua llama-cpp-python.

    Hỗ trợ tự động nhận diện chat template:
      - ChatML  : Qwen2.5-*, SmolLM2-*, ...  (mặc định)
      - Phi-3   : Phi-3-mini-*, Phi-3.5-mini-*
      - Gemma   : gemma-2-*
      - Llama-3 : Llama-3.*
    """

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
        n_threads: Optional[int] = None,
    ):
        """
        Khởi tạo local Llama model.

        Args:
            model_path : Đường dẫn tới file .gguf.
            n_ctx      : Kích thước context window (tokens).
            n_threads  : Số CPU threads. None → dùng toàn bộ core.
        """
        super().__init__(model_name=os.path.basename(model_path))

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Model file not found at: {model_path}\n"
                "Please download the .gguf file and place it in the models/ folder."
            )

        self._chat_fmt = _detect_chat_format(self.model_name)
        print(f"[LocalProvider] Loading '{self.model_name}' (chat_format={self._chat_fmt}) ...")

        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            verbose=False,
        )

        print(f"[LocalProvider] Model ready.")

    # ------------------------------------------------------------------

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """Non-streaming completion."""
        start_time = time.time()

        full_prompt, stop_tokens = _build_prompt(prompt, system_prompt, self._chat_fmt)

        response = self.llm(
            full_prompt,
            max_tokens=1024,
            stop=stop_tokens,
            echo=False,
        )

        latency_ms = int((time.time() - start_time) * 1000)
        content = response["choices"][0]["text"].strip()
        usage = {
            "prompt_tokens": response["usage"]["prompt_tokens"],
            "completion_tokens": response["usage"]["completion_tokens"],
            "total_tokens": response["usage"]["total_tokens"],
        }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "local",
            "model": self.model_name,
            "chat_format": self._chat_fmt,
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """Streaming completion."""
        full_prompt, stop_tokens = _build_prompt(prompt, system_prompt, self._chat_fmt)

        stream = self.llm(
            full_prompt,
            max_tokens=1024,
            stop=stop_tokens,
            stream=True,
        )

        for chunk in stream:
            token = chunk["choices"][0]["text"]
            if token:
                yield token
