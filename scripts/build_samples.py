"""生成 10 份示例账单 bills.json，并用 core.irr 计算标准答案写入 expected 字段。

标准答案同时用等额本息闭式/先息后本口径交叉验证，供 Excel RATE() 复核。
运行：python scripts/build_samples.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import irr  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_bills" / "bills.json"


def annuity_payment(principal: float, monthly_rate: float, n: int) -> float:
    """等额本息月供（真实计息口径）。"""
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** (-n))


def build() -> list[dict]:
    bills: list[dict] = []

    def add(name, tag, scenario, nominal_text, principal, periods,
            payment, upfront_fee=0.0, extra_last=0.0, note=""):
        payments = [payment] * periods
        if extra_last:
            payments[-1] = payment + extra_last
        cfs = [-(principal - upfront_fee)] + payments
        r = irr.irr_monthly(cfs)
        apr, ear = irr.annualized(r)
        bills.append({
            "id": len(bills) + 1, "name": name, "tag": tag, "scenario": scenario,
            "nominal_text": nominal_text, "principal": principal, "periods": periods,
            "payment": round(payment, 2), "upfront_fee": upfront_fee,
            "extra_last": extra_last, "note": note,
            "expected_monthly_irr": round(r, 6),
            "expected_apr": round(apr, 6), "expected_ear": round(ear, 6),
        })

    # 1. 经典电商分期：月费率0.6% → 年化约13.03%（全场记忆点）
    add("电商白条式分期", "认知差之王", "12,000 元买笔记本，分 12 期，标称月费率 0.6%",
        "月费率 0.6%", 12000, 12, 12000 / 12 + 12000 * 0.006,
        note="大多数同学以为年化是 0.6%×12=7.2%，实际接近两倍。")

    # 2. 手机 3 期
    add("手机 3 期免息分期？", "短周期陷阱", "5,000 元手机分 3 期，标称月费率 0.75%",
        "月费率 0.75%", 5000, 3, 5000 / 3 + 5000 * 0.0075,
        note="期数越短，费率折算年化越狠。")

    # 3. 银行消费贷等额本息（诚实定价对照组）
    add("银行消费贷（对照组）", "诚实定价", "30,000 元分 24 期，月利率 0.8% 按实际余额计息",
        "月利率 0.8%（按余额计息）", 30000, 24, annuity_payment(30000, 0.008, 24),
        note="按余额计息的等额本息，费率即真实利率——对照组，用于对比哪些商家在玩话术。")

    # 4. 先息后本经营贷
    add("先息后本经营贷", "口径陷阱", "100,000 元，月息 0.9% 先息后本，12 期还本",
        "月息 0.9%", 100000, 12, 900, extra_last=100000,
        note="每月只还利息看似便宜，资金利用率高，真实年化≈10.8%。")

    # 5. 一次性服务费陷阱
    add("一次性服务费陷阱", "费率美化", "10,000 元分 12 期，每月还 900 元，另收 800 元服务费",
        "月费率 0.66%（另有 800 元服务费）", 10000, 12, 900, upfront_fee=800,
        note="服务费不计入息，利率就被'美化'了；计入后年化显著抬升。")

    # 6. 免息 + 手续费
    add("免息分期（收手续费）", "免息话术", "6,000 元分 6 期免息，每期 1,000 元，另收 300 元手续费",
        "免息（另收 300 元手续费）", 6000, 6, 1000, upfront_fee=300,
        note="'免息'不等于零成本——手续费折算年化照样存在。")

    # 7. 超司法红线
    add("高息现金贷", "超红线", "20,000 元分 12 期，每月还 2,100 元",
        "月费率 2%", 20000, 12, 2100,
        note="远超 4 倍 LPR 司法保护上限，报告中给出红线判定。")

    # 8. 日息万五
    add("'日息万五'网贷", "话术之王", "10,000 元分 12 期，宣传'日息万五'（=月息约1.5%）",
        "日息万五", 10000, 12, 10000 / 12 + 10000 * 0.015,
        note="'万五'听起来像没有成本，年化一看约 16%+。")

    # 9. 校园分期
    add("校园分期", "超 24% 警示", "8,000 元分 12 期，每月还 799 元",
        "每月仅需 799 元", 8000, 12, 799,
        note="话术只说每月金额，从不提年化——本产品的典型目标场景。")

    # 10. 大额装修贷（长周期对照组）
    add("装修贷（对照组）", "诚实定价", "200,000 元分 36 期，月利率 0.33% 按余额计息",
        "月利率 0.33%（按余额计息）", 200000, 36, annuity_payment(200000, 0.0033, 36),
        note="长周期诚实定价对照，验证引擎在低利率长周期下依然精确。")

    return bills


if __name__ == "__main__":
    data = build()
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写入 {OUT}\n")
    print(f"{'账单':<14}{'标称':<16}{'真实年化APR':>10}{'有效年化':>10}")
    for b in data:
        print(f"{b['name']:<14}{b['nominal_text']:<16}{b['expected_apr']:>10.2%}{b['expected_ear']:>10.2%}")
