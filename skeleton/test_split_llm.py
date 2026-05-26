"""针对 split_by_llm 锚点定位逻辑的最小验证测试。

覆盖 _count_body_hits / _resolve_anchor 的核心分支，以及
split_by_llm 在多命中场景下的行为。

运行方式:
    python -m pytest skeleton/test_split_llm.py -v
    # 或直接
    python skeleton/test_split_llm.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# 把 skeleton/ 加到搜索路径，方便直接 python 运行
sys.path.insert(0, str(Path(__file__).parent))

from split import Chapter, _count_body_hits, _resolve_anchor, split_by_llm  # noqa: E402


def test_count_body_hits_none():
    """needle 不存在 -> 空列表"""
    md = "abcdef" * 100
    assert _count_body_hits(md, "ZZZ", 0) == []


def test_count_body_hits_single():
    """needle 出现 1 次 -> 单元素列表"""
    md = "aaa bbb UNIQUE ccc ddd"
    hits = _count_body_hits(md, "UNIQUE", 0)
    assert hits == [md.index("UNIQUE")]


def test_count_body_hits_multiple():
    """needle 出现 3 次 -> 3 个位置"""
    md = "TAG first TAG second TAG third"
    hits = _count_body_hits(md, "TAG", 0)
    assert len(hits) == 3
    assert hits == sorted(hits)


def test_count_body_hits_toc_threshold():
    """toc_threshold 之前的命中被跳过"""
    md = "ANCHOR early content ... " + "X" * 200 + " ANCHOR body content"
    first_pos = md.index("ANCHOR")
    threshold = first_pos + 1
    hits = _count_body_hits(md, "ANCHOR", threshold)
    assert len(hits) == 1
    assert hits[0] > threshold


def test_resolve_anchor_zero_hits():
    """完全不命中 -> None"""
    md = "some content without the anchor"
    assert _resolve_anchor(md, "MISSING", 0) is None


def test_resolve_anchor_unique():
    """唯一命中 -> 直接返回正确位置"""
    md = "prefix " * 50 + "# 第一章 货币资金\n正文内容" + "suffix " * 50
    needle = "# 第一章 货币资金"
    result = _resolve_anchor(md, needle, 0)
    assert result == md.index(needle)


def test_resolve_anchor_multiple_identical_context():
    """多次命中且后续上下文完全相同 -> 消歧失败"""
    repeated_block = "CHAPTER_START\n" + "X" * 200 + "\n"
    md = "toc " * 20 + repeated_block * 3
    needle = "CHAPTER_START"
    assert _resolve_anchor(md, needle, 0) is None


def test_resolve_anchor_multiple_unique_context_ambiguous():
    """多个命中都有唯一上下文时，不盲猜其中任意一个"""
    toc = "toc " * 30
    body_1 = "ANCHOR" + "DUPLICATE_BODY " * 20
    body_2 = "ANCHOR" + "UNIQUE_CH1_BODY " * 20
    md = toc + body_1 + "separator " * 5 + body_2
    needle = "ANCHOR"
    threshold = len(toc)

    result = _resolve_anchor(md, needle, threshold)
    assert result is None


def test_resolve_anchor_one_unique_among_many():
    """多次命中中恰好 1 个有唯一上下文 -> 返回该位置"""
    toc = "toc " * 30
    header = "ANCHOR" + "REPEATED_HEADER " * 15
    real_ch = "ANCHOR" + "REAL_CHAPTER_UNIQUE_CONTENT " * 15

    md = toc + header + "mid " * 5 + header + "mid " * 5 + real_ch
    threshold = len(toc)
    needle = "ANCHOR"

    result = _resolve_anchor(md, needle, threshold)
    assert result is not None
    expected = md.index(real_ch)
    assert result == expected


class _FakeLLMClient:
    """把预设响应作为 LLM 输出返回。"""

    def __init__(self, response: str):
        self._response = response

    def chat(self, messages):  # noqa: ARG002
        return self._response


def _build_textbook(chapters: list[tuple[str, str, str]]) -> str:
    """构造简单 markdown 教材。每个 chapter: (num, title, first_line)"""
    toc = "# 目录\n" + "\n".join(
        f"# 第{num}章 {title} → {i}" for i, (num, title, _) in enumerate(chapters, 1)
    ) + "\n\n" + "=" * 80 + "\n\n"
    body = ""
    for num, title, first_line in chapters:
        body += f"{first_line}\n# 第{num}章 {title}\n\n" + f"正文内容 第{num}章。\n" * 30 + "\n"
    return toc + body


def test_split_by_llm_unique_anchors():
    """正常场景：每个 first_line 唯一命中 -> 正确切出 3 章"""
    chapters = [
        ("1", "货币资金", "# 第一章 货币资金"),
        ("2", "应收账款", "# 第二章 应收账款"),
        ("3", "存货管理", "# 第三章 存货管理"),
    ]
    md = _build_textbook(chapters)
    import json as _json

    proposals = [
        {"num": num, "title": title, "first_line": first_line}
        for num, title, first_line in chapters
    ]
    llm = _FakeLLMClient(_json.dumps(proposals, ensure_ascii=False))
    result = split_by_llm(md, llm)
    assert len(result) == 3
    assert all(isinstance(chapter, Chapter) for chapter in result)
    assert result[0].num == "1"
    assert result[2].num == "3"


def test_split_by_llm_multi_hit_skipped(capsys):
    """多次命中且无法消歧时，该 proposal 被跳过，不产生错误章节"""
    toc = "# 目录\n第1章 测试\n\n"
    same_ctx = "A" * 200
    repeated_block = "REPEATED_ANCHOR\n" + same_ctx + "\n"
    unique_ch2 = "# 第2章 唯一章节标题UNIQUE\n" + "章节正文内容。" * 40 + "\n"
    body = toc + repeated_block * 3 + unique_ch2

    import json as _json

    proposals = [
        {"num": "1", "title": "重复测试", "first_line": "REPEATED_ANCHOR"},
        {"num": "2", "title": "唯一章", "first_line": "# 第2章 唯一章节标题UNIQUE"},
    ]
    llm = _FakeLLMClient(_json.dumps(proposals, ensure_ascii=False))
    result = split_by_llm(body, llm)

    assert len(result) == 1
    assert result[0].num == "2"

    captured = capsys.readouterr()
    assert "消歧失败" in captured.out or "命中" in captured.out


def test_split_by_llm_hallucinated_anchor(capsys):
    """LLM 幻觉 first_line 被跳过，不抛异常"""
    toc = "# 目录\n\n" + " " * 400
    unique_body = "# 第1章 真实唯一标题ABCDE\n" + "\n".join(
        f"第{i}段正文，包含一些独特内容 sentence_{i}。" for i in range(60)
    )
    md = toc + unique_body

    import json as _json

    proposals = [
        {"num": "0", "title": "幻觉章", "first_line": "这段文字在原文里根本不存在XYZXYZ000"},
        {"num": "1", "title": "真实章节", "first_line": "# 第1章 真实唯一标题ABCDE"},
    ]
    llm = _FakeLLMClient(_json.dumps(proposals, ensure_ascii=False))
    result = split_by_llm(md, llm)

    assert len(result) == 1
    assert result[0].num == "1"

    captured = capsys.readouterr()
    assert "未命中" in captured.out


if __name__ == "__main__":
    import contextlib
    import inspect
    import io
    import traceback

    tests = [
        test_count_body_hits_none,
        test_count_body_hits_single,
        test_count_body_hits_multiple,
        test_count_body_hits_toc_threshold,
        test_resolve_anchor_zero_hits,
        test_resolve_anchor_unique,
        test_resolve_anchor_multiple_identical_context,
        test_resolve_anchor_multiple_unique_context_ambiguous,
        test_resolve_anchor_one_unique_among_many,
        test_split_by_llm_unique_anchors,
        test_split_by_llm_multi_hit_skipped,
        test_split_by_llm_hallucinated_anchor,
    ]

    class _CaptureSys:
        def readouterr(self):
            output = self._buf.getvalue() if hasattr(self, "_buf") else ""
            return type("R", (), {"out": output, "err": ""})()

        def __enter__(self):
            self._buf = io.StringIO()
            self._redirect = contextlib.redirect_stdout(self._buf)
            self._redirect.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            self._redirect.__exit__(exc_type, exc, tb)

    passed = failed = 0
    for test in tests:
        cap = _CaptureSys()
        try:
            sig = inspect.signature(test)
            if "capsys" in sig.parameters:
                with cap:
                    test(cap)
            else:
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
