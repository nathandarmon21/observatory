"""LLM provider — Ollama with persistent chat threads."""
from __future__ import annotations
import json
import asyncio
import re
from typing import Optional, List


class LLMProvider:
    def __init__(self, config: dict):
        self.config = config
        self.model = config.get("model", "llama3.2:3b")
        self.timeout = config.get("timeout", 90)
        self.temperature = config.get("temperature", 0.7)
        self.call_times: List[float] = []

    async def complete(self, prompt: str, system: str = "") -> str:
        raise NotImplementedError

    async def chat(self, messages: List[dict]) -> str:
        raise NotImplementedError

    async def check_available(self) -> bool:
        raise NotImplementedError

    async def complete_json(self, prompt: str, system: str = "", retries: int = 3) -> dict:
        last_raw = ""
        for attempt in range(retries):
            raw = await self.complete(prompt, system=system)
            if not raw:
                await asyncio.sleep(1)
                continue
            last_raw = raw
            parsed = _extract_json(raw)
            if parsed is not None:
                return parsed
            await asyncio.sleep(0.5)
        raise RuntimeError(
            f"LLM failed to return valid JSON after {retries} attempts.\n"
            f"Last response: {last_raw[:400]}"
        )

    async def chat_json(self, messages: List[dict], retries: int = 3) -> dict:
        """Send chat messages and parse JSON response."""
        last_raw = ""
        for attempt in range(retries):
            raw = await self.chat(messages)
            if not raw:
                await asyncio.sleep(1)
                continue
            last_raw = raw
            parsed = _extract_json(raw)
            if parsed is not None:
                return parsed
            await asyncio.sleep(0.5)
        raise RuntimeError(
            f"LLM chat failed to return valid JSON after {retries} attempts.\n"
            f"Last: {last_raw[:400]}"
        )

    @staticmethod
    def estimate_tokens(messages: List[dict]) -> int:
        """Rough token estimate: 1 token ≈ 4 chars."""
        total = sum(len(m.get("content", "")) for m in messages)
        return total // 4

    def log_call_time(self, seconds: float):
        self.call_times.append(seconds)
        if len(self.call_times) > 100:
            self.call_times = self.call_times[-100:]

    @property
    def avg_call_time(self) -> float:
        if not self.call_times:
            return 0.0
        return sum(self.call_times) / len(self.call_times)


def _extract_json(raw: str) -> Optional[dict]:
    raw = raw.strip()
    if "```" in raw:
        parts = raw.split("```")
        for p in parts:
            p = p.strip().lstrip("json").strip()
            if p.startswith("{"):
                raw = p
                break
    start = raw.find("{")
    if start < 0:
        return None
    end = raw.rfind("}") + 1
    candidate = raw[start:end] if end > start else raw[start:]
    # Fix $400 → 400 in numeric positions
    candidate = re.sub(r':\s*\$(\d+(?:\.\d+)?)', r': \1', candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    candidate = _close_truncated_json(candidate)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    return None


def _close_truncated_json(s: str) -> str:
    s = s.rstrip().rstrip(",")
    in_string = False
    escape = False
    for ch in s:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
    if in_string:
        s += '"'
    s += "]" * max(0, s.count("[") - s.count("]"))
    s += "}" * max(0, s.count("{") - s.count("}"))
    return s


class AnthropicProvider(LLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        import os
        self.api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
        self.max_tokens = config.get("max_tokens", 2048)

    async def complete(self, prompt: str, system: str = "") -> str:
        import time
        t0 = time.time()
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            response = await client.messages.create(**kwargs)
            self.log_call_time(time.time() - t0)
            return response.content[0].text if response.content else ""
        except Exception:
            return ""

    async def chat(self, messages: List[dict]) -> str:
        import time
        t0 = time.time()
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=self.api_key)
            # Extract system message if present
            system = ""
            chat_messages = []
            for m in messages:
                if m.get("role") == "system":
                    system = m.get("content", "")
                else:
                    chat_messages.append({"role": m["role"], "content": m.get("content", "")})
            if not chat_messages:
                return ""
            kwargs = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "messages": chat_messages,
            }
            if system:
                kwargs["system"] = system
            response = await client.messages.create(**kwargs)
            self.log_call_time(time.time() - t0)
            return response.content[0].text if response.content else ""
        except Exception:
            return ""

    async def check_available(self) -> bool:
        return bool(self.api_key)


class OllamaProvider(LLMProvider):
    def __init__(self, config: dict):
        super().__init__(config)
        self.base_url = config.get("base_url", "http://localhost:11434")
        self._using_gpu: Optional[bool] = None

    async def complete(self, prompt: str, system: str = "") -> str:
        import time
        t0 = time.time()
        try:
            import httpx
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature, "top_p": 0.9, "num_predict": 1200, "num_ctx": 8192},
            }
            if system:
                payload["system"] = system
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    self.log_call_time(time.time() - t0)
                    return result.get("response", "")
                return ""
        except Exception:
            return ""

    async def chat(self, messages: List[dict]) -> str:
        import time
        t0 = time.time()
        try:
            import httpx
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": self.temperature, "top_p": 0.9, "num_predict": 1200, "num_ctx": 32768},
            }
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    self.log_call_time(time.time() - t0)
                    return result.get("message", {}).get("content", "")
                return ""
        except Exception:
            return ""

    async def check_available(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code != 200:
                    return False
                models = [m["name"] for m in resp.json().get("models", [])]
                model_base = self.model.split(":")[0]
                return any(model_base in m for m in models)
        except Exception:
            return False

    async def check_gpu(self) -> bool:
        """Check if Ollama is using GPU acceleration."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/ps")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    for m in models:
                        details = m.get("details", {}) or {}
                        # If size_vram > 0, GPU is being used
                        if m.get("size_vram", 0) > 0:
                            self._using_gpu = True
                            return True
                self._using_gpu = False
                return False
        except Exception:
            self._using_gpu = False
            return False

    async def compress_history(self, messages: List[dict], keep_recent: int = 20) -> List[dict]:
        """Compress old message history when context window is filling up."""
        if len(messages) <= keep_recent + 2:  # system + keep_recent + some buffer
            return messages

        system_msg = messages[0]  # always keep system prompt
        recent = messages[-(keep_recent * 2):]  # keep last N exchanges (user+assistant pairs)
        to_compress = messages[1:-(keep_recent * 2)]

        if not to_compress:
            return messages

        # Build summary text
        text_parts = []
        for m in to_compress:
            role = m.get("role", "")
            content = str(m.get("content", ""))[:600]
            text_parts.append(f"[{role}]: {content}")
        text = "\n\n".join(text_parts[:30])  # cap at 30 messages for summary

        summary_prompt = (
            "Summarize the following agent decision history in 200-300 words. "
            "Capture: key strategic decisions made, relationships formed or broken, "
            "notable events observed, lessons learned, current strategy direction. "
            "Write in first person as the agent.\n\n" + text
        )

        summary = await self.complete(
            summary_prompt,
            system="You are summarizing an AI agent's strategic decision log. Be concise and capture the most important strategic information."
        )

        if not summary:
            # If compression fails, just truncate
            return [system_msg] + recent

        compressed = [
            system_msg,
            {"role": "user", "content": f"[COMPRESSED MEMORY — Days before this summary]\n{summary}"},
            {"role": "assistant", "content": "Understood. I have reviewed my compressed history and will continue with this context."},
        ] + recent

        return compressed


def create_provider(config: dict) -> LLMProvider:
    provider_type = config.get("provider", "ollama")
    if provider_type == "anthropic":
        return AnthropicProvider(config)
    return OllamaProvider(config)


async def require_llm(provider: LLMProvider):
    try:
        available = await asyncio.wait_for(provider.check_available(), timeout=8.0)
    except asyncio.TimeoutError:
        available = False

    if not available:
        model = getattr(provider, "model", "unknown")
        if isinstance(provider, AnthropicProvider):
            raise RuntimeError(
                f"\n\n  ✗  Anthropic API key is missing or invalid.\n\n"
                f"  Set the ANTHROPIC_API_KEY environment variable and restart.\n\n"
                f"  The Sanctuary requires a valid API key for all agent decisions.\n"
                f"  There is no rule-based fallback.\n"
            )
        base_url = getattr(provider, "base_url", "unknown")
        print(
            f"\n  ⚠  Ollama not reachable at {base_url} or model '{model}' not pulled yet.\n"
            f"  Starting simulation anyway — agent turns will retry individually.\n"
            f"  Make sure Ollama is running and '{model}' is pulled on the server.\n"
        )
