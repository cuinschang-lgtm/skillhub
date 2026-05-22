"""LLM 抽取章节内容（V1 修订版）

Input:  chapters.json + LLM client
Output:
  - extracted/<idx>-<title>.md，每章一个 markdown 文件
  - extracted/_manifest.json，记录每章成功/失败 + 原因（V1 新增）

⚠️ 关键约束:
- LLM 调用绝不传 max_tokens / temperature（reasoning 模型陷阱）— 由 llm.py 强制
- 并发跑（DeepSeek 支持高并发，串行差 10x+）
- 抽取 prompt 模板在 prompts/extraction.md，按需读取（这里只引用）
- V1: 任一章失败默认 fail-fast；用户显式 allow_partial 才允许带缺章继续

V0 实测 prompt 关键点:
- 明确 "写给机器看不是给学生看"
- 含反例（❌ 不要写"本章主要介绍"）
- 强制结构: 核心概念 / 公式 / 方法 / 例题 / 易混点 / 关联
- 数字、公式 100% 准确，OCR 错乱标 [OCR错乱]
"""
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from llm import LLMClient, LLMError


@dataclass
class ExtractResult:
    idx: int
    title: str
    path: Path
    success: bool
    error: str = ""
    error_kind: str = ""


def load_extraction_prompt(prompt_dir: Path) -> str:
    """从 prompts/extraction.md 加载 prompt 模板（只取第一个 fenced block）"""
    prompt_file = prompt_dir / "extraction.md"
    if not prompt_file.exists():
        raise FileNotFoundError(f"找不到 extraction prompt: {prompt_file}")
    raw = prompt_file.read_text(encoding="utf-8")
    m = re.search(r"```\s*\n(.+?)\n```", raw, re.DOTALL)
    if not m:
        raise ValueError(
            f"{prompt_file} 没有 fenced code block。prompt 模板必须包在 ``` 围栏里。"
        )
    return m.group(1)


def extract_one_chapter(
    client: LLMClient,
    prompt_template: str,
    chapter: dict,
    *,
    max_input_chars: int = 30000,
) -> str:
    """处理单章。返回抽取后的 markdown。失败抛 LLMError。"""
    text = chapter["content"]
    if len(text) > max_input_chars:
        text = text[:max_input_chars] + "\n[...章节后段省略...]"
    prompt = prompt_template.replace("{chapter_text}", text)
    return client.chat([{"role": "user", "content": prompt}])


def extract_all(
    chapters: list[dict],
    output_dir: Path,
    client: LLMClient,
    prompt_dir: Path,
    max_workers: int = 11,
    max_input_chars: int = 30000,
    *,
    allow_partial: bool = False,
) -> tuple[list[ExtractResult], Path]:
    """并发抽取所有章节。

    Returns:
        (results, manifest_path) — results 是 per-chapter 状态，manifest 持久化到磁盘
    Raises:
        RuntimeError: 任一章失败且 allow_partial=False
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_template = load_extraction_prompt(prompt_dir)

    def worker(chapter) -> ExtractResult:
        idx = chapter["idx"]
        title = chapter["title"]
        print(f"[extract] {idx}: {title[:30]}...", flush=True)
        safe_title = re.sub(r"[^\w一-鿿\-]", "_", title)[:60]
        filename = f"{idx:02d}-{safe_title}.md"
        path = output_dir / filename
        try:
            result = extract_one_chapter(
                client,
                prompt_template,
                chapter,
                max_input_chars=max_input_chars,
            )
            path.write_text(result, encoding="utf-8")
            return ExtractResult(idx=idx, title=title, path=path, success=True)
        except LLMError as e:
            print(f"[extract] {idx} 失败: {e}", flush=True)
            # 写一个清晰可识别的占位（带原因），便于人工排查
            path.write_text(
                f"# {title}\n\n[抽取失败 kind={e.kind}: {e}]\n",
                encoding="utf-8",
            )
            return ExtractResult(
                idx=idx, title=title, path=path,
                success=False, error=str(e), error_kind=e.kind,
            )
        except Exception as e:
            print(f"[extract] {idx} unexpected: {e}", flush=True)
            path.write_text(f"# {title}\n\n[抽取失败 kind=unknown: {e}]\n", encoding="utf-8")
            return ExtractResult(
                idx=idx, title=title, path=path,
                success=False, error=str(e), error_kind="unknown",
            )

    worker_count = max(1, min(max_workers, len(chapters)))
    with ThreadPoolExecutor(max_workers=worker_count) as ex:
        results = list(ex.map(worker, chapters))

    # 持久化 manifest
    manifest_path = output_dir / "_manifest.json"
    manifest = {
        "total": len(results),
        "success": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "chapters": [
            {
                "idx": r.idx,
                "title": r.title,
                "path": str(r.path),
                "success": r.success,
                "error": r.error,
                "error_kind": r.error_kind,
            }
            for r in results
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    failed = [r for r in results if not r.success]
    if failed and not allow_partial:
        raise RuntimeError(
            f"\n❌ 抽取失败 {len(failed)}/{len(results)} 章。失败列表:\n"
            + "\n".join(f"  - 第{r.idx}章 {r.title}: {r.error_kind} — {r.error[:80]}" for r in failed)
            + f"\n\nManifest: {manifest_path}\n"
            "默认 fail-fast 不继续。如确认要带缺章继续，传 allow_partial=True（不推荐）。"
        )

    print(
        f"[extract] 抽取完成 {manifest['success']}/{manifest['total']} 成功"
        + (f"，{manifest['failed']} 失败" if manifest['failed'] else ""),
        flush=True,
    )
    return results, manifest_path


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("chapters_json", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("prompt_dir", type=Path)
    p.add_argument("provider", nargs="?", default="deepseek")
    p.add_argument("--allow-partial", action="store_true",
                   help="允许部分章节失败继续（不推荐）")
    args = p.parse_args()

    chapters = json.loads(args.chapters_json.read_text(encoding="utf-8"))
    client = LLMClient.from_env(args.provider)
    results, manifest = extract_all(
        chapters, args.output_dir, client, args.prompt_dir,
        allow_partial=args.allow_partial,
    )
    print(f"\n[main] manifest: {manifest}", flush=True)
