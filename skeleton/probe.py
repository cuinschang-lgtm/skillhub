"""探测 PDF 元数据（最小骨架）"""

import json
import sys
from pathlib import Path

from pdf_utils import probe_pdf_file


def probe_pdf(pdf_path: Path) -> dict:
    return probe_pdf_file(pdf_path)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: probe.py <pdf_path>", file=sys.stderr)
        sys.exit(1)
    result = probe_pdf(Path(sys.argv[1]))
    print(json.dumps(result, indent=2, ensure_ascii=False))
