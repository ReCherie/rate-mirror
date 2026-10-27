"""IRR 引擎单元测试。运行：python -m pytest tests/ -v 或 python tests/test_irr.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pytest

from core import irr
from core.report import analyze, prepay_decision

BILLS = json.loads((Path(__file__).resolve().parent.parent / "data" / "sample_bills" / "bills.json")
                   .read_text(encoding="utf-8"))


def test_single_period_exact():
    """借 100 一月后还 110，月 IRR 必须精确等于 10%。"""
    r = irr.irr_monthly([-100, 110])
    assert abs(r - 0.10) < 1e-9


def test_pv_consistency():
    """解出的利率代回现值方程，残差必须趋近 0（自洽性）。"""
    cfs = [-12000] + [1072.0] * 12
    r = irr.irr_monthly(cfs)
    assert abs(irr.pv(cfs, r)) < 1e-6


def test_classic_1303():
    """经典案例：12000/12期/月费率0.6%，名义年化（月IRR×12）≈ 13.03%。"""
    b = BILLS[0]
    assert abs(b["expected_apr"] - 0.1303) < 0.001, f"期望约13.03%，实际 {b['expected_apr']:.4%}"


def test_all_sample_bills_self_consistent():
    """所有示例账单：解出的 IRR 代回现值方程残差趋近 0。"""
    for b in BILLS:
        payments = [b["payment"]] * b["periods"]
        if b["extra_last"]:
            payments[-1] += b["extra_last"]
        cfs = irr.parse_bill_to_cashflows(b["principal"], payments, b["upfront_fee"])
        r = irr.irr_monthly(cfs)
        # 月供保留到分（bills.json 已四舍五入），残差容忍到 0.01 元级
        assert abs(irr.pv(cfs, r)) < 1e-4, b["name"]


def test_bad_cashflows_raise():
    with pytest.raises(ValueError):
        irr.irr_monthly([100, -110])   # 方向反了
    with pytest.raises(ValueError):
        irr.irr_monthly([-100])        # 没有还款


def test_upfront_fee_raises_rate():
    """同样还款额下，收前置服务费必然抬高真实年化（费率美化的数学本质）。"""
    no_fee = analyze(10000, [900] * 12)
    with_fee = analyze(10000, [900] * 12, upfront_fee=800)
    assert with_fee["apr"] > no_fee["apr"]


def test_prepay_decision():
    d1 = prepay_decision(6, 1000, 5000, penalty=0)
    assert d1["verdict"] == "划算"
    d2 = prepay_decision(6, 1000, 5000, penalty=9999)
    assert d2["verdict"] == "不划算"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
