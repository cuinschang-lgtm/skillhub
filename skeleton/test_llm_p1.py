"""针对 P1 reasoning 模型陷阱的最小回归测试。

覆盖两条关键行为：
1. OpenAI-compatible 路径不传 max_tokens / temperature
2. 返回空 content 时抛出明确的 LLMError

运行方式:
    python skeleton/test_llm_p1.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

# 把 skeleton/ 加到搜索路径，方便直接 python 运行
sys.path.insert(0, str(Path(__file__).parent))

from llm import LLMClient, LLMError  # noqa: E402


class _FakeResponse:
    def __init__(self, *, ok: bool = True, status_code: int = 200, payload=None, text: str = ""):
        self.ok = ok
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text
        self.headers = {}

    def json(self):
        return self._payload


def _make_client() -> LLMClient:
    return LLMClient(
        provider="deepseek",
        base_url="https://api.deepseek.com",
        api_key="test-key",
        model="deepseek-v4-flash",
    )


def test_openai_compat_omits_max_tokens_and_temperature():
    captured = {}

    def fake_post(url, headers, json, timeout):  # noqa: A002
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _FakeResponse(
            payload={"choices": [{"message": {"content": "ok"}}]},
            text='{"choices":[{"message":{"content":"ok"}}]}',
        )

    client = _make_client()
    with patch("llm.requests.post", side_effect=fake_post):
        result = client.chat([{"role": "user", "content": "你好"}], system="你是助手")

    assert result == "ok"
    assert captured["url"].endswith("/chat/completions")
    body = captured["json"]
    assert body["model"] == "deepseek-v4-flash"
    assert body["messages"][0] == {"role": "system", "content": "你是助手"}
    assert "max_tokens" not in body
    assert "temperature" not in body


def test_empty_content_raises_llm_error_with_p1_hint():
    def fake_post(url, headers, json, timeout):  # noqa: ARG001,A002
        return _FakeResponse(
            payload={"choices": [{"message": {"content": ""}}]},
            text='{"choices":[{"message":{"content":""}}]}',
        )

    client = _make_client()
    with patch("llm.requests.post", side_effect=fake_post):
        try:
            client.chat([{"role": "user", "content": "你好"}])
        except LLMError as exc:
            assert exc.kind == "empty_content"
            assert "max_tokens" in str(exc)
            assert "empty_content" in str(exc)
        else:
            raise AssertionError("期望抛出 LLMError(empty_content)，但没有抛错")


if __name__ == "__main__":
    import traceback

    tests = [
        test_openai_compat_omits_max_tokens_and_temperature,
        test_empty_content_raises_llm_error_with_p1_hint,
    ]

    passed = failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception:  # noqa: BLE001
            print(f"  FAIL  {test.__name__}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"结果: {passed} 通过 / {failed} 失败")
    if failed:
        sys.exit(1)
