"""归一化函数单元测试（覆盖 LLM 把等额还款抽成单元素数组的真实 bug）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from core.parse import normalize_installments


def test_single_element_expanded():
    """LLM 只返回 [1072] + periods=12 → 必须补齐为 12 个。"""
    out = normalize_installments({"principal": 12000, "periods": 12, "installments": [1072]})
    assert len(out) == 12 and all(x == 1072 for x in out)


def test_short_array_padded_with_last():
    out = normalize_installments({"periods": 4, "installments": [100, 100, 90]})
    assert out == [100, 100, 90, 90]


def test_long_array_truncated():
    out = normalize_installments({"periods": 2, "installments": [1, 2, 3]})
    assert out == [1, 2]


def test_missing_raise():
    with pytest.raises(ValueError):
        normalize_installments({"periods": 12, "installments": []})


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
