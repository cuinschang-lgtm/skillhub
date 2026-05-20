"""LLM 客户端抽象（V1 修订版）

设计原则:
- 统一 OpenAI-compatible 接口为主路径
- Anthropic Messages API 单独适配（接口形态不同 + max_tokens 是 API 强制字段）
- **绝不传 max_tokens / temperature 给 reasoning 模型**（V0 实测踩过的坑：DeepSeek-v4-flash
  等 reasoning 模型内部 reasoning_tokens 会占预算，max_tokens 太小时 content 字段返回空）
- LLMError 区分 retryable / terminal，对 429 + 5xx 指数退避；对 401/403 立刻 fail-fast
- 失败带 request id / response body / retry_after 给上层 harness 决策

支持 provider:
- deepseek (默认): https://api.deepseek.com  model=deepseek-v4-flash
- openai: https://api.openai.com/v1  model=gpt-4o-mini
- openai-compatible: 透传 base_url + key（支持任何 OpenAI 兼容服务）
- anthropic: https://api.anthropic.com  model=claude-sonnet-4-7（注：Messages API 强制 max_tokens，
  本 provider 设硬编码默认 8192——这是 API 机制要求，不是全局 max_tokens 策略的例外）

使用:
    client = LLMClient.from_env()  # 读 DEEPSEEK_KEY 等
    text = client.chat([{"role": "user", "content": "..."}])
"""
import os
import random
import time
from dataclasses import dataclass, field
from typing import Literal
import requests


ErrorKind = Literal["auth", "rate_limit", "server", "client", "network", "empty_content", "parse"]


class LLMError(Exception):
    """统一 LLM 错误类型，方便 harness 决策"""

    def __init__(
        self,
        message: str,
        *,
        kind: ErrorKind,
        retryable: bool = False,
        retry_after: float | None = None,
        provider: str = "",
        status: int | None = None,
        body: str = "",
        request_id: str = "",
    ):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.retry_after = retry_after
        self.provider = provider
        self.status = status
        self.body = body[:2000]  # 防止巨大错误体撑爆日志
        self.request_id = request_id

    def __str__(self) -> str:
        bits = [super().__str__(), f"kind={self.kind}"]
        if self.status is not None:
            bits.append(f"status={self.status}")
        if self.provider:
            bits.append(f"provider={self.provider}")
        if self.request_id:
            bits.append(f"request_id={self.request_id}")
        if self.retryable and self.retry_after is not None:
            bits.append(f"retry_after={self.retry_after}s")
        return " | ".join(bits)


def _classify_http_error(
    status: int, body: str, provider: str, retry_after_header: str | None
) -> LLMError:
    """把 HTTP 错误映射到 LLMError"""
    snippet = body[:500]
    if status == 401 or status == 403:
        return LLMError(
            f"{provider} 鉴权失败 ({status})。检查 API key 是否正确、是否过期。",
            kind="auth",
            retryable=False,
            provider=provider,
            status=status,
            body=snippet,
        )
    if status == 429:
        retry_after: float | None = None
        if retry_after_header:
            try:
                retry_after = float(retry_after_header)
            except ValueError:
                retry_after = None
        return LLMError(
            f"{provider} 限流 ({status})。请等待后重试。",
            kind="rate_limit",
            retryable=True,
            retry_after=retry_after,
            provider=provider,
            status=status,
            body=snippet,
        )
    if 500 <= status < 600:
        return LLMError(
            f"{provider} 服务端错误 ({status})。",
            kind="server",
            retryable=True,
            provider=provider,
            status=status,
            body=snippet,
        )
    return LLMError(
        f"{provider} 客户端错误 ({status})。{snippet}",
        kind="client",
        retryable=False,
        provider=provider,
        status=status,
        body=snippet,
    )


@dataclass
class LLMClient:
    """统一客户端。OpenAI-compatible 走 chat()，Anthropic 走 chat_anthropic()"""
    provider: str
    base_url: str
    api_key: str
    model: str
    flavor: Literal["openai-compat", "anthropic"] = "openai-compat"
    timeout: int = 600
    max_retries: int = 3
    # Anthropic 专用：Messages API 强制 max_tokens（API 机制，不可省）
    anthropic_max_tokens: int = 8192

    @classmethod
    def from_env(
        cls,
        provider: str = "deepseek",
        *,
        base_url_override: str | None = None,
        model_override: str | None = None,
        env_key_override: str | None = None,
    ) -> "LLMClient":
        """从环境变量构造。
        provider="custom" + base_url_override + env_key_override 可接任何 OpenAI 兼容服务
        """
        configs = {
            "deepseek": {
                "base_url": "https://api.deepseek.com",
                "model": "deepseek-v4-flash",
                "env_key": "DEEPSEEK_KEY",
                "flavor": "openai-compat",
            },
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4o-mini",
                "env_key": "OPENAI_API_KEY",
                "flavor": "openai-compat",
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com",
                "model": "claude-sonnet-4-7",
                "env_key": "ANTHROPIC_API_KEY",
                "flavor": "anthropic",
            },
            "custom": {
                "base_url": base_url_override or "",
                "model": model_override or "",
                "env_key": env_key_override or "LLM_API_KEY",
                "flavor": "openai-compat",
            },
        }
        if provider not in configs:
            raise ValueError(f"Unknown provider {provider}, supported: {list(configs)}")
        cfg = configs[provider]
        if provider == "custom":
            if not (base_url_override and env_key_override and model_override):
                raise ValueError(
                    "provider='custom' 必须传 base_url_override + model_override + env_key_override"
                )
        key = os.environ.get(cfg["env_key"], "")
        if not key:
            raise LLMError(
                f"{cfg['env_key']} 未设置。请获取 key 后:\n  export {cfg['env_key']}=your-key",
                kind="auth",
                retryable=False,
                provider=provider,
            )
        return cls(
            provider=provider,
            base_url=cfg["base_url"],
            api_key=key,
            model=cfg["model"],
            flavor=cfg["flavor"],
        )

    # ---------- 公共入口 ----------

    def chat(self, messages: list, *, system: str | None = None) -> str:
        """发请求，返回 content 字符串。带指数退避重试。

        ⚠️ OpenAI-compatible 路径**绝不传 max_tokens / temperature**（reasoning 模型陷阱）
        Anthropic 路径必须传 max_tokens（API 强制字段）
        """
        if self.flavor == "anthropic":
            return self._chat_anthropic(messages, system=system)
        return self._chat_openai_compat(messages, system=system)

    # ---------- OpenAI-compatible ----------

    def _chat_openai_compat(self, messages: list, *, system: str | None) -> str:
        if system:
            messages = [{"role": "system", "content": system}, *messages]
        body = {"model": self.model, "messages": messages}
        # 故意不传 max_tokens / temperature
        return self._do_request(
            url=f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            body=body,
            extract_content=lambda data: data["choices"][0]["message"]["content"],
        )

    # ---------- Anthropic Messages API ----------

    def _chat_anthropic(self, messages: list, *, system: str | None) -> str:
        # Anthropic 要求 system 是顶层字段，不在 messages 里
        body: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.anthropic_max_tokens,  # API 必填
        }
        if system:
            body["system"] = system

        def extract(data: dict) -> str:
            # Anthropic 响应：content 是 list of {type, text}
            blocks = data.get("content", [])
            text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            return "".join(text_parts)

        return self._do_request(
            url=f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            body=body,
            extract_content=extract,
        )

    # ---------- 共享请求 + 重试逻辑 ----------

    def _do_request(self, *, url: str, headers: dict, body: dict, extract_content) -> str:
        last_err: LLMError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                r = requests.post(url, headers=headers, json=body, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                last_err = LLMError(
                    f"{self.provider} 网络错误: {e}",
                    kind="network",
                    retryable=True,
                    provider=self.provider,
                )
                self._maybe_retry(attempt, last_err)
                continue

            if not r.ok:
                err = _classify_http_error(
                    r.status_code, r.text, self.provider, r.headers.get("Retry-After")
                )
                err.request_id = r.headers.get("x-request-id", "") or r.headers.get("request-id", "")
                if err.retryable and attempt < self.max_retries:
                    last_err = err
                    self._maybe_retry(attempt, err)
                    continue
                raise err

            try:
                data = r.json()
                content = extract_content(data)
            except (ValueError, KeyError, IndexError) as e:
                raise LLMError(
                    f"{self.provider} 响应解析失败: {e}",
                    kind="parse",
                    retryable=False,
                    provider=self.provider,
                    status=r.status_code,
                    body=r.text,
                    request_id=r.headers.get("x-request-id", ""),
                )

            if not content or not content.strip():
                raise LLMError(
                    "LLM 返回空 content。reasoning 模型陷阱：检查是否误传了 max_tokens；"
                    "或 prompt 触发了内容过滤。",
                    kind="empty_content",
                    retryable=False,
                    provider=self.provider,
                    status=r.status_code,
                    body=r.text[:500],
                    request_id=r.headers.get("x-request-id", ""),
                )
            return content

        # 重试用尽
        assert last_err is not None
        raise last_err

    def _maybe_retry(self, attempt: int, err: LLMError) -> None:
        """指数退避 + jitter，遵守 Retry-After"""
        if err.retry_after is not None:
            wait = err.retry_after
        else:
            wait = (2 ** attempt) + random.uniform(0, 1)
        wait = min(wait, 60.0)  # 不要等太久
        print(
            f"[llm] {err.kind} retry attempt={attempt + 1}/{self.max_retries} sleep={wait:.1f}s",
            flush=True,
        )
        time.sleep(wait)


def chat_concurrent(
    client: LLMClient,
    prompts: list,
    max_workers: int = 8,
) -> list:
    """并发调用 LLM，返回与输入等长的结果列表。
    单个失败不阻断其他，失败位置返回 LLMError 实例（**不是 None**——便于上游分类）
    """
    from concurrent.futures import ThreadPoolExecutor
    results: list = [None] * len(prompts)

    def worker(idx_msg):
        idx, msgs = idx_msg
        try:
            return idx, client.chat(msgs)
        except LLMError as e:
            print(f"[llm] prompt {idx} failed: {e}", flush=True)
            return idx, e
        except Exception as e:
            print(f"[llm] prompt {idx} unexpected: {e}", flush=True)
            return idx, LLMError(str(e), kind="client", provider=client.provider)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for idx, result in ex.map(worker, [(i, p) for i, p in enumerate(prompts)]):
            results[idx] = result
    return results
