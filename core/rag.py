"""轻量 RAG：法条关键词检索（确定性实现，零外部依赖）。

说明：MVP 阶段用关键词匹配实现"检索增强"——把法条库切成段落，
按查询词命中数排序返回最相关段落及出处。
向量检索（chromadb）为 V2 规划，接口保持一致，报告里写清即可。
"""
from __future__ import annotations

import re
from pathlib import Path

LAWS_DIR = Path(__file__).resolve().parent.parent / "data" / "laws"

DEFAULT_QUERY = ["年化利率", "明示", "费用", "IRR"]


def _load_paragraphs() -> list[dict]:
    """把所有法条 md 按段落切块。"""
    paras = []
    for path in sorted(LAWS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        source = path.stem
        for block in re.split(r"\n\s*\n", text):
            block = block.strip()
            if len(block) < 40:  # 跳过过短块
                continue
            paras.append({"source": source, "text": block})
    return paras


def retrieve(query_terms: list[str] | None = None, k: int = 2) -> list[dict]:
    """返回最相关的 k 个法条段落（含出处）。"""
    terms = [t for t in (query_terms or DEFAULT_QUERY) if t]
    results = []
    for para in _load_paragraphs():
        score = sum(para["text"].count(t) for t in terms)
        if score > 0:
            results.append({**para, "score": score})
    results.sort(key=lambda x: -x["score"])
    return results[:k]
