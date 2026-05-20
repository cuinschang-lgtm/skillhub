"""
textbook2skill Agent 包
自主 AI Agent 框架：Think → Act → Reflect 循环

把 PDF 教材编译成 skill 的决策权交给 LLM Agent，
而非固定的 pipeline 脚本。
"""
import sys
from pathlib import Path

# 把 skeleton/ 加入 Python 路径，让 agent 子模块可以直接 import skeleton 里的模块
_skeleton_dir = str(Path(__file__).parent.parent / "skeleton")
if _skeleton_dir not in sys.path:
    sys.path.insert(0, _skeleton_dir)
